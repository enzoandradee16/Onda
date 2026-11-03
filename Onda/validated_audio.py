"""Bounded catalog-to-video references, independent of disposable audio files."""

import json
import hashlib
import re
import sqlite3
import time

from search_choices import ChoiceStore, identity


def reference_key(record):
    # Separate catalog releases and explicit/clean versions even when their
    # title, artist and reported duration happen to be identical.
    data = [
        identity(record),
        str(record.get('source_url') or '').split('?')[0],
        record.get('album'),
        record.get('version'),
        record.get('title_version'),
        record.get('explicit'),
        record.get('isrc'),
    ]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


class ValidatedAudioStore(ChoiceStore):
    def __init__(self, path=None):
        super().__init__(path)
        if path is None:
            self.path = self.path.with_name('validated-audio.sqlite')

    def get(self, record):
        try:
            with self._connect() as db:
                db.execute(
                    'CREATE TABLE IF NOT EXISTS audio (identity TEXT PRIMARY KEY, data TEXT, updated REAL)'
                )
                row = db.execute(
                    'SELECT data FROM audio WHERE identity=?', (reference_key(record),)
                ).fetchone()
                value = json.loads(row[0]) if row else None
                if not isinstance(value, dict):
                    return None
                video = value.get('id')
                if not isinstance(video, str) or not re.fullmatch(
                    r'[A-Za-z0-9_-]{11}', video
                ):
                    return None
                value['source_url'] = 'https://www.youtube.com/watch?v=' + video
                return value
        except (OSError, sqlite3.Error, ValueError, TypeError):
            return None

    def set(self, record, selected):
        try:
            with self._connect() as db:
                db.execute(
                    'CREATE TABLE IF NOT EXISTS audio (identity TEXT PRIMARY KEY, data TEXT, updated REAL)'
                )
                db.execute(
                    'INSERT OR REPLACE INTO audio VALUES (?,?,?)',
                    (reference_key(record), json.dumps(selected), time.time()),
                )
                db.execute(
                    'DELETE FROM audio WHERE rowid NOT IN (SELECT rowid FROM audio ORDER BY updated DESC LIMIT 10000)'
                )
        except (OSError, sqlite3.Error, ValueError, TypeError):
            pass

    def forget(self, record):
        try:
            with self._connect() as db:
                db.execute(
                    'DELETE FROM audio WHERE identity=?', (reference_key(record),)
                )
        except (OSError, sqlite3.Error, TypeError, ValueError):
            pass
