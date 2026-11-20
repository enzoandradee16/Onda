import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

import mobile_tool_updates as updates


class Response:
    status_code = 200

    def __init__(self, data=None, content=b''):
        self.data, self.content = data, content

    def raise_for_status(self):
        pass

    def json(self):
        return self.data

    def iter_content(self, _):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class Client:
    def __init__(self, corrupt=False, dependency=None, version='0.8'):
        self.corrupt, self.dependency = corrupt, dependency
        self.version, self.downloads = version, []

    def get(self, url, **_):
        if url.endswith('/json'):
            name = url.split('/')[-2]
            body = self.wheel(name)
            return Response(
                dict(
                    info=dict(
                        version=self.version,
                        requires_python='>=3.10',
                        requires_dist=[self.dependency] if self.dependency else [],
                    ),
                    urls=[
                        dict(
                            filename=name + '-0.8-py3-none-any.whl',
                            url='https://files.pythonhosted.org/' + name,
                            digests=dict(sha256=hashlib.sha256(body).hexdigest()),
                        )
                    ],
                )
            )
        self.downloads.append(url)
        return Response(
            content=b'broken' if self.corrupt else self.wheel(url.split('/')[-1])
        )

    def wheel(self, name):
        body = io.BytesIO()
        with zipfile.ZipFile(body, 'w') as archive:
            archive.writestr(
                zipfile.ZipInfo(name.replace('-', '_') + '/__init__.py'), ''
            )
            archive.writestr(
                zipfile.ZipInfo(name.replace('-', '_') + '-0.8.dist-info/METADATA'),
                'Name: ' + name + '\nVersion: ' + self.version + '\n',
            )
        return body.getvalue()


class ToolUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = patch.object(updates.metadata, 'version', return_value='0.7')
        self.base.start()
        self.addCleanup(self.base.stop)

    def test_complete_generation_commits_once(self):
        versions = updates.prepare(self.root, client=Client())
        folder = self.root / 'tools/python-updates'
        active = (folder / 'active').read_text()
        self.assertEqual(set(versions), set(updates.PACKAGES))
        client = Client()
        updates.prepare(self.root, client=client)
        self.assertEqual((folder / 'active').read_text(), active)
        self.assertEqual(client.downloads, [])
        self.assertFalse(list(folder.glob('pending-*')))

    def test_failed_download_keeps_previous_generation(self):
        updates.prepare(self.root, client=Client())
        pointer = self.root / 'tools/python-updates/active'
        previous = pointer.read_text()
        with self.assertRaisesRegex(ValueError, 'verificação'):
            updates.prepare(self.root, client=Client(corrupt=True, version='0.8.1'))
        self.assertEqual(pointer.read_text(), previous)

    def test_incompatible_dependency_never_activates(self):
        with self.assertRaisesRegex(ValueError, 'incompatível'):
            updates.prepare(self.root, client=Client(dependency='requests>=9'))
        self.assertFalse((self.root / 'tools/python-updates/active').exists())

    def test_new_apk_and_tampering_reject_cached_update(self):
        updates.prepare(self.root, client=Client())
        with patch.object(updates.metadata, 'version', return_value='0.9'):
            self.assertFalse(updates.activate(self.root))
        folder = self.root / 'tools/python-updates'
        generation = (folder / 'active').read_text()
        (folder / generation / 'mutagen.whl').write_bytes(b'bad')
        self.assertFalse(updates.activate(self.root))

    def test_rejects_untrusted_hosts(self):
        with self.assertRaises(ValueError):
            updates._get(
                Client(), 'https://example.com/package', 'files.pythonhosted.org'
            )

    def test_button_repairs_a_corrupted_generation(self):
        updates.prepare(self.root, client=Client())
        folder = self.root / 'tools/python-updates'
        previous = (folder / 'active').read_text()
        (folder / previous / 'mutagen.whl').write_bytes(b'bad')
        client = Client()
        updates.prepare(self.root, client=client)
        self.assertNotEqual((folder / 'active').read_text(), previous)
        self.assertEqual(len(client.downloads), 1)

    def test_invalid_manifest_is_replaced_by_verified_downloads(self):
        updates.prepare(self.root, client=Client())
        folder = self.root / 'tools/python-updates'
        generation = (folder / 'active').read_text()
        (folder / generation / 'manifest.json').write_text('[]', encoding='utf8')
        client = Client()
        updates.prepare(self.root, client=client)
        self.assertEqual(len(client.downloads), len(updates.PACKAGES))
        self.assertNotEqual((folder / 'active').read_text(), generation)

    def test_only_abandoned_staging_is_cleaned(self):
        folder = self.root / 'tools/python-updates'
        old = folder / 'pending-old'
        fresh = folder / 'pending-fresh'
        old.mkdir(parents=True)
        fresh.mkdir()
        os.utime(old, (time.time() - 90000, time.time() - 90000))
        updates.prepare(self.root, client=Client())
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_desktop_button_includes_the_extended_package_set(self):
        import threading
        import qt_operations_ui
        from types import SimpleNamespace

        with patch.object(
            qt_operations_ui.subprocess,
            'run',
            return_value=SimpleNamespace(returncode=0),
        ) as run:
            result = qt_operations_ui.perform(
                'update_tools',
                {'_root': self.root},
                threading.Event(),
                lambda *a, **k: None,
            )
        command = run.call_args.args[0]
        for prefix in (
            'mutagen',
            'requests',
            'PyYAML',
            'yt-dlp-ejs',
            'Pillow',
            'gallery-dl',
            'yt-dlp[',
        ):
            self.assertTrue(any(arg.startswith(prefix) for arg in command), prefix)
        self.assertTrue(result['report']['restart_required'])
        if __import__('sys').version_info >= (3, 15):
            self.assertIn('yt-dlp[curl-cffi]', command)
            self.assertIn('brotlicffi>=1.2.0.1', command)
            self.assertEqual(run.call_args.kwargs['env']['PYYAML_FORCE_LIBYAML'], '0')

    def test_native_or_traversal_wheel_is_rejected(self):
        for name in ('../outside.py', 'module/native.so', 'module/startup.pth'):
            path = self.root / 'invalid.whl'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(name, '')
            with self.assertRaises(ValueError):
                updates._verify_wheel(path, 'mutagen', '0.8')


if __name__ == '__main__':
    unittest.main()
