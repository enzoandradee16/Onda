"""Conservative catalog matching, with explicit selection for uncertain releases."""

from matching import words, without_guest_credit, version_signature, matching_tokens
from search_evidence import explicit_conflict, album_core, release_year
from metadata import MetadataError
from record_identity import catalog_identity, normalized_isrc
from edition_evidence import edition_conflicts, recording_title, finite_positive


class CatalogChoiceRequired(MetadataError):
    def __init__(self, anchor, candidates):
        super().__init__("Confirme qual faixa do catálogo corresponde ao link Spotify.")
        self.anchor, self.candidates = anchor, candidates


def picker_event(anchor, candidates):
    return {
        "title": anchor["title"],
        "artists": anchor.get("artists", []),
        "duration_ms": anchor.get("duration_ms"),
        "candidates": [
            {
                **row,
                "id": row["source_url"],
                "channel": ", ".join(row.get("artists", [])),
                "duration": (row.get("duration_ms") or 0) / 1000,
                "match_score": row.get("catalog_score", 0),
            }
            for row in candidates
        ],
    }


def rank_catalog(anchor, records):
    title = matching_tokens(without_guest_credit(recording_title(anchor)))
    if not title:
        return []
    artists = words(without_guest_credit((anchor.get("artists") or [""])[0]))
    duration = anchor.get("duration_ms")
    ranked, seen = [], set()
    for record in records:
        candidate_title = matching_tokens(without_guest_credit(recording_title(record)))
        if not record.get("artists") or not candidate_title:
            continue
        identity = catalog_identity(anchor, record)
        if explicit_conflict(anchor, record) or edition_conflicts(anchor, record):
            continue
        if (
            version_signature(recording_title(record))
            != version_signature(recording_title(anchor))
            and identity is None
        ):
            continue
        overlap = len(title & candidate_title) / len(title | candidate_title)
        if overlap < 0.8:
            if identity is None:
                continue
            overlap = 1.0
        artist_words = words(" ".join(record["artists"]))
        from artist_aliases import artist_overlap

        artist_score = max(
            (
                artist_overlap(name, artist_words)
                for name in anchor.get('artists') or []
            ),
            default=0,
        )
        if artists and artist_score < 0.85 and identity != "isrc":
            continue
        other_duration = record.get("duration_ms")
        duration_score = 0
        if finite_positive(duration) and finite_positive(other_duration):
            tolerance = max(4000, min(10000, duration * 0.03))
            difference = abs(duration - other_duration)
            if difference > tolerance:
                continue
            duration_score = 1 - difference / tolerance
        isrc, other_isrc = normalized_isrc(anchor.get("isrc")), normalized_isrc(
            record.get("isrc")
        )
        if isrc and other_isrc and isrc.upper() != other_isrc.upper():
            continue
        same_isrc = bool(isrc and other_isrc and isrc.upper() == other_isrc.upper())
        score = (
            1
            if same_isrc
            else 0.55 * overlap + 0.3 * artist_score + 0.15 * duration_score
        )
        year, other_year = release_year(anchor), release_year(record)
        if not same_isrc and year and other_year and abs(year - other_year) > 1:
            # Reissues can change dates; prefer the original year without rejecting them.
            score -= 0.03
        if anchor.get("album") and album_core(anchor["album"]) == album_core(
            record.get("album")
        ):
            score += 0.02
        if record["source_url"] in seen:
            continue
        seen.add(record["source_url"])
        ranked.append(
            {
                **record,
                "catalog_score": round(min(1, score), 4),
                "same_isrc": same_isrc,
                "match_reasons": (
                    ["Mesmo ISRC; versão e duração verificadas"]
                    if identity == 'isrc'
                    else ["Título, artista e versão compatíveis"]
                ),
                "match_confidence": "confirmed" if identity == 'isrc' else "probable",
            }
        )
    return sorted(ranked, key=lambda row: row["catalog_score"], reverse=True)


def automatic_catalog(anchor, candidates, *, prefer_best=False):
    if not candidates:
        return None
    best = candidates[0]
    confident = (
        finite_positive(anchor.get('duration_ms'))
        and finite_positive(best.get('duration_ms'))
        and (
            best.get('match_confidence') == 'confirmed'
            or (anchor.get("artists") and best["catalog_score"] >= 0.94)
        )
    )
    if not confident:
        return None
    if (
        not prefer_best
        and len(candidates) > 1
        and best["catalog_score"] - candidates[1]["catalog_score"] < 0.04
    ):
        return None
    return best
