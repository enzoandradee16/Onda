"""Small, persistable subset of catalog metadata for queue presentation."""

FIELDS = (
    'title',
    'artists',
    'album',
    'cover_url',
    'duration_ms',
    'release_date',
    'genre',
    'track_number',
    'disc_number',
    'platform',
)


def queue_info(record):
    return {
        key: record[key] for key in FIELDS if record.get(key) not in (None, '', [], {})
    }
