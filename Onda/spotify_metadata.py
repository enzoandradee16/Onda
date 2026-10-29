"""Spotify identity is primary only for validated direct Spotify track links."""

from copy import deepcopy
from metadata import parse_link, MetadataError, spotify_record

FIELDS = (
    "title",
    "artists",
    "album",
    "album_artists",
    "release_date",
    "duration_ms",
    "track_number",
    "disc_number",
    "genre",
    "isrc",
    "explicit",
    "cover_url",
    "preview_url",
)


def missing(value):
    return value is None or value == "" or value == [] or value == {}


def spotify_track(url):
    try:
        service, identity, _, canonical = parse_link(url)
        return (identity, canonical) if service == "spotify" else None
    except (MetadataError, ValueError, TypeError, AttributeError):
        return None


def original_metadata(record):
    result = deepcopy(record)
    result["metadata_sources"] = {
        key: {"platform": "Spotify", "source_url": record["source_url"]}
        for key in FIELDS
        if not missing(record.get(key))
    }
    result["metadata_sources"].update(deepcopy(record.get("metadata_sources") or {}))
    return result


def supplement_metadata(anchor, other, evidence):
    result = original_metadata(anchor)
    result["metadata_sources"].update(deepcopy(anchor.get("metadata_sources") or {}))
    added = []
    for key in FIELDS:
        if missing(result.get(key)) and not missing(other.get(key)):
            result[key] = deepcopy(other[key])
            added.append(key)
            result["metadata_sources"][key] = {
                "platform": other["platform"],
                "source_url": other["source_url"],
            }
    result["catalog_match"] = deepcopy(evidence)
    result["requested_source_url"] = anchor["source_url"]
    result["metadata_supplements"] = deepcopy(anchor.get("metadata_supplements") or [])
    if added:
        result["metadata_supplements"].append(
            {
                "platform": other["platform"],
                "source_url": other["source_url"],
                "fields": added,
            }
        )
    return result


def source_label(record):
    providers = list(
        dict.fromkeys(
            row["platform"]
            for row in record.get("metadata_supplements", [])
            if row.get("fields")
        )
    )
    return (
        "Spotify" + (" + " + " / ".join(providers) if providers else "")
        if record.get("platform") == "Spotify"
        else record["platform"]
    )


def prepare_spotify_config(config, account):
    """Run off the UI thread. Send normalized metadata to workers, never OAuth tokens."""
    link = spotify_track(config.get("url"))
    if not link or account is None or not account.connected:
        return config
    cached = config.get("catalog_record")
    if cached:
        from spotify_search import cached_record

        cached = cached_record(cached, config['url'])
        if all(
            not missing(cached.get(key))
            for key in (
                'title',
                'artists',
                'album',
                'cover_url',
                'duration_ms',
                'release_date',
                'track_number',
            )
        ):
            return config
    try:
        data = account.get("tracks/" + link[0])
        record = spotify_record(data, link[0], link[1])
        if record.get("artists"):
            if cached:
                record = {
                    **record,
                    **{
                        key: value
                        for key, value in cached.items()
                        if not missing(value)
                    },
                }
            return dict(config, catalog_record=record)
    except MetadataError:
        pass
    return config
