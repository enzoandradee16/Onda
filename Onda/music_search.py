"""Bounded catalog discovery shared by desktop and Android.

Search relevance is deliberately separate from recording identity: a suggestion
must never become permission to download a different recording automatically.
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
from difflib import get_close_matches
import re
import threading
import time

from metadata import MetadataClient, MetadataError, is_streaming_link
from matching import words, matching_tokens, version_signature
from edition_evidence import date_parts, finite_positive, recording_title, edition_details


class SearchCancelled(MetadataError):
    pass


_cache = OrderedDict()
_lock = threading.RLock()
_stats = {'searches': 0, 'cache_hits': 0, 'provider_errors': 0, 'cancelled': 0,
          'completed':0, 'empty':0, 'total_ms':0, 'manual_choices':0, 'automatic_choices':0, 'revalidated_choices':0}
FIELDS = {'artist':'artist', 'artista':'artist', 'album':'album', 'title':'title', 'titulo':'title',
          'version':'version', 'versao':'version', 'year':'year', 'ano':'year',
          'duration':'duration', 'duracao':'duration', 'exact':'exact', 'exata':'exact'}


def diagnostics():
    # Aggregate counters only: never log queries, URLs, tokens, or account data.
    with _lock:
        return dict(_stats,average_ms=round(_stats['total_ms']/max(1,_stats['completed'])))


def count_selection(kind):
    key={'user':'manual_choices','remembered':'revalidated_choices','automatic':'automatic_choices'}.get(kind)
    if key:
        with _lock:_stats[key]+=1


def clear_cache():
    with _lock:
        _cache.clear()


def parse_query(query):
    query = ' '.join(str(query).split())
    if not 1 <= len(query) <= 300:
        raise MetadataError('Digite entre 1 e 300 caracteres para pesquisar.')
    filters = {}
    pattern = r'(?<!\S)([\w]+):("[^"]*"|\S+)'
    def field(match):
        key = FIELDS.get(match[1].lower())
        if not key:
            return match[0]
        filters[key] = match[2].strip('"')
        return ''
    free = re.sub(pattern, field, query)
    if free.count('"') % 2:
        raise MetadataError('Feche as aspas da pesquisa exata.')
    phrases = re.findall(r'"([^"]+)"', free)
    if 'year' in filters and not re.fullmatch(r'(?:19|20)\d{2}(?:-(?:19|20)\d{2})?',filters['year']):
        raise MetadataError('Use ano:2022 ou ano:2020-2022.')
    if 'duration' in filters and not re.fullmatch(r'\d+(?::[0-5]\d)?(?:-\d+(?::[0-5]\d)?)?',filters['duration']):
        raise MetadataError('Use duracao:3:30 ou duracao:3:00-4:00.')
    if 'exact' in filters and filters['exact'].lower() not in ('true','false','sim','nao','não','1','0'):
        raise MetadataError('Use exata:sim ou exata:nao.')
    free = ' '.join(free.split()).strip()
    terms = [free] + [filters[key] for key in ('artist','title','album','version') if filters.get(key)]
    remote = ' '.join(terms).strip()
    if not remote:
        raise MetadataError('Informe também um título, artista ou álbum.')
    return {'query':remote, 'free':free, 'filters':filters, 'phrases':phrases}


def _seconds(value):
    parts = [int(part) for part in value.split(':')]
    return parts[0] if len(parts)==1 else parts[0]*60+parts[1]


def accepts(record, parsed):
    filters = parsed['filters']
    for key, field in (('artist','artists'),('album','album'),('title','title')):
        if key in filters:
            value = ' '.join(record.get(field) or []) if field=='artists' else record.get(field)
            if not words(filters[key]) <= words(value):
                return False
    if filters.get('version'):
        expected = version_signature(filters['version'])
        actual = version_signature(recording_title(record))
        if expected:
            if expected != actual:
                return False
            wanted=edition_details({'title':'('+filters['version']+')'})
            observed=edition_details(record)
            if any(observed.get(key)!=value for key,value in wanted.items()):return False
        elif filters['version'].casefold() in ('original','studio','estudio','estúdio'):
            if actual:return False
        elif not words(filters['version']) <= words(recording_title(record)):
            return False
    if filters.get('year'):
        years = [int(year) for year in filters['year'].split('-')]
        actual = date_parts(record.get('release_date'))
        if not actual or not min(years) <= actual[0] <= max(years):
            return False
    if filters.get('duration'):
        limits = [_seconds(value) for value in filters['duration'].split('-')]
        duration = record.get('duration_ms')
        if not finite_positive(duration):
            return False
        low, high = (limits[0]-2,limits[0]+2) if len(limits)==1 else (min(limits),max(limits))
        if not low <= duration/1000 <= high:
            return False
    text = ' '.join(str(record.get(key) or '') for key in ('title','album'))+' '+' '.join(record.get('artists') or [])
    normalized = ' '+' '.join(re.findall(r'[^\W_]+',text.casefold()))+' '
    for phrase in parsed['phrases']:
        if ' '+' '.join(re.findall(r'[^\W_]+',phrase.casefold()))+' ' not in normalized:
            return False
    if filters.get('exact','').lower() in ('true','sim','1'):
        title = filters.get('title') or parsed['free'].strip('"')
        if title and matching_tokens(title) != matching_tokens(record.get('title')):
            return False
    return True


def _rank(records, parsed, limit):
    from record_identity import catalog_identity
    query_tokens = matching_tokens(parsed['query'])
    ranked, seen = [], set()
    for row in records:
        if not isinstance(row,dict) or not row.get('source_url') or row['source_url'] in seen or not accepts(row,parsed):
            continue
        seen.add(row['source_url'])
        identity = matching_tokens(row.get('title')) | words(' '.join(row.get('artists') or [])) | words(row.get('album'))
        score = len(query_tokens & identity)/max(1,len(query_tokens))
        ranked.append(dict(row, search_score=round(score,4)))
    ranked.sort(key=lambda row:row['search_score'],reverse=True)
    grouped = []
    for row in ranked:
        # Only collapse proven duplicates on the same album, preserving editions
        # and the user's ability to choose another release/cover.
        duplicate = next((item for item in grouped if words(item.get('album')) == words(row.get('album'))
                          and item.get('isrc') and row.get('isrc') and catalog_identity(item,row)=='isrc'),None)
        if duplicate is not None:
            duplicate.setdefault('equivalent_sources',[]).append({key:row.get(key) for key in ('source_url','platform','title','album')})
        else:
            grouped.append(row)
    return grouped[:limit]


def search_music(client, query, provider='Deezer', *, country='br', limit=25, account=None,
                 cancelled=lambda:False, deadline_seconds=30, automatic=False, choose=None, refresh=False):
    started = time.monotonic()
    def check():
        if cancelled():
            raise SearchCancelled('Pesquisa cancelada.')
        if time.monotonic()-started > deadline_seconds:
            raise SearchCancelled('Tempo de pesquisa esgotado. Tente uma busca mais específica.')
    check()
    if type(limit) is not int or not 1 <= limit <= 50:
        raise MetadataError('Use um limite de busca entre 1 e 50 músicas.')
    if is_streaming_link(query):
        record = client.resolve(query,choose=choose,automatic=automatic)
        check()
        return {'tracks':[record], 'warnings':[], 'suggestions':[], 'elapsed_ms':int((time.monotonic()-started)*1000)}
    parsed = parse_query(query)
    if provider not in ('Todos','Deezer','Apple / iTunes','Spotify'):
        raise MetadataError('Catálogo de pesquisa inválido.')
    providers = ['Deezer','Apple / iTunes'] if provider=='Todos' else [provider]
    if provider=='Todos' and ((account is not None and account.connected) or (client.client_id and client.client_secret)):
        providers.append('Spotify')
    with _lock:
        _stats['searches'] += 1
    rows, warnings, attempts = [], [], []
    def lookup(name, region, text):
        key = (name,region,text,limit,tuple(sorted(parsed['filters'].items())))
        if name != 'Spotify' and not refresh:
            with _lock:
                cached = _cache.get(key)
                if cached and time.monotonic()-cached[0]<300:
                    _stats['cache_hits'] += 1
                    _cache.move_to_end(key)
                    return deepcopy(cached[1])
        check()
        # Each worker owns its HTTP session; no concurrent requests.Session use.
        worker = MetadataClient(client.client_id,client.client_secret or '')
        worker.cancelled = cancelled
        worker.deadline = started + deadline_seconds
        try:
            found = worker.search(text,name,country=region,limit=limit,account=account)
            if name=='Deezer':
                detailed=[]
                requests=0
                for row in found:
                    if requests<4 and ('year' in parsed['filters'] and not date_parts(row.get('release_date'))):
                        check()
                        requests+=1
                        try:row=worker.fetch(row['source_url'])
                        except MetadataError:pass
                    detailed.append(row)
                found=detailed
            check()
        finally:
            worker.close()
        if found and name != 'Spotify':
            with _lock:
                _cache[key] = (time.monotonic(),deepcopy(found))
                _cache.move_to_end(key)
                while len(_cache)>128:
                    _cache.popitem(last=False)
        return found
    executor = ThreadPoolExecutor(max_workers=3,thread_name_prefix='onda-search')
    def collect(specs):
        futures = {}
        for spec in specs:
            if spec in attempts:
                continue
            attempts.append(spec)
            futures[executor.submit(lookup,*spec)] = spec
        # Collect by provider order after completion, so network timing cannot
        # change the order of equally relevant results.
        results = {}
        while futures:
            if cancelled():check()
            if time.monotonic()-started>deadline_seconds:
                warnings.append('Tempo limite atingido; exibindo os resultados disponíveis.')
                for future in futures:future.cancel()
                break
            ready,_ = wait(futures,timeout=.1,return_when=FIRST_COMPLETED)
            for future in ready:
                spec = futures.pop(future)
                try:
                    results[spec] = future.result()
                except SearchCancelled:
                    if cancelled():raise
                    warnings.append(spec[0]+': tempo limite atingido.')
                except MetadataError as exc:
                    warnings.append(spec[0]+': '+str(exc))
                    with _lock:
                        _stats['provider_errors'] += 1
        for spec in specs:
            rows.extend(results.get(spec,[]))
    try:
        collect([(name,country,parsed['query']) for name in providers])
        if not _rank(rows,parsed,limit) and time.monotonic()-started<deadline_seconds:
            # One fallback wave only: another public catalog / alternate region.
            fallback = [('Apple / iTunes','us',parsed['query'])] if provider=='Todos' else [
                ('Apple / iTunes' if provider=='Deezer' else 'Deezer',country,parsed['query'])]
            collect(fallback)
            if rows:warnings.append('A busca foi ampliada para outro catálogo ou região.')
        ranked = _rank(rows,parsed,limit)
        suggestions = []
        if not ranked or ranked[0]['search_score']<.75:
            vocabulary = {token for row in rows for token in words(row.get('title'))}
            for token in words(parsed['free']):
                if token not in vocabulary and len(token)>3:
                    alternatives = get_close_matches(token,sorted(vocabulary),n=1,cutoff=.82)
                    if alternatives:
                        suggestions.append(token+' → '+alternatives[0])
        if cancelled() or not rows:check()
        if not rows and warnings and len(warnings)==len(attempts):
            raise MetadataError('Não foi possível consultar os catálogos. '+'; '.join(warnings))
        elapsed=int((time.monotonic()-started)*1000)
        with _lock:
            _stats['completed']+=1
            _stats['empty']+=int(not ranked)
            _stats['total_ms']+=elapsed
        return {'tracks':ranked,'warnings':warnings,'suggestions':suggestions[:3],
                'elapsed_ms':elapsed,'attempts':len(attempts)}
    except SearchCancelled:
        with _lock:
            _stats['cancelled'] += 1
        raise
    finally:
        executor.shutdown(wait=False,cancel_futures=True)
