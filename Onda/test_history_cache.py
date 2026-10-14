import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from history_details import history_details, _cached_details

class HistoryCacheTests(unittest.TestCase):
    def test_reuses_details_but_refreshes_changed_or_removed_files(self):
        _cached_details.cache_clear()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"track.mp3"
            path.write_bytes(b"original")
            with patch("history_details.read_audio",return_value={"title":"Original"}) as read, patch("history_details.cover_preview",return_value=""):
                self.assertEqual(history_details(path)["title"],"Original")
                history_details(path)
                self.assertEqual(read.call_count,1)
                path.write_bytes(b"changed!")
                stat=path.stat();os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns+1000000))
                read.return_value={"title":"Changed"}
                self.assertEqual(history_details(path)["title"],"Changed")
                self.assertEqual(read.call_count,2)
                path.unlink()
                self.assertIn("removido",history_details(path)["note"])
