"""Local queue/history, without account credentials or session tokens."""
from datetime import datetime
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

JOB_FIELDS = {"output_files", "queue_original", "_queue_estimate", "failure_original_url", "last_error", "filename_template", "detect_duplicates", "work_id", "normalize_volume", "resume_downloads", "url", "mode", "height", "fps", "audio_quality", "folder", "playlist", "playlist_limit", "state", "streaming",
              "selected_catalog_url", "review_metadata", "organization", "duplicate_policy", "confirm_version", "playlist_title", "image_options", "catalog_record", "display_name", "queue_info", "_pause_reason"}


class LibraryStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS queue (position INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, date TEXT, path TEXT, name TEXT, mode TEXT, source TEXT)")
            columns={row[1] for row in db.execute('PRAGMA table_info(history)')}
            if 'source_key' not in columns:db.execute('ALTER TABLE history ADD COLUMN source_key TEXT')
            if 'mode_key' not in columns:db.execute('ALTER TABLE history ADD COLUMN mode_key TEXT')
            from duplicate_links import source_key
            cursor=db.execute('SELECT id,source,mode FROM history WHERE source_key IS NULL OR mode_key IS NULL')
            while batch:=cursor.fetchmany(500):
                db.executemany('UPDATE history SET source_key=?,mode_key=? WHERE id=?',
                               ((source_key(source),str(mode or '').lower(),identity) for identity,source,mode in batch))
            db.execute('CREATE INDEX IF NOT EXISTS history_duplicate_key ON history(source_key,mode_key,id DESC)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save_queue(self, jobs):
        rows = []
        for job in jobs:
            if job.get("state") == "Concluído":
                continue
            data = {key: value for key, value in job.items() if key in JOB_FIELDS}
            if data.get("state") == "Em andamento":
                data["state"] = "Na fila"
            rows.append((len(rows), json.dumps(data, ensure_ascii=False)))
        with self.connect() as db:
            previous=dict(db.execute('SELECT position,data FROM queue'))
            changed=[row for row in rows if previous.get(row[0])!=row[1]]
            if changed:
                db.executemany('INSERT INTO queue(position,data) VALUES (?,?) ON CONFLICT(position) DO UPDATE SET data=excluded.data',changed)
            if any(position>=len(rows) for position in previous):
                db.execute('DELETE FROM queue WHERE position>=?',(len(rows),))

    def load_queue(self):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM queue ORDER BY position").fetchall()
        result = []
        for (raw,) in rows:
            try:
                job = json.loads(raw)
                if isinstance(job, dict) and all(isinstance(job.get(k), str) for k in ("url", "folder", "mode")):
                    result.append({key: value for key, value in job.items() if key in JOB_FIELDS})
            except (ValueError, TypeError):
                continue
        return result

    def add_history(self, path, mode, source=""):
        path = str(Path(path).resolve())
        from duplicate_links import source_key
        with self.connect() as db:
            db.execute("INSERT INTO history(date,path,name,mode,source,source_key,mode_key) VALUES (?,?,?,?,?,?,?)",
                       (datetime.now().astimezone().isoformat(timespec="seconds"), path, Path(path).stem, mode, source,source_key(source),str(mode or '').lower()))

    def history(self, query="", kind="Todos"):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            limit=" LIMIT 1000" if kind=="Todos" else ""
            if query:
                # SQLite lower() only folds ASCII; music titles commonly use accents.
                db.create_function('casefold', 1, lambda value: (value or '').casefold(), deterministic=True)
                cursor = db.execute("SELECT id,date,path,name,mode,source FROM history WHERE instr(casefold(name),?)>0 ORDER BY id DESC"+limit, (query.casefold(),))
            else:
                cursor = db.execute("SELECT id,date,path,name,mode,source FROM history ORDER BY id DESC"+limit)
            from platform_info import history_kind
            from itertools import islice
            return list(islice((dict(row) for row in cursor if kind=="Todos" or history_kind(row['mode'],row['path'])==kind),1000))

    def remove_history(self,identity):
        with self.connect() as db:
            db.execute("DELETE FROM history WHERE id=?",(int(identity),))

    def find_duplicate(self, source, mode):
        from duplicate_links import source_key
        key = source_key(source)
        if not key:
            return None
        with self.connect() as db:
            rows=db.execute('SELECT path FROM history WHERE source_key=? AND mode_key=? ORDER BY id DESC',(key,str(mode).lower()))
            return next((path for (path,) in rows if Path(path).is_file()),None)

    def comparison_history(self):
        with self.connect() as db:
            db.row_factory=sqlite3.Row
            return [dict(row) for row in db.execute('SELECT path,source FROM history ORDER BY id DESC')]

    def clear_history(self):
        with self.connect() as db:
            db.execute("DELETE FROM history")
