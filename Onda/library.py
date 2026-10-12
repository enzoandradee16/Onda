"""Local queue/history, without account credentials or session tokens."""
from datetime import datetime
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

JOB_FIELDS = {"url", "mode", "height", "fps", "audio_quality", "folder", "playlist", "playlist_limit", "state", "streaming",
              "selected_catalog_url", "review_metadata", "organization", "duplicate_policy", "confirm_version"}


class LibraryStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS queue (position INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, date TEXT, path TEXT, name TEXT, mode TEXT, source TEXT)")

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
            db.execute("DELETE FROM queue")
            db.executemany("INSERT INTO queue VALUES (?, ?)", rows)

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
        with self.connect() as db:
            db.execute("INSERT INTO history(date,path,name,mode,source) VALUES (?,?,?,?,?)",
                       (datetime.now().astimezone().isoformat(timespec="seconds"), path, Path(path).stem, mode, source))

    def history(self, query=""):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM history WHERE instr(lower(name),lower(?))>0 ORDER BY id DESC LIMIT 1000", (query,))]

    def clear_history(self):
        with self.connect() as db:
            db.execute("DELETE FROM history")
