"""Ordered queue checkpoints; background progress writes never access live jobs."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading
from library import JOB_FIELDS


class QueuePersistence:
    def __init__(self, library):
        self.library = library
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='ONDA-queue-save'
        )
        self.lock = threading.Lock()
        self.generation = 0

    def submit(self, jobs):
        snapshot = [
            deepcopy({key: value for key, value in job.items() if key in JOB_FIELDS})
            for job in jobs
            if job.get('state') != 'Concluído'
        ]
        with self.lock:
            self.generation += 1
            generation = self.generation

        def write():
            if generation == self.generation:
                self.library.save_queue(snapshot)

        return self.executor.submit(write)

    def close(self):
        self.executor.shutdown(wait=True)
