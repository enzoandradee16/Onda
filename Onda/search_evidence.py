"""Conservative evidence shared by desktop and Android music matching."""

import re
from matching import words, version_signature


def explicit_conflict(anchor, other):
    left, right = anchor.get("explicit"), other.get("explicit")
    tokens = words(other.get("title"))
    anchor_tokens = words(anchor.get('title'))
    if not isinstance(left, bool):
        if 'clean' in anchor_tokens and 'clean' not in tokens:
            left = False
        elif 'explicit' in anchor_tokens and 'explicit' not in tokens:
            left = True
    if not isinstance(right, bool):
        if "clean" in tokens and "clean" not in words(anchor.get("title")):
            right = False
        elif "explicit" in tokens and "explicit" not in words(anchor.get("title")):
            right = True
    return isinstance(left, bool) and isinstance(right, bool) and left != right


def album_core(value):
    # Only packaging labels are removed. Live/remix/remaster remain significant.
    value = re.sub(
        r"[\(\[]\s*(?:deluxe|expanded|anniversary|special|bonus)(?:\s+(?:edition|version|tracks?))?\s*[\)\]]",
        "",
        value or "",
        flags=re.I,
    )
    return words(value)


def release_year(record):
    match = re.match(r"(\d{4})(?:-|$)", str(record.get("release_date") or ""))
    return int(match[1]) if match else None


def video_identity(candidate):
    # Structured music fields are usable only for auto-generated Topic uploads.
    # Arbitrary descriptions and verification badges do not prove track identity.
    channel = candidate.get("channel") or candidate.get("uploader") or ""
    if (
        not channel.endswith(" - Topic")
        or not candidate.get("track")
        or not candidate.get("artist")
    ):
        return candidate
    from edition_evidence import edition_conflicts

    if version_signature(candidate.get("title")) != version_signature(
        candidate["track"]
    ) or edition_conflicts(candidate, dict(title=candidate['track'])):
        return candidate
    return dict(candidate, title=candidate["track"])


def presentation_title(anchor, candidate):
    """Remove bounded presentation syntax; retain the raw title for edition checks."""
    from matching import matching_tokens, words, version_signature
    from edition_evidence import recording_title

    title = recording_title(candidate)
    expected = matching_tokens(recording_title(anchor))
    album = album_search_title(anchor.get('album'))
    album_tokens = matching_tokens(album)
    artists = [words(name) for name in anchor.get('artists') or []]

    def labels(value):
        value = re.sub(
            r'\((?:original score|original soundtrack(?: track)?|colonna sonora originale|high quality audio|hd audio)\)',
            '',
            value,
            flags=re.I,
        )

        def from_album(match):
            tokens = words(match[1].strip(' "\''))
            return '' if tokens and tokens <= words(anchor.get('album')) else match[0]

        value = re.sub(r'\(from\s+([^()]*)\)', from_album, value, flags=re.I)

        # A short bracketed music-brand label is presentation, not a version.
        def brand(match):
            label = match[1]
            return (
                ''
                if len(label) <= 40
                and words(label)
                and label.lower().endswith(' music')
                and not version_signature(label)
                else match[0]
            )

        return re.sub(r'\[([^]\n]+)\]', brand, value)

    title = labels(title)
    title = re.sub(
        r'^\s*(?:film music|retro tv music|show televisivo italiano)\s*\|\s*',
        '',
        title,
        flags=re.I,
    )
    campaign = re.match(
        r'^#([^\s]+)\s*[-–—]\s*(.*?)\s*[-–—]\s*the story of\b.*$', title, re.I
    )
    if campaign and re.search(r'anniversary\s+edition', campaign[2], re.I):
        name = re.sub(r'\d+$', '', campaign[1]).casefold()
        if any(
            name == ''.join(re.findall(r'[^\W_]+', artist.casefold()))
            for artist in anchor.get('artists') or []
        ):
            title = re.sub(
                r'\((?:\d+(?:st|nd|rd|th)\s+)?anniversary edition\)',
                '',
                campaign[2],
                flags=re.I,
            ).strip()
    # Credit - cue - by performer (Original Score) is a common soundtrack format.
    parts = re.split(r'\s+[-–—]\s+', title)
    if len(parts) == 3 and re.match(r'^by\s+', parts[2], re.I):
        author = words(re.sub(r'^by\s+', '', parts[2], flags=re.I))
        if (
            any(author == artist for artist in artists)
            and matching_tokens(parts[1]) == expected
        ):
            return parts[1]
    # Film/actor credits may surround a cue, but require the known album too.
    blocks = re.split(r'[●•·]', title)
    if len(blocks) >= 3 and album_tokens:
        cleaned = [matching_tokens(labels(block)) for block in blocks]
        exact = next(
            (index for index, tokens in enumerate(cleaned) if tokens == expected), None
        )
        if exact is not None and any(
            tokens == album_tokens
            for index, tokens in enumerate(cleaned)
            if index != exact
        ):
            return blocks[exact].strip()
        for index, tokens in enumerate(cleaned):
            if (
                expected <= tokens
                and album_tokens <= tokens
                and tokens <= expected | album_tokens
            ):
                if any(
                    any(other == artist for artist in artists)
                    for j, other in enumerate(cleaned)
                    if j != index
                ):
                    return recording_title(anchor)
    return title


def album_search_title(value):
    return re.sub(
        r'\([^()]*(?:original motion picture soundtracks?|colonna sonora originale|original soundtrack)[^()]*\)',
        '',
        value or '',
        flags=re.I,
    ).strip()
