"""Bounded local, opt-in recording choices; no credentials or search history."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from contextlib import contextmanager


def identity(record):
    from matching import matching_tokens, words
    data=[sorted(matching_tokens(record.get('title'))), sorted(words(' '.join(record.get('artists') or []))), record.get('duration_ms')]
    return hashlib.sha256(json.dumps(data,ensure_ascii=False).encode()).hexdigest()


class ChoiceStore:
    def __init__(self,path=None):
        root=Path(os.environ.get('ONDA_ALIAS_CACHE_ROOT') or Path(os.environ.get('LOCALAPPDATA') or Path.home()/'.config')/'Onda')
        self.path=Path(path) if path else root/'search-choices.sqlite'

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=2)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS choices (record TEXT, candidate TEXT, accepted INTEGER, updated REAL, PRIMARY KEY(record,candidate))')
            with db:
                yield db
        finally:
            db.close()

    def get(self,record):
        if not self.path.exists():return {}
        try:
            with self._connect() as db:
                return {row[0]:bool(row[1]) for row in db.execute('SELECT candidate, accepted FROM choices WHERE record=? AND updated>?',(identity(record),time.time()-90*86400))}
        except (OSError,sqlite3.Error):return {}

    def set(self,record,candidate,accepted):
        if not isinstance(candidate,str) or not candidate or len(candidate)>500:return
        try:
            with self._connect() as db:
                if accepted:db.execute('DELETE FROM choices WHERE record=? AND accepted=1',(identity(record),))
                db.execute('INSERT OR REPLACE INTO choices VALUES (?,?,?,?)',(identity(record),candidate,int(accepted),time.time()))
                db.execute('DELETE FROM choices WHERE rowid NOT IN (SELECT rowid FROM choices ORDER BY updated DESC LIMIT 500)')
        except (OSError,sqlite3.Error):pass

    def clear(self,record=None):
        if not self.path.exists():return
        try:
            with self._connect() as db:
                if record is None:db.execute('DELETE FROM choices')
                else:db.execute('DELETE FROM choices WHERE record=?',(identity(record),))
        except (OSError,sqlite3.Error):pass
