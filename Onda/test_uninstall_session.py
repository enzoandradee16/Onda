"""Keep Windows uninstall cleanup in sync with actual playback persistence."""

import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from playback_session import FIELDS, save


class UninstallSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workspace = SimpleNamespace(
            store=SimpleNamespace(path=self.root / 'settings.json'),
            options=dict.fromkeys(FIELDS),
            bridge=SimpleNamespace(
                playlist=[{'id': 'track', 'restore_seconds': 42}],
                _prepared={},
                queue_index=0,
                model=None,
                position=0,
                phase=0,
                _params=(45, 20, 80, True),
                queue_repeat=False,
                queue_shuffle=False,
                _shuffle_order=[],
                _queue_history=[],
            ),
        )
        recipe = (
            Path(__file__).resolve().parents[1] / 'empacotamento/Onda.iss'
        ).read_text(encoding='utf-8')
        cleanup = recipe.split('procedure RemoveUserData;', 1)[1]
        allowlist = re.search(r'Names := \[(.*?)\];', cleanup, re.S).group(1)
        self.cleanup_names = set(re.findall(r"'([^']+)'", allowlist))

    def test_saved_session_is_covered_by_uninstall_data_cleanup(self):
        save(self.workspace, strict=True)
        files = {path.name for path in self.root.iterdir()}
        self.assertTrue(files)
        self.assertLessEqual(files, self.cleanup_names)

    def test_interrupted_session_save_is_also_covered_by_cleanup(self):
        with patch('pathlib.Path.replace', side_effect=OSError('Interrupted save')):
            save(self.workspace)
        files = {path.name for path in self.root.iterdir()}
        self.assertTrue(files)
        self.assertLessEqual(files, self.cleanup_names)
