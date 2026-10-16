"""Conservative catalog-to-YouTube matching; never assumes the first hit is correct."""
import re
import unicodedata


def words(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    text = re.sub(r"(?<=\w)[’'ʼ](?=\w)", "", text)
    return set(re.findall(r"[^\W_]+", "".join(c for c in text.casefold() if not unicodedata.combining(c))))


def without_guest_credit(value):
    """Guest credits move between artist and title across catalogs/uploads."""
    return re.sub(r"\b(?:feat(?:uring)?|ft|convidando)\.?\s+[^()\[\]]+", "", value or "", flags=re.I).strip()


VERSIONS = {"live", "cover", "remix", "karaoke", "instrumental", "acoustic", "sped", "slowed", "nightcore", "remaster", "remastered", "extended", "edit", "demo", "mono", "stereo", "piano", "lofi", "medley", "mashup", "loop", "looped", "reverb"}


class NoCompatibleMatch(ValueError):
    pass


class AmbiguousMatch(ValueError):
    def __init__(self, candidates):
        super().__init__("Há versões semelhantes demais no YouTube; a seleção automática ficou incerta.")
        self.candidates = candidates


def revalidate_match(record, selected, current):
    """Validate fresh extractor metadata before any audio bytes are downloaded."""
    from edition_evidence import differences, finite_positive
    if selected.get('id') != current.get('id') or current.get('is_live'):
        raise NoCompatibleMatch('A fonte mudou desde a busca. Escolha a versão novamente.')
    if selected.get('selection') == 'user':
        snapshot=dict(selected,duration_ms=selected.get('duration',0)*1000 if finite_positive(selected.get('duration')) else None)
        old,new=matching_tokens(selected.get('title')),matching_tokens(current.get('title'))
        if differences(snapshot,current,video=True) or not old or len(old & new)/len(old)<.9:
            raise NoCompatibleMatch('Os detalhes da versão escolhida mudaram. Faça uma nova busca.')
    else:
        anchor=dict(record)
        if selected.get('_verified_artist_aliases'):
            from artist_alias_lookup import valid_groups
            anchor['_verified_artist_aliases']=valid_groups(selected['_verified_artist_aliases'])
        alias=selected.get('title_alias')
        if alias:
            anchor.update(title=alias['alternate_title'],artists=alias['alternate_artists'])
        score=score_candidate(anchor,current)
        if score is None or score<.84:
            raise NoCompatibleMatch('Os detalhes completos do áudio não confirmam a correspondência. Escolha a versão novamente.')
    return current


def matching_tokens(value):
    value=re.sub(r'\b([A-Z][a-z]{1,8})(?:\1){1,3}\b',lambda match:' '.join([match[1]]*(len(match[0])//len(match[1]))),value or '')
    value=re.sub(r'(?:\b(?:version|versione|part|parte|pt|seq|sequence)\.?\s*[:#-]?\s*|(?<!\w)#\s*)(\d{1,2})\b',lambda match:'sequence'+str(int(match[1])),value,flags=re.I)
    tokens = words(value)
    phrase_text = unicodedata.normalize("NFKD", value or "").casefold()
    phrase_text = "".join(c for c in phrase_text if not unicodedata.combining(c) and unicodedata.category(c) != 'Cf')
    phrase_text = re.sub(r"[’'ʼ]", "", phrase_text)
    phrase_text = " ".join(re.findall(r"[^\W_]+", phrase_text))
    aliases = {"remastered": "remaster", "rerecorded": "rerecording",
               "en vivo": "live", "ao vivo": "live", "re recorded": "rerecording",
               "re recording": "rerecording", "new recording": "rerecording", "taylors version": "rerecording",
               "remasterizado": "remaster", "remasterizada": "remaster",
               "acustico": "acoustic", "acustica": "acoustic",
               "a cappella": "acappella", "a capella": "acappella",
               "sped up": "sped", "speed up": "sped", "slowed down": "slowed",
               "en directo": "live", "ao vivo": "live", "unplugged": "acoustic",
               "regravacao": "rerecording", "regrabacion": "rerecording",
               "versao instrumental": "instrumental", "version instrumental": "instrumental"}
    for phrase, canonical in aliases.items():
        parts = set(phrase.split())
        if parts <= tokens and (len(parts)==1 or re.search(r"(?<!\w)"+re.escape(phrase)+r"(?!\w)", phrase_text)):
            tokens = (tokens - parts) | {canonical}
    return tokens


def version_signature(value):
    tokens=matching_tokens(value)
    signature=tokens & (VERSIONS | {"rerecording", "acappella"})
    signature |= {token for token in tokens if re.fullmatch(r"sequence\d{1,2}",token)}
    # "Live Forever" and "Acoustic Dreams" are titles, not version labels.
    # An additional label, e.g. "Live Forever (Live)", remains significant.
    match=re.match(r'^\s*(live|acoustic|instrumental|piano|cover|demo|stereo|mono)\s+(\w+)',value or '',re.I)
    if match and match[2].lower() not in {'at','in','from','version','mix','edit','remix'}:
        term=match[1].lower()
        if len(re.findall(r'\b'+term+r'\b',value,re.I))==1:signature.discard(term)
    return signature


def score_candidate(record, candidate):
    from search_evidence import explicit_conflict, video_identity, presentation_title
    from edition_evidence import edition_conflicts, recording_title, finite_positive
    candidate = video_identity(candidate)
    if explicit_conflict(record, candidate) or edition_conflicts(record, candidate):
        return None
    title = matching_tokens(without_guest_credit(recording_title(record)))
    candidate_title = matching_tokens(without_guest_credit(presentation_title(record,candidate)))
    if not title or not record.get("artists") or candidate.get("is_live"):
        return None
    if version_signature(recording_title(candidate)) != version_signature(recording_title(record)):
        return None
    title_overlap = len(title & candidate_title) / len(title)
    if title_overlap < .9:
        return None
    identity = candidate_title | words(candidate.get("title")) | words(candidate.get("channel")) | words(candidate.get("uploader")) | words(candidate.get("artist"))
    # Known artist aliases retain provenance and all title/version/time constraints.
    from artist_aliases import artist_overlap as compare_artist
    artist_overlap = max((compare_artist(name,identity,record) for name in record["artists"] if isinstance(name,str) and name.strip()),default=0)
    if artist_overlap < .65:
        return None
    target = record.get("duration_ms")
    duration = candidate.get("duration")
    duration_score = .5
    if target is not None:
        if not finite_positive(target) or not finite_positive(duration):
            return None
        difference = abs(target / 1000 - duration)
        tolerance = max(6, min(15, target / 1000 * .04))
        if difference > tolerance:
            return None
        duration_score = 1 - difference / tolerance
    # Extra unrelated title words must not receive a perfect identity score.
    from artist_aliases import artist_names
    artist_tokens=set().union(*(tokens for name in record['artists'] for tokens,_ in artist_names(name,record)))
    extra = candidate_title - title - artist_tokens - words(record.get('album')) - {'official','oficial','audio','video','lyrics','lyric','hd','hq','4k','visualizer','visual','visualiser','music','high','quality'}
    if len(title)/max(1,len(title)+len(extra)) < .7:
        return None
    penalty = min(.12, .025 * len(extra))
    score = .55 * title_overlap + .3 * artist_overlap + .15 * duration_score - penalty
    return round(score, 4)


def select_candidate(record, entries, *, prefer_best=False):
    from edition_evidence import differences
    entries = list({entry.get('id'):entry for entry in entries if isinstance(entry,dict)}.values())
    from search_choices import ChoiceStore
    choices=ChoiceStore().get(record)
    entries=[entry for entry in entries if choices.get(entry.get('id')) is not False]
    ranked = []
    rejected_reasons=set()
    for entry in entries:
        if not entry or not re.fullmatch(r"[A-Za-z0-9_-]{11}", entry.get("id", "")):
            continue
        score = score_candidate(record, entry)
        if score is not None and score >= .84:
            ranked.append((score, entry))
        else:
            expected=matching_tokens(without_guest_credit(record.get('title')))
            if expected and len(expected & matching_tokens(entry.get('title')))/len(expected)>=.5:
                rejected_reasons.update(differences(record,entry,video=True))
    if not ranked:
        if prefer_best:
            detail=(' '+ '; '.join(sorted(rejected_reasons))+'.') if rejected_reasons else ''
            raise NoCompatibleMatch("Nenhuma versão suficientemente compatível no YouTube para seleção automática. O item não foi baixado; confira título, artista e versão da faixa."+detail)
        # Offer plausible versions for explicit review; never silently relax
        # duration/version constraints for the automatic selection.
        title = matching_tokens(without_guest_credit(record.get("title"))) - VERSIONS
        artist = words(without_guest_credit((record.get("artists") or [""])[0])) - {"and", "with"}
        from artist_aliases import artist_overlap as compare_artist
        manual = []
        for entry in entries:
            if not entry or entry.get("is_live") or not re.fullmatch(r"[A-Za-z0-9_-]{11}", entry.get("id", "")):
                continue
            identity = words(entry.get("title")) | words(entry.get("channel")) | words(entry.get("uploader"))
            if not title or not artist or not title <= identity or max((compare_artist(name,identity,record) for name in record["artists"] if isinstance(name,str) and name.strip()),default=0) < .65:
                continue
            if words(entry.get("title")) & {"cover", "karaoke"}:
                continue
            manual.append({**entry, "match_score": 0, "manual_review": True,
                           "match_reasons": differences(record,entry,video=True) or ['Identidade insuficiente para escolha automática'],
                           "source_url": "https://www.youtube.com/watch?v=" + entry["id"]})
        if manual:
            raise AmbiguousMatch(manual)
        raise NoCompatibleMatch("Nenhuma versão suficientemente compatível no YouTube. Confira título, artista e versão da faixa.")
    ranked.sort(key=lambda row: row[0], reverse=True)
    candidates = [{**entry, "match_score": score, "match_confidence": 'probable',
                   "match_reasons": ['Título, artista, versão e duração compatíveis'],
                   "source_url": "https://www.youtube.com/watch?v=" + entry["id"]} for score, entry in ranked]
    if record.get('_verified_artist_aliases'):
        for candidate in candidates:candidate['_verified_artist_aliases']=record['_verified_artist_aliases']
    remembered=next((row for row in candidates if choices.get(row['id']) is True),None)
    if remembered:
        return dict(remembered,selection='remembered',match_reasons=remembered['match_reasons']+['Escolha anterior revalidada'])
    from artist_aliases import alias_evidence
    for candidate in candidates:
        identity=words(candidate.get('title')) | words(candidate.get('channel')) | words(candidate.get('uploader')) | words(candidate.get('artist'))
        evidence=alias_evidence(record['artists'][0],identity,record)
        if evidence:candidate['artist_alias']=evidence
    if not prefer_best and len(ranked) > 1 and ranked[0][0] - ranked[1][0] < .04:
        raise AmbiguousMatch(candidates)
    return candidates[0]


def find_youtube(record, logger, *, prefer_best=False):
    from yt_dlp import YoutubeDL
    if not record.get("title") or not record.get("artists"):
        raise ValueError("Faltam título/artista para buscar com segurança. Pesquise a música pelo nome na aba Pesquisar músicas e escolha uma faixa do catálogo.")
    options = dict(quiet=True, logger=logger, extract_flat="in_playlist", skip_download=True,
                   playlistend=8, socket_timeout=20, retries=1, extractor_retries=1,
                   js_runtimes={"deno": {}, "node": {}})
    session_options = getattr(logger, 'youtube_options', None)
    if isinstance(session_options, dict):
        options.update(session_options)
    # Reuse client config and visitor cookies across alternate queries instead
    # of reinitializing the YouTube extractor for every spelling of a song.
    with YoutubeDL(options) as downloader:
        try:
            return _find_youtube(record, downloader, prefer_best=prefer_best)
        finally:
            logger.youtube_cookiejar = downloader.cookiejar


def _find_youtube(record, downloader, *, prefer_best=False):
    import time
    observed=[]
    query_cache={}
    deadline=time.monotonic()+60
    def search(current,album=False,artist=None,exact=False):
        nonlocal observed
        parts=[without_guest_credit(artist or current["artists"][0]),without_guest_credit(current["title"])]
        if album and current.get('album'):
            from search_evidence import album_search_title
            parts.append(album_search_title(current['album']))
        query=" ".join('"' + part.replace('"'," ") + '"' for part in parts[:2]) if exact else " ".join([*parts,"audio"])
        if time.monotonic()>=deadline:
            raise NoCompatibleMatch('Tempo de pesquisa esgotado. Tente uma busca mais específica.')
        if query not in query_cache:
            result=downloader.extract_info("ytsearch8:"+query,download=False)
            query_cache[query]=list((result or {}).get('entries') or [])
        observed=query_cache[query]
        return select_candidate(current,observed,prefer_best=prefer_best)
    try:
        return search(record)
    except NoCompatibleMatch as original_error:
        # Search wording can hide exact hits; retry once without the generic audio term.
        # Candidate identity, version and duration checks remain unchanged.
        previous=observed
        try:return search(record,exact=True)
        except NoCompatibleMatch:
            observed=previous+observed
        from artist_alias_lookup import discover_aliases
        groups=discover_aliases(record)
        if groups:
            record=dict(record,_verified_artist_aliases=groups)
            try:return select_candidate(record,observed,prefer_best=prefer_best)
            except NoCompatibleMatch:pass
            alternatives=list(dict.fromkeys(name for group in groups for name in group['aliases'] if words(name)!=words(record['artists'][0])))[:2]
            for artist in alternatives:
                try:return search(record,album=True,artist=artist)
                except NoCompatibleMatch:continue
        from catalog_aliases import alternate_records
        from metadata import MetadataClient
        client=MetadataClient()
        client.deadline=deadline
        try:aliases=alternate_records(record,client)
        finally:client.close()
        for alternate in aliases:
            current=dict(record,title=alternate['title'],artists=alternate.get('artists') or record['artists'],album=alternate.get('album') or record.get('album'))
            evidence={'original_title':record['title'],'alternate_title':alternate['title'],
                      'original_artists':record['artists'],'alternate_artists':current['artists'],
                      'source_url':alternate['source_url'],'verified_by':alternate['identity_evidence'],
                      'album':alternate.get('album'),'track_number':alternate.get('track_number'),'disc_number':alternate.get('disc_number')}
            try:
                try:match=select_candidate(current,observed,prefer_best=prefer_best)
                except NoCompatibleMatch:match=search(current,album=True)
                return dict(match,title_alias=evidence)
            except AmbiguousMatch as error:
                raise AmbiguousMatch([dict(row,title_alias=evidence) for row in error.candidates]) from None
            except NoCompatibleMatch:
                continue
        # A generic cue name may be buried among the composer's other soundtracks.
        # Keep this extra query on the slow path and reuse the existing session.
        if not aliases and record.get('album'):
            try:return search(record,album=True)
            except NoCompatibleMatch:pass
        raise original_error



def resolve_youtube(record, logger, choose, *, automatic=False, confirm=False):
    try:
        match = find_youtube(record, logger,prefer_best=True) if automatic else find_youtube(record, logger)
    except AmbiguousMatch as exc:
        if automatic:
            raise NoCompatibleMatch('Nenhuma versão suficientemente compatível para seleção automática. Confira a faixa na lista de falhas.') from None
        match=choose(record, exc.candidates)
    else:
        if confirm and not automatic:match=choose(record,[match])
    if match.get('remember_choice'):
        from search_choices import ChoiceStore
        ChoiceStore().set(record,match['id'],True)
    from music_search import count_selection
    count_selection(match.get('selection','automatic'))
    return match
