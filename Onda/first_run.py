"""One-time, per-user welcome state independent of saved preferences."""

from pathlib import Path


class FirstRunStore:
    def __init__(self, path):
        self.path = Path(path)

    def claim(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("x", encoding="utf-8") as output:
                output.write('{"welcome_seen": true, "version": 1}\n')
        except FileExistsError:
            return False
        return True
