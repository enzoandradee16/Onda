"""Find localized titles using public catalog evidence, with bounded requests."""

from metadata import MetadataError, deezer_record
from record_identity import normalized_isrc, catalog_identity, artist_and_duration_match
from matching import words, version_signature
from output_rules import positive_number


def alternate_records(anchor, client):
    found = []
    seen = set()

    def add(record):
        evidence = catalog_identity(anchor, record)
        title = record.get('title')
        key = (title, tuple(record.get('artists') or []))
        differs = words(title) != words(anchor.get('title')) or record.get(
            'artists'
        ) != anchor.get('artists')
        if evidence and title and differs and key not in seen:
            seen.add(key)
            found.append(dict(record, identity_evidence=evidence))

    isrc = normalized_isrc(anchor.get('isrc'))
    if isrc:
        try:
            data = client.get_json('https://api.deezer.com/track/isrc:' + isrc)
            if str(data.get('id', '')).isdigit() and data.get('title'):
                candidate = deezer_record(
                    data,
                    str(data['id']),
                    'https://www.deezer.com/track/' + str(data['id']),
                )
                if (
                    version_signature(anchor.get('title'))
                    ^ version_signature(candidate.get('title'))
                ) == {'remaster'}:
                    # Confirm release date before accepting an omitted edition label.
                    candidate = client.fetch(candidate['source_url'])
                add(candidate)
        except MetadataError:
            pass
        if found:
            return found
    # Album position is meaningful only within the same release, not the playlist.
    if (
        not words(anchor.get('album'))
        or not positive_number(anchor.get('track_number'))
        or not anchor.get('artists')
    ):
        return found
    query = ' '.join([anchor['artists'][0], anchor['album']])[:300]
    detail_requests = 0
    for provider in ('Deezer', 'Apple / iTunes'):
        try:
            rows = client.search(query, provider, country='us', limit=50)
        except MetadataError:
            continue
        for row in rows:
            if not artist_and_duration_match(anchor, row) or words(
                row.get('album')
            ) != words(anchor['album']):
                continue
            if words(row.get('title')) == words(anchor.get('title')):
                continue
            if (
                not positive_number(row.get('track_number'))
                and provider == 'Deezer'
                and detail_requests < 6
            ):
                detail_requests += 1
                try:
                    row = client.fetch(row['source_url'])
                except MetadataError:
                    continue
            add(row)
            if len(found) >= 2:
                return found
        if found:
            return found
    return found
