import importlib.util, shutil, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
from app_version import VERSION
from advanced_options import release_update

ROOT = Path(__file__).resolve().parents[1]


class AppVersionTests(unittest.TestCase):
    def test_updater_uses_installed_version_for_equal_release(self):
        from qt_operations_ui import perform

        release = {
            'tag_name': 'v' + VERSION,
            'assets': [
                {
                    'name': 'Onda-' + VERSION + '-Setup-Windows-x64.exe',
                    'browser_download_url': 'https://github.com/enzoandradee16/Onda/releases/download/v'
                    + VERSION
                    + '/setup.exe',
                }
            ],
        }
        with patch(
            'advanced_options.release_update',
            side_effect=lambda platform, current: release_update(
                platform, current, [release]
            ),
        ):
            self.assertFalse(
                perform('app_update', {}, threading.Event(), lambda *a, **k: None)[
                    'available'
                ]
            )

    def test_windows_metadata_matches_canonical_version(self):
        launcher = (ROOT / 'empacotamento/Launcher.cs').read_text(encoding='utf-8')
        installer = (ROOT / 'empacotamento/Onda.iss').read_text(encoding='utf-8')
        self.assertIn('AssemblyInformationalVersion("' + VERSION + '")', launcher)
        self.assertIn('AppVersion=' + VERSION + '\n', installer)
        self.assertIn(
            'OutputBaseFilename=Onda-' + VERSION + '-Setup-Windows-x64', installer
        )

    def test_generator_updates_both_artifacts_and_is_idempotent(self):
        spec = importlib.util.spec_from_file_location(
            'sync_version', ROOT / 'empacotamento/sync_version.py'
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'Onda').mkdir()
            (root / 'empacotamento').mkdir()
            (root / 'Onda/app_version.py').write_text("VERSION = '2.3.4-rc.2'\n")
            for name in ('Launcher.cs', 'Onda.iss'):
                shutil.copy2(
                    ROOT / 'empacotamento' / name, root / 'empacotamento' / name
                )
            self.assertEqual(module.sync_version(root), '2.3.4-rc.2')
            first = {p.name: p.read_bytes() for p in (root / 'empacotamento').iterdir()}
            module.sync_version(root)
            self.assertEqual(
                first,
                {p.name: p.read_bytes() for p in (root / 'empacotamento').iterdir()},
            )
            self.assertIn(
                'AssemblyFileVersion("2.3.4.0")', first['Launcher.cs'].decode()
            )
            self.assertIn('AppVersion=2.3.4-rc.2', first['Onda.iss'].decode())
