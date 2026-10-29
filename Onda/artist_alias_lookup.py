"""Bounded MusicBrainz aliases, verified against a recording and cached locally."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import requests
from matching import words, version_signature

MBID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
POSITIVE_TTL = 30 * 86400
NEGATIVE_TTL = 86400


class LookupUnavailable(Exception):
    pass


def cache_path():
    android = os.environ.get('ONDA_ALIAS_CACHE_ROOT')
    base = (
        Path(android)
        if android
        else Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.cache') / 'Onda'
    )
    return base / 'artist-aliases.sqlite3'


def context_key(record):
    fields = [
        record.get('artists', [None])[0] if record.get('artists') else None,
        record.get('title'),
        record.get('album'),
        record.get('duration_ms'),
        record.get('isrc'),
        record.get('spotify_artist_ids'),
    ]
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()


def spotify_artist_key(record):
    values = record.get('spotify_artist_ids') or []
    return (
        'spotify:' + values[0]
        if values
        and isinstance(values[0], str)
        and re.fullmatch('[A-Za-z0-9]{22}', values[0])
        else None
    )


def valid_groups(groups):
    if not isinstance(groups, list):
        return []
    result = []
    for row in groups[:1]:
        if not isinstance(row, dict) or not MBID.fullmatch(
            str(row.get('artist_id', ''))
        ):
            continue
        aliases = row.get('aliases')
        if (
            not isinstance(aliases, list)
            or not all(
                isinstance(name, str) and 1 < len(name) <= 128 for name in aliases
            )
            or len(aliases) > 20
        ):
            continue
        result.append(
            {
                'artist_id': row['artist_id'],
                'source_url': 'https://musicbrainz.org/artist/' + row['artist_id'],
                'aliases': aliases,
                'verified_by': row.get('verified_by', 'recording'),
            }
        )
    return result


class AliasCache:
    def __init__(self, path=None):
        self.path = Path(path) if path else cache_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute(
                'CREATE TABLE IF NOT EXISTS aliases (key TEXT PRIMARY KEY, expires REAL NOT NULL, data TEXT NOT NULL)'
            )
            db.execute(
                'CREATE TABLE IF NOT EXISTS gate (id INTEGER PRIMARY KEY, next REAL NOT NULL)'
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=3)
        try:
            with db:
                yield db
        finally:
            db.close()

    def read(self, key):
        with self.connect() as db:
            row = db.execute(
                'SELECT expires,data FROM aliases WHERE key=?', (key,)
            ).fetchone()
        if not row or row[0] < time.time():
            return None
        try:
            return valid_groups(json.loads(row[1]))
        except (ValueError, TypeError):
            return None

    def write(self, key, groups):
        with self.connect() as db:
            db.execute('DELETE FROM aliases WHERE expires<?', (time.time(),))
            db.execute(
                'INSERT OR REPLACE INTO aliases VALUES(?,?,?)',
                (
                    key,
                    time.time() + (POSITIVE_TTL if groups else NEGATIVE_TTL),
                    json.dumps(groups, ensure_ascii=False),
                ),
            )
            db.execute(
                'DELETE FROM aliases WHERE key IN (SELECT key FROM aliases ORDER BY expires DESC LIMIT -1 OFFSET 2000)'
            )

    def request_slot(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT next FROM gate WHERE id=1').fetchone()
            now = time.time()
            slot = max(now, row[0] if row else now)
            if slot - now > 8:
                raise LookupUnavailable()
            db.execute('INSERT OR REPLACE INTO gate VALUES(1,?)', (slot + 1.1,))
        if slot > now:
            time.sleep(slot - now)

    def cool_down(self, seconds):
        with self.connect() as db:
            db.execute(
                'INSERT INTO gate VALUES(1,?) ON CONFLICT(id) DO UPDATE SET next=MAX(gate.next,excluded.next)',
                (time.time() + seconds,),
            )


def get_json(path, params, cache):
    cache.request_slot()
    with requests.get(
        'https://musicbrainz.org/ws/2/' + path,
        params=dict(params, fmt='json'),
        headers={
            'User-Agent': 'ONDA/1.1.3 (https://github.com/enzoandradee16/Onda)',
            'Accept': 'application/json',
        },
        timeout=(4, 8),
        allow_redirects=False,
        stream=True,
    ) as response:
        if response.status_code in (429, 503):
            retry = response.headers.get('Retry-After', '60')
            cache.cool_down(max(60, min(3600, int(retry))) if retry.isdigit() else 60)
            raise LookupUnavailable()
        if response.status_code != 200:
            raise LookupUnavailable()
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > 1048576:
                raise LookupUnavailable()
        value = json.loads(data)
        if not isinstance(value, dict):
            raise LookupUnavailable()
        return value


def quoted(text):
    return '"' + re.sub(r'[^\w\s-]', ' ', str(text or ''), flags=re.UNICODE)[:150] + '"'


def compatible_recording(anchor, row):
    from record_identity import normalized_isrc

    if words(anchor.get('title')) != words(row.get('title')) or version_signature(
        anchor.get('title')
    ) != version_signature(row.get('title')):
        return False
    duration, other = anchor.get('duration_ms'), row.get('length')
    if not all(
        isinstance(value, (int, float)) and value > 0 for value in (duration, other)
    ):
        return False
    if abs(duration - other) > max(4000, min(10000, duration * 0.03)):
        return False
    isrc = normalized_isrc(anchor.get('isrc'))
    # Search results alone do not prove an ISRC; only an actual returned identifier does.
    if isrc and isrc in {normalized_isrc(value) for value in row.get('isrcs', [])}:
        return True
    album = words(anchor.get('album'))
    return bool(
        album
        and any(
            words(release.get('title')) == album
            for release in row.get('releases', [])
            if isinstance(release, dict)
        )
    )


def discover_aliases(record, *, cache=None, fetch=None):
    if (
        not record.get('artists')
        or not record.get('title')
        or not record.get('duration_ms')
        or not record.get('album')
    ):
        return []
    try:
        cache = cache or AliasCache()
        key = context_key(record)
        artist_key = spotify_artist_key(record)
        for lookup_key in (artist_key, key):
            if lookup_key:
                saved = cache.read(lookup_key)
                if saved is not None:
                    return saved
        fetch = fetch or get_json
        artist = record['artists'][0]
        query = 'recording:' + quoted(record['title']) + ' AND artist:' + quoted(artist)
        if record.get('album'):
            query += ' AND release:' + quoted(record['album'])
        response = fetch('recording', {'query': query, 'limit': 5}, cache)
        rows = response.get('recordings', [])
        if not isinstance(rows, list):
            return []
        candidates = {}
        for row in rows[:5]:
            if not isinstance(row, dict) or not compatible_recording(record, row):
                continue
            credits = [
                credit
                for credit in row.get('artist-credit', [])
                if isinstance(credit, dict) and isinstance(credit.get('artist'), dict)
            ]
            # Only the primary performer; a guest/composer is not an alias of the artist.
            if not credits:
                continue
            credit = credits[0]
            identity = credit['artist'].get('id', '')
            if not MBID.fullmatch(str(identity)):
                continue
            candidates[identity] = True
        # Homonyms with indistinguishable recordings must not be merged.
        searched_artist = False
        if not candidates:
            # Recording search does not always index a legal/stage-name alias.
            artists = fetch(
                'artist',
                {
                    'query': 'artist:' + quoted(artist) + ' OR alias:' + quoted(artist),
                    'limit': 5,
                },
                cache,
            ).get('artists', [])
            for row in artists[:5]:
                if not isinstance(row, dict) or not MBID.fullmatch(
                    str(row.get('id', ''))
                ):
                    continue
                names = [row.get('name')] + [
                    alias.get('name')
                    for alias in row.get('aliases', [])
                    if isinstance(alias, dict)
                ]
                if any(
                    words(name) == words(artist)
                    for name in names
                    if isinstance(name, str)
                ):
                    candidates[row['id']] = True
            searched_artist = True
        if len(candidates) != 1:
            cache.write(key, [])
            return []
        identity = next(iter(candidates))
        profile = fetch('artist/' + identity, {'inc': 'aliases+url-rels'}, cache)
        if profile.get('id') != identity:
            return []
        names = [profile.get('name')] + [
            alias.get('name')
            for alias in profile.get('aliases', [])
            if isinstance(alias, dict)
            and alias.get('type') in ('Artist name', 'Legal name')
        ]
        names = list(
            dict.fromkeys(
                name
                for name in names
                if isinstance(name, str) and 1 < len(name) <= 128 and bool(words(name))
            )
        )
        if not any(words(name) == words(artist) for name in names):
            cache.write(key, [])
            return []
        names = list(dict.fromkeys([artist] + names))[:20]
        if searched_artist:
            query = (
                'recording:'
                + quoted(record['title'])
                + ' AND arid:'
                + identity
                + ' AND release:'
                + quoted(record['album'])
            )
            rows = fetch('recording', {'query': query, 'limit': 5}, cache).get(
                'recordings', []
            )

            def primary_id(row):
                credits = [
                    credit
                    for credit in row.get('artist-credit', [])
                    if isinstance(credit, dict)
                ]
                return (credits[0].get('artist') or {}).get('id') if credits else None

            if not any(
                isinstance(row, dict)
                and primary_id(row) == identity
                and compatible_recording(record, row)
                for row in rows[:5]
            ):
                cache.write(key, [])
                return []
        group = {
            'artist_id': identity,
            'source_url': 'https://musicbrainz.org/artist/' + identity,
            'aliases': names,
            'verified_by': 'title-duration-album',
        }
        groups = valid_groups([group])
        cache.write(key, groups)
        if artist_key:
            wanted = 'https://open.spotify.com/artist/' + artist_key.split(':', 1)[1]
            if any(
                isinstance(relation, dict)
                and (relation.get('url') or {}).get('resource', '').rstrip('/')
                == wanted
                for relation in profile.get('relations', [])
            ):
                cache.write(artist_key, groups)
        return groups
    except requests.RequestException:
        try:
            cache.cool_down(60)
        except (AttributeError, OSError, sqlite3.Error):
            pass
        return []
    except (
        LookupUnavailable,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OSError,
        sqlite3.Error,
    ):
        return []
