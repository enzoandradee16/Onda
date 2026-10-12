"""Conservative catalog-to-YouTube matching; never assumes the first hit is correct."""
import re
import unicodedata


def words(value):
    text = unicodedata.normalize("NFKD", value or "")
    return set(re.findall(r"[a-z0-9]+", "".join(c for c in text.lower() if not unicodedata.combining(c))))


def without_guest_credit(value):
    """Guest credits move between artist and title across catalogs/uploads."""
    return re.sub(r"\b(?:feat(?:uring)?|ft)\.?\s+[^()\[\]]+", "", value or "", flags=re.I).strip()


VERSIONS = {"live", "cover", "remix", "karaoke", "instrumental", "acoustic", "sped", "slowed", "nightcore", "remaster", "remastered", "extended", "edit", "demo", "mono", "stereo", "piano", "lofi"}


class AmbiguousMatch(ValueError):
    def __init__(self, candidates):
        super().__init__("Há versões semelhantes demais no YouTube; a seleção automática ficou incerta.")
        self.candidates = candidates


def score_candidate(record, candidate):
    title = words(without_guest_credit(record.get("title")))
    candidate_title = words(without_guest_credit(candidate.get("title")))
    if not title or not record.get("artists") or candidate.get("is_live"):
        return None
    if (words(candidate.get("title")) & VERSIONS) != (words(record.get("title")) & VERSIONS):
        return None
    title_overlap = len(title & candidate_title) / len(title)
    if title_overlap < .9:
        return None
    identity = candidate_title | words(candidate.get("channel")) | words(candidate.get("uploader"))
    # Apple may supply one combined credit string; compare its constituent words.
    artist = words(without_guest_credit(record["artists"][0])) - {"and", "with"}
    artist_overlap = len(artist & identity) / len(artist) if artist else 0
    if artist_overlap < .65:
        return None
    target = record.get("duration_ms")
    duration = candidate.get("duration")
    duration_score = .5
    if target:
        if not isinstance(duration, (int, float)) or duration <= 0:
            return None
        difference = abs(target / 1000 - duration)
        tolerance = max(6, min(15, target / 1000 * .04))
        if difference > tolerance:
            return None
        duration_score = 1 - difference / tolerance
    score = .55 * title_overlap + .3 * artist_overlap + .15 * duration_score
    return round(score, 4)


def select_candidate(record, entries, *, prefer_best=False):
    entries = list(entries)
    ranked = []
    for entry in entries:
        if not entry or not re.fullmatch(r"[A-Za-z0-9_-]{11}", entry.get("id", "")):
            continue
        score = score_candidate(record, entry)
        if score is not None and score >= .84:
            ranked.append((score, entry))
    if not ranked:
        if prefer_best:
            raise ValueError("Nenhuma versão suficientemente compatível no YouTube para seleção automática. O item não foi baixado; confira título, artista e versão da faixa.")
        # Offer plausible versions for explicit review; never silently relax
        # duration/version constraints for the automatic selection.
        title = words(without_guest_credit(record.get("title"))) - VERSIONS
        artist = words(without_guest_credit((record.get("artists") or [""])[0])) - {"and", "with"}
        manual = []
        for entry in entries:
            if not entry or entry.get("is_live") or not re.fullmatch(r"[A-Za-z0-9_-]{11}", entry.get("id", "")):
                continue
            identity = words(entry.get("title")) | words(entry.get("channel")) | words(entry.get("uploader"))
            if not title or not artist or not title <= identity or len(artist & identity) / len(artist) < .65:
                continue
            if words(entry.get("title")) & {"cover", "karaoke"}:
                continue
            manual.append({**entry, "match_score": 0, "manual_review": True,
                           "source_url": "https://www.youtube.com/watch?v=" + entry["id"]})
        if manual:
            raise AmbiguousMatch(manual)
        raise ValueError("Nenhuma versão suficientemente compatível no YouTube. Confira título, artista e versão da faixa.")
    ranked.sort(key=lambda row: row[0], reverse=True)
    candidates = [{**entry, "match_score": score,
                   "source_url": "https://www.youtube.com/watch?v=" + entry["id"]} for score, entry in ranked]
    if not prefer_best and len(ranked) > 1 and ranked[0][0] - ranked[1][0] < .025:
        raise AmbiguousMatch(candidates)
    return candidates[0]


def find_youtube(record, logger, *, prefer_best=False):
    from yt_dlp import YoutubeDL
    if not record.get("title") or not record.get("artists"):
        raise ValueError("Faltam título/artista para buscar com segurança. Pesquise a música pelo nome na aba Pesquisar músicas e escolha uma faixa do catálogo.")
    query = " ".join([without_guest_credit(record["artists"][0]), without_guest_credit(record["title"]), "audio"])
    options = dict(quiet=True, logger=logger, extract_flat="in_playlist", skip_download=True,
                   playlistend=8, socket_timeout=20, retries=2, js_runtimes={"deno": {}, "node": {}})
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info("ytsearch8:" + query, download=False)
    return select_candidate(record, (result or {}).get("entries") or [], prefer_best=prefer_best)


def resolve_youtube(record, logger, choose, *, automatic=False, confirm=False):
    if automatic:
        return find_youtube(record, logger, prefer_best=True)
    try:
        match = find_youtube(record, logger)
    except AmbiguousMatch as exc:
        return choose(record, exc.candidates)
    return choose(record, [match]) if confirm else match
