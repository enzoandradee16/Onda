"""Bounded, asynchronous artwork loading for visible queue cards."""

import queue
import threading
from collections import OrderedDict


class QueueArtwork:
    def __init__(self):
        self.requests = queue.Queue(maxsize=64)
        self.results = queue.Queue(maxsize=64)
        self.cache = OrderedDict()
        self.pending = set()
        self.stopped = threading.Event()
        self.thread = None

    def get(self, url):
        if not isinstance(url, str) or not url.startswith('https://'):
            return None
        if url in self.cache:
            self.cache.move_to_end(url)
            return self.cache[url]
        if url not in self.pending and not self.stopped.is_set():
            try:
                self.requests.put_nowait(url)
            except queue.Full:
                return None
            self.pending.add(url)
            if self.thread is None:
                self.thread = threading.Thread(target=self.run, daemon=True)
                self.thread.start()
        return None

    def run(self):
        from catalog_ui import cached_cover_png

        while not self.stopped.is_set():
            try:
                url = self.requests.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                data = cached_cover_png(url)
            except Exception:
                data = None
            if self.stopped.is_set():
                return
            while not self.stopped.is_set():
                try:
                    self.results.put((url, data), timeout=0.2)
                    break
                except queue.Full:
                    continue

    def poll(self):
        while True:
            try:
                url, data = self.results.get_nowait()
            except queue.Empty:
                break
            self.pending.discard(url)
            self.cache[url] = data
            while len(self.cache) > 64:
                self.cache.popitem(last=False)

    def shutdown(self):
        self.stopped.set()
