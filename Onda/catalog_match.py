"""Conservative catalog matching, with explicit selection for uncertain releases."""
from matching import words, VERSIONS
from metadata import MetadataError


class CatalogChoiceRequired(MetadataError):
    def __init__(self, anchor, candidates):
        super().__init__("Confirme qual faixa do catálogo corresponde ao link Spotify.")
        self.anchor, self.candidates = anchor, candidates


def picker_event(anchor, candidates):
    return {"title": anchor["title"], "artists": anchor.get("artists", []), "duration_ms": anchor.get("duration_ms"),
            "candidates": [{**row, "id": row["source_url"], "channel": ", ".join(row.get("artists", [])),
                            "duration": (row.get("duration_ms") or 0) / 1000, "match_score": row.get("catalog_score", 0)} for row in candidates]}


def rank_catalog(anchor, records):
    title = words(anchor.get("title"))
    if not title:
        return []
    artists = words((anchor.get("artists") or [""])[0])
    duration = anchor.get("duration_ms")
    ranked, seen = [], set()
    for record in records:
        candidate_title = words(record.get("title"))
        if not record.get("artists") or not candidate_title:
            continue
        if candidate_title & VERSIONS != title & VERSIONS:
            continue
        overlap = len(title & candidate_title) / len(title | candidate_title)
        if overlap < .8:
            continue
        artist_words = words(" ".join(record["artists"]))
        artist_score = len(artists & artist_words) / len(artists) if artists else 0
        if artists and artist_score < .85:
            continue
        other_duration = record.get("duration_ms")
        duration_score = 0
        if duration and other_duration:
            tolerance = max(4000, min(10000, duration * .03))
            difference = abs(duration - other_duration)
            if difference > tolerance:
                continue
            duration_score = 1 - difference / tolerance
        isrc, other_isrc = anchor.get("isrc"), record.get("isrc")
        if isrc and other_isrc and isrc.upper() != other_isrc.upper():
            continue
        same_isrc = bool(isrc and other_isrc and isrc.upper() == other_isrc.upper())
        score = 1 if same_isrc else .55 * overlap + .3 * artist_score + .15 * duration_score
        if anchor.get("album") and words(anchor["album"]) == words(record.get("album")):
            score += .02
        if record["source_url"] in seen:
            continue
        seen.add(record["source_url"])
        ranked.append({**record, "catalog_score": round(score, 4), "same_isrc": same_isrc})
    return sorted(ranked, key=lambda row: row["catalog_score"], reverse=True)


def automatic_catalog(anchor, candidates):
    if not candidates:
        return None
    best = candidates[0]
    confident = best["same_isrc"] or (anchor.get("artists") and anchor.get("duration_ms") and best["catalog_score"] >= .94)
    if not confident:
        return None
    if len(candidates) > 1 and best["catalog_score"] - candidates[1]["catalog_score"] < .04:
        return None
    return best
