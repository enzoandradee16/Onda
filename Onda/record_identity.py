"""Evidence for translated catalog titles; never use playlist position as track number."""

import re
from matching import words, version_signature
from search_evidence import explicit_conflict, release_year
from output_rules import positive_number
from edition_evidence import (
    finite_positive,
    same_release,
    edition_conflicts,
    recording_title,
)


def normalized_isrc(value):
    value = re.sub(r'[-\s]', '', str(value or '')).upper()
    return value if re.fullmatch(r'[A-Z]{2}[A-Z0-9]{3}[0-9]{7}', value) else ''


def duration_match(anchor, other):
    duration, other_duration = anchor.get('duration_ms'), other.get('duration_ms')
    if not all(finite_positive(value) for value in (duration, other_duration)):
        return False
    return abs(duration - other_duration) <= max(
        4000, min(10000, min(duration, other_duration) * 0.03)
    )


def artist_and_duration_match(anchor, other):
    artists = [
        name
        for name in anchor.get('artists') or []
        if isinstance(name, str) and name.strip()
    ]
    other_artist = words(' '.join(other.get('artists') or []))
    from artist_aliases import artist_overlap

    if (
        not artists
        or max(artist_overlap(name, other_artist, anchor) for name in artists) < 0.85
    ):
        return False
    return duration_match(anchor, other)


def catalog_identity(anchor, other):
    artist_match = artist_and_duration_match(anchor, other)
    if not artist_match:
        # A different artist spelling needs the same recording ID AND title/time.
        isrc = normalized_isrc(anchor.get('isrc'))
        if not (
            isrc
            and isrc == normalized_isrc(other.get('isrc'))
            and words(anchor.get('title')) == words(other.get('title'))
            and words(anchor.get('title'))
            and duration_match(anchor, other)
        ):
            return None
    if explicit_conflict(anchor, other) or edition_conflicts(anchor, other):
        return None
    isrc, other_isrc = normalized_isrc(anchor.get('isrc')), normalized_isrc(
        other.get('isrc')
    )
    left, right = version_signature(recording_title(anchor)), version_signature(
        recording_title(other)
    )
    if left != right:
        # Catalogs may omit a remaster label on the same recording and release.
        if not (
            (left ^ right) == {'remaster'}
            and isrc
            and isrc == other_isrc
            and same_release(anchor, other)
        ):
            return None
    if isrc and other_isrc:
        return 'isrc' if isrc == other_isrc else None
    year, other_year = release_year(anchor), release_year(other)
    if year and other_year and abs(year - other_year) > 1:
        return None
    # Different editions can reorder tracks; only ISRC may bridge those.
    album, other_album = words(anchor.get('album')), words(other.get('album'))
    track, other_track = positive_number(anchor.get('track_number')), positive_number(
        other.get('track_number')
    )
    if (
        album
        and album == other_album
        and track
        and track == other_track
        and positive_number(anchor.get('disc_number'), 1)
        == positive_number(other.get('disc_number'), 1)
    ):
        return 'album-track'
    return None
