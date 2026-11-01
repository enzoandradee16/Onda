"""Coalesced session serialization and atomic disk writes outside the Qt thread."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor


class SessionWriter:
    def __init__(self, target):
        self.target = target
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='ONDA-session'
        )
        self.generation = 0
        self.lock = threading.Lock()
        self.last = None
        self._queue_source = None
        self._queue_json = None

    def submit(self, data):
        with self.lock:
            self.generation += 1
            generation = self.generation

        def write():
            if generation != self.generation:
                return
            raw = self.encode(data)
            if raw == self.last:
                return
            temporary = self.target.with_suffix(f'.{generation}.tmp')
            try:
                temporary.write_text(raw, encoding='utf-8')
                with self.lock:
                    if generation == self.generation:
                        temporary.replace(self.target)
                        self.last = raw
            finally:
                temporary.unlink(missing_ok=True)

        return self.executor.submit(write)

    def encode(self, data):
        # Playback owns an immutable queue snapshot until its next queue change.
        # Position checkpoints must not encode megabytes of unchanged artwork.
        jukebox = data.get('jukebox')
        rows = jukebox.get('queue') if isinstance(jukebox, dict) else None
        if not isinstance(rows, list):
            return json.dumps(data, ensure_ascii=False, allow_nan=False)
        if rows is not self._queue_source:
            encoded = json.dumps(rows, ensure_ascii=False, allow_nan=False)
            self._queue_source, self._queue_json = rows, encoded
        outer = {key: value for key, value in data.items() if key != 'jukebox'}
        inner = {key: value for key, value in jukebox.items() if key != 'queue'}
        outer_json = json.dumps(outer, ensure_ascii=False, allow_nan=False)
        inner_json = json.dumps(inner, ensure_ascii=False, allow_nan=False)
        return (
            outer_json[:-1]
            + (', ' if outer else '')
            + '"jukebox": '
            + inner_json[:-1]
            + (', ' if inner else '')
            + '"queue": '
            + self._queue_json
            + '}}'
        )

    def close(self):
        self.executor.shutdown(wait=True)
