"""Text-only catalog identification; lookup never modifies the source audio."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import time
import unicodedata
from uuid import UUID


def _words(value):
    value = unicodedata.normalize('NFKD', str(value)).casefold()
    return ' '.join(re.findall(r'[^\W_]+', ''.join(c for c in value if not unicodedata.combining(c))))


def filename_hint(filename, record=None):
    record = record or {}
    name = re.split(r'[/\\]', str(filename))[-1]
    stem = re.sub(r'\.(mp3|m4a|flac|wav|ogg|opus)$', '', name, flags=re.I)
    clean = re.sub(r'\[([A-Za-z0-9_-]{11})\]',
                   lambda m: '' if re.search(r'\d', m[1]) else m[0], stem)
    clean = re.sub(r'^\s*\d{1,3}\s*[-._]\s*', '', clean)
    clean = clean.replace('_', ' ')
    noise = r'(?:official\s+(?:music\s+)?(?:audio|video)|lyrics?|lyric\s+video|hd|hq|4k|\d{3,4}p)'
    clean = re.sub(r'[\[(]\s*' + noise + r'\s*[\])]', '', clean, flags=re.I)
    clean = re.sub(r'\s*[-–—]\s*' + noise + r'\s*$', '', clean, flags=re.I)
    clean = re.sub(r'^\s*\d{1,3}\s*[-._]\s*', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    parts = re.split(r'\s+[-–—]\s+', clean, maxsplit=1)
    title = str(record.get('title') or '').strip()
    if _words(title) in (_words(stem), _words(clean)):
        title = ''  # read_audio uses the filename as a display fallback.
    artists = record.get('artists') or []
    if isinstance(artists, str):
        artists = [part.strip() for part in artists.split(';') if part.strip()]
    artists = [str(a).strip() for a in artists if str(a).strip()]
    inferred = len(parts) == 2 and not artists and not title
    if len(parts) == 2:
        if not artists:
            artists = [parts[0]]
        title = title or parts[1]
    else:
        title = title or clean
    if not title or re.fullmatch(r'(?:audio|track|unknown|untitled|desconhecido)[\s\d_-]*', title, re.I):
        raise ValueError('O nome do arquivo não informa uma música. Preencha título ou artista para pesquisar.')
    anchor = {'title': title[:200], 'artists': artists, 'album': record.get('album') or ''}
    if inferred:
        anchor['_filename_pair'] = parts
    try:
        duration = float(record.get('duration') or 0)
        if 0 < duration < 86400:
            anchor['duration_ms'] = round(duration * 1000)
    except (TypeError, ValueError, OverflowError):
        pass
    return anchor


def _check(cancel):
    if cancel.is_set():
        raise InterruptedError('Operação cancelada.')


def _brainz(anchor):
    from artist_alias_lookup import AliasCache, get_json, quoted
    query = 'recording:' + quoted(anchor['title'])
    if anchor['artists']:
        names = list(dict.fromkeys(name.strip() for credit in anchor['artists'] for name in [credit, *re.split(r'\s*[,;]\s*', credit)] if name.strip()))
        query += ' AND (' + ' OR '.join('artist:' + quoted(name) for name in names[:8]) + ')'
    data = get_json('recording', {'query': query, 'limit': 8}, AliasCache())
    rows = []
    for row in data.get('recordings', []):
        identity = str(UUID(row['id']))
        releases = sorted(row.get('releases', []), key=lambda r: r.get('date') or '9999')
        edition = next((r for r in releases if r.get('status') == 'Official'), {})
        rows.append(dict(platform='MusicBrainz', title=row.get('title'),
                         artists=[a['artist']['name'] for a in row.get('artist-credit', []) if isinstance(a, dict) and a.get('artist')],
                         duration_ms=row.get('length'), album=edition.get('title') or '',
                         release_date=edition.get('date') or '',
                         _compilation='Compilation' in edition.get('release-group', {}).get('secondary-types', []),
                         source_url='https://musicbrainz.org/recording/' + identity))
    return rows


def _review_title(title):
    title = re.sub(r'\s*[\[(]\s*with\s+[^\])]+[\])]', '', title, flags=re.I)
    versions = r'instrumental|extended|karaoke|acoustic|demo|live|remix|remaster(?:ed)?|radio\s+(?:edit|mix)|original\s+mix'
    return re.sub(r'\s*[\[(][^\])]*\b(?:' + versions + r')\b[^\])]*[\])]|\s+[-–—]\s*(?:' + versions + r')\b.*$', '', title, flags=re.I).strip()


def _review_matches(anchor, rows, seen):
    """Broader suggestions for the manual tag picker only; never auto-match."""
    from difflib import SequenceMatcher
    from matching import words, without_guest_credit
    from artist_aliases import artist_overlap
    from edition_evidence import recording_title, finite_positive
    title = _words(_review_title(without_guest_credit(recording_title(anchor))))
    if not title:
        return []
    suggestions = []
    for row in rows:
        if row['source_url'] in seen or not row.get('artists'):
            continue
        other = _words(_review_title(without_guest_credit(recording_title(row))))
        tokens, other_tokens = set(title.split()), set(other.split())
        overlap = len(tokens & other_tokens) / max(1, len(tokens | other_tokens))
        similarity = SequenceMatcher(None, title, other).ratio()
        if overlap < .6 and similarity < .86:
            continue
        artist = max((artist_overlap(name, words(' '.join(row['artists']))) for name in anchor.get('artists') or []), default=0)
        # Some files store all credited artists in one tag, while a catalog
        # returns only the lead artist. Accept that subset for manual review.
        anchor_artists = words(' '.join(anchor.get('artists') or []))
        artist = max(artist, max((artist_overlap(name, anchor_artists) for name in row['artists'] if len(words(name)) >= 2), default=0))
        if anchor.get('artists') and artist < .65:
            continue
        duration, other_duration = anchor.get('duration_ms'), row.get('duration_ms')
        different_version = _words(recording_title(anchor)) != _words(recording_title(row)) and (
            title != _words(without_guest_credit(recording_title(anchor))) or other != _words(without_guest_credit(recording_title(row))))
        if finite_positive(duration) and finite_positive(other_duration):
            if abs(duration - other_duration) > max(30000, duration * .15) and not different_version:
                continue
        if not anchor.get('artists') and (similarity < .9 or not finite_positive(duration) or not finite_positive(other_duration)):
            continue
        suggestions.append(dict(row, catalog_score=min(.79, .55*max(overlap, similarity)+.3*artist-.1), manual_review=True,
                                match_reasons=['Correspondência aproximada. Confira artista, versão e duração antes de escolher.']))
        seen.add(row['source_url'])
    return suggestions


def _rank(anchor, rows):
    from catalog_match import rank_catalog
    from edition_evidence import recording_title
    from matching import version_signature

    originals = {row['source_url']: row for row in rows}
    from matching import matching_tokens
    # A catalog's non-explicit flag is not evidence that an untagged file is censored.
    if anchor.get('explicit') is None and not ({'clean', 'explicit'} & matching_tokens(anchor['title'])):
        rows = [dict(row, explicit=None) for row in rows]
    ranked = rank_catalog(anchor, rows)
    seen = {row['source_url'] for row in ranked}
    if not version_signature(anchor['title']):
        neutral = r'\s*[\[(]\s*(?:radio\s+(?:edit|mix)|original\s+(?:mix|version)|album\s+version|single\s+version|remaster(?:ed)?(?:\s+\d{4})?)\s*[\])]'
        for row in rows:
            display = recording_title(row)
            core = re.sub(neutral, '', display, flags=re.I).strip()
            if core == display or row['source_url'] in seen:
                continue
            view = dict(row, title=core, version='', title_version='')
            for item in rank_catalog(anchor, [view]):
                item.update(title=display, title_version=row.get('title_version'), version=row.get('version'))
                item['catalog_score'] -= .02
                item['match_reasons'] = ['Confira a versão indicada pelo catálogo.']
                ranked.append(item)
                seen.add(item['source_url'])
    ranked.extend(_review_matches(anchor, rows, seen))
    return [dict(row, explicit=originals[row['source_url']].get('explicit')) for row in ranked]


def search(config, cancel):
    from audio_library import read_audio
    from metadata import MetadataClient

    _check(cancel)
    record = config.get('record')
    if record is None:
        record = read_audio(config['source']) if config.get('source') else {}
    anchor = filename_hint(config.get('filename') or Path(config['source']).name, record)
    query = ' '.join(anchor['artists'] + [anchor['title']])[:300]
    deadline = time.monotonic() + 25

    def lookup(provider):
        _check(cancel)
        if provider == 'MusicBrainz':
            found = _brainz(anchor)
            core = _review_title(anchor['title'])
            if core != anchor['title'] and not _rank(anchor, found):
                _check(cancel)
                found += _brainz(dict(anchor, title=core))
            return found
        client = MetadataClient()
        client.cancelled, client.deadline = cancel.is_set, deadline
        try:
            found = client.search(query, provider, country=config.get('country', 'br'), limit=8)
            core = _review_title(anchor['title'])
            if core != anchor['title'] and not _rank(anchor, found):
                _check(cancel)
                found += client.search(' '.join(anchor['artists'] + [core])[:300], provider,
                                       country=config.get('country', 'br'), limit=8)
            return found
        finally:
            client.close()

    rows, warnings = [], []
    pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='metadata-name')
    try:
        jobs = {pool.submit(lookup, p): p for p in ('Deezer', 'Apple / iTunes', 'MusicBrainz')}
        for job in as_completed(jobs):
            _check(cancel)
            try:
                rows.extend(job.result())
            except Exception as error:
                _check(cancel)
                warnings.append(jobs[job] + ': ' + str(error))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    _check(cancel)
    ranked = _rank(anchor, rows)
    if anchor.get('_filename_pair'):
        reverse = dict(anchor, title=anchor['_filename_pair'][0], artists=[anchor['_filename_pair'][1]])
        reversed_rows = _rank(reverse, rows)
        if reversed_rows and (not ranked or reversed_rows[0]['catalog_score'] > ranked[0]['catalog_score']):
            anchor, ranked = reverse, reversed_rows
    # Prefer ordinary releases over obvious compilation titles without claiming certainty.
    for row in ranked:
        album = re.sub(r'\s*[-–—]\s*(single|ep)$', '', row.get('album') or '', flags=re.I)
        if _words(album) == _words(anchor['title']):
            row['catalog_score'] = min(1, row['catalog_score'] + .03)
        if row.get('_compilation'):
            row['catalog_score'] -= .05
        if re.search(r'\b(compilation|greatest hits|top hits|various artists)\b', row.get('album') or '', re.I):
            row['catalog_score'] -= .03
    ranked.sort(key=lambda row: row['catalog_score'], reverse=True)
    if not rows and len(warnings) == 3:
        raise ValueError('Não foi possível consultar os catálogos. Tente novamente.')
    return dict(anchor=anchor, candidates=ranked[:15], warnings=warnings)


def _complete_brainz(result, cancel):
    from artist_alias_lookup import AliasCache, get_json
    identity = str(UUID(result['source_url'].rsplit('/', 1)[-1]))
    cache = AliasCache()
    recording = get_json('recording/' + identity, {'inc': 'releases+isrcs'}, cache)
    editions = [r for r in recording.get('releases', []) if r.get('status') == 'Official']
    if editions:
        edition = min(editions, key=lambda r: r.get('date') or '9999')
        release_id = str(UUID(edition['id']))
        _check(cancel)
        release = get_json('release/' + release_id, {'inc': 'recordings+artist-credits'}, cache)
        result.update(album=release.get('title'), release_date=release.get('date'),
                      album_artists=[a['artist']['name'] for a in release.get('artist-credit', []) if isinstance(a, dict) and a.get('artist')])
        for medium in release.get('media', []):
            for track in medium.get('tracks', []):
                if track.get('recording', {}).get('id') == identity:
                    result.update(track_number=track.get('position'), disc_number=medium.get('position'))
        if release.get('cover-art-archive', {}).get('front'):
            result['cover_url'] = 'https://coverartarchive.org/release/' + release_id + '/front-500'
    if len(recording.get('isrcs', [])) == 1:
        result['isrc'] = recording['isrcs'][0]


def details(record, cancel):
    from audio_library import FIELDS
    from metadata import MetadataClient, MetadataError

    _check(cancel)
    result = dict(record)
    if result.get('platform') == 'MusicBrainz':
        import requests
        from artist_alias_lookup import LookupUnavailable
        try:
            _complete_brainz(result, cancel)
        except (OSError, LookupUnavailable, requests.RequestException):
            _check(cancel)
    else:
        client = MetadataClient()
        client.cancelled, client.deadline = cancel.is_set, time.monotonic() + 20
        try:
            if result.get('platform') == 'Deezer':
                from metadata import parse_link, deezer_record
                _, identity, _, url = parse_link(result['source_url'])
                raw = client.get_json('https://api.deezer.com/track/' + identity)
                full = deezer_record(raw, identity, url)
                album_id = str((raw.get('album') or {}).get('id') or '')
                if album_id.isdigit():
                    try:
                        album = client.get_json('https://api.deezer.com/album/' + album_id)
                        if (album.get('artist') or {}).get('name'):
                            full['album_artists'] = [album['artist']['name']]
                        genres = [g['name'] for g in (album.get('genres') or {}).get('data', []) if g.get('name')]
                        if genres:
                            full['genre'] = '; '.join(genres)
                    except MetadataError:
                        _check(cancel)
            else:
                full = client.fetch(result['source_url'])
            result.update({k: v for k, v in full.items() if v not in (None, '', [])})
        except MetadataError:
            _check(cancel)  # A failed detail request can still use the reviewed search result.
        finally:
            client.close()
    _check(cancel)
    from edition_evidence import recording_title
    result['title'] = recording_title(record)
    if record.get('artists'):
        result['artists'] = record['artists']
    if result.get('album_artists'):
        result['album_artist'] = '; '.join(result['album_artists'])
    fields = {k: (list(v) if k == 'artists' else str(v)) for k, v in result.items() if k in FIELDS and v not in (None, '', [])}
    return dict(changes=fields, cover_url=result.get('cover_url') or '')


def identify_entries(config, cancel, choose, emit):
    entries = config.get('entries')
    if entries is None:
        entries = [dict(source=config['source'], filename=config.get('filename'), record=config.get('record'), identity='single')]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 500:
        raise ValueError('Escolha de 1 a 500 arquivos de áudio.')
    matches, errors = [], []
    for index, entry in enumerate(entries):
        _check(cancel)
        emit('stage', message=f"{index+1}/{len(entries)} · {entry.get('filename') or Path(entry['source']).name}")
        try:
            found = search(entry, cancel)
            if not found['candidates']:
                errors.append({'filename': entry.get('filename') or entry['source'], 'error': 'Nenhuma gravação correspondente foi encontrada.'})
                continue
        except (ValueError, OSError) as error:
            _check(cancel)
            errors.append({'filename': entry.get('filename') or entry.get('source', ''), 'error': str(error)})
            continue
        chosen = choose(found['anchor'], found['candidates'])
        _check(cancel)
        matches.append(dict(identity=entry['identity'], **details(chosen, cancel)))
    return dict(matches=matches, errors=errors)
