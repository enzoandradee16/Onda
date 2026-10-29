import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

import ffmpeg_runtime as runtime


def archive_bytes(*, omit=None, extra=False):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        for name in runtime.EXECUTABLES:
            if name != omit:
                archive.writestr(
                    f'{runtime.ARCHIVE_ROOT}/bin/{name}', b'MZ-fixture-' + name.encode()
                )
        archive.writestr(f'{runtime.ARCHIVE_ROOT}/LICENSE', 'fixture license')
        archive.writestr(f'{runtime.ARCHIVE_ROOT}/README.txt', 'fixture readme')
        if extra:
            archive.writestr('../../outside.txt', 'do not extract')
    return data.getvalue()


class Response:
    def __init__(self, body):
        self.body = body
        self.headers = {'Content-Length': str(len(body))}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def raise_for_status(self):
        pass

    def iter_content(self, _):
        yield self.body[:50]
        yield self.body[50:]


class Session:
    def __init__(self, body):
        self.body, self.calls = body, 0

    def get(self, *_, **__):
        self.calls += 1
        return Response(self.body)


class RuntimeDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.body = archive_bytes()
        self.hash = hashlib.sha256(self.body).hexdigest()

    def install(self, **options):
        with patch.object(runtime, 'SHA256', self.hash):
            return runtime.download_tools(
                root=self.root, session=Session(self.body), **options
            )

    def test_verified_download_and_cache_reuse_without_network(self):
        session = Session(self.body)
        progress = []
        with patch.object(runtime, 'SHA256', self.hash):
            folder = runtime.download_tools(
                root=self.root,
                session=session,
                progress=lambda *item: progress.append(item),
            )
            second = runtime.download_tools(root=self.root, session=session)
            self.assertEqual(folder, second)
            self.assertEqual(session.calls, 1)
            self.assertEqual(runtime.cached_folder(self.root), folder)
        self.assertEqual(
            set(p.name for p in folder.iterdir()),
            set(runtime.EXECUTABLES) | {'LICENSE.txt', 'README.txt', 'verified.json'},
        )
        self.assertTrue(progress)
        self.assertFalse(list(folder.parent.glob('.onda-download-*')))

    def test_bad_hash_never_installs_executables(self):
        with self.assertRaisesRegex(ValueError, 'verificação'):
            runtime.download_tools(root=self.root, session=Session(self.body))
        self.assertIsNone(runtime.cached_folder(self.root))
        self.assertFalse(list(self.root.rglob('*.exe')))

    def test_missing_ffplay_rejected_before_install(self):
        self.body = archive_bytes(omit='ffplay.exe')
        self.hash = hashlib.sha256(self.body).hexdigest()
        with self.assertRaisesRegex(ValueError, 'incompleto'):
            self.install()
        self.assertFalse(list(self.root.rglob('*.exe')))

    def test_archive_cannot_write_outside_allowlist(self):
        self.body = archive_bytes(extra=True)
        self.hash = hashlib.sha256(self.body).hexdigest()
        folder = self.install()
        self.assertTrue(runtime.complete_folder(folder))
        self.assertFalse(list(self.root.parent.glob('outside.txt')))
        self.assertFalse(list(self.root.rglob('outside.txt')))

    def test_cancel_interrupts_and_cleans_partial_download(self):
        cancel = threading.Event()

        def progress(done, *_):
            if done:
                cancel.set()

        with self.assertRaises(runtime.DownloadCancelled):
            self.install(progress=progress, cancel=cancel)
        self.assertFalse(list(self.root.rglob('*.exe')))
        self.assertFalse(list(self.root.rglob('ffmpeg.zip')))

    def test_corrupt_cache_is_downloaded_again(self):
        folder = self.install()
        (folder / 'ffmpeg.exe').write_bytes(b'truncated')
        with patch.object(runtime, 'SHA256', self.hash):
            self.assertIsNone(runtime.cached_folder(self.root))
        repaired = self.install()
        self.assertEqual(
            (repaired / 'ffmpeg.exe').read_bytes(), b'MZ-fixture-ffmpeg.exe'
        )

    def test_limits_reject_large_download_and_extraction(self):
        with (
            patch.object(runtime, 'MAX_DOWNLOAD', 1),
            self.assertRaisesRegex(ValueError, 'tamanho'),
        ):
            self.install()
        with (
            patch.object(runtime, 'MAX_EXTRACTED', 1),
            self.assertRaisesRegex(ValueError, 'tamanho'),
        ):
            self.install()
        self.assertFalse(list(self.root.rglob('*.exe')))

    def test_failed_connection_never_creates_valid_cache(self):
        with patch.object(Session, 'get', side_effect=OSError('connection failed')):
            with self.assertRaises(OSError):
                self.install()
        self.assertIsNone(runtime.cached_folder(self.root))
        self.assertFalse(list(self.root.rglob('.onda-download-*')))

    def test_custom_tools_preserved_and_invalid_custom_falls_back_to_cache(self):
        custom = self.root / 'custom'
        custom.mkdir()
        for name in runtime.EXECUTABLES:
            (custom / name).write_bytes(b'MZ-fixture')
        (self.root / 'settings.json').write_text(json.dumps({'ffmpeg': str(custom)}))
        self.assertEqual(runtime.existing_folder(self.root), custom)
        (custom / 'ffplay.exe').unlink()
        cached = self.install()
        with patch.object(runtime, 'SHA256', self.hash):
            self.assertEqual(runtime.existing_folder(self.root), cached)


@unittest.skipUnless(
    os.environ.get('ONDA_UI_TESTS') == '1', 'requires interactive Windows desktop'
)
class RuntimeDialogTests(unittest.TestCase):
    def test_download_dialog_runs_worker_and_finishes_on_ui_thread(self):
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:

            def fake_download(progress, cancel):
                progress(50, 100, 'Testing')
                return Path('fixture-tools')

            with patch.object(runtime, 'download_tools', side_effect=fake_download):
                result = runtime.download_with_window(root)
            self.assertEqual(result, Path('fixture-tools'))
        finally:
            root.destroy()

    def test_error_can_be_retried_without_reopening_app(self):
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        calls = []

        def fake_download(**_):
            calls.append(1)
            if len(calls) == 1:
                raise OSError('offline')
            return Path('recovered-tools')

        def retry():
            def widgets(parent):
                for child in parent.winfo_children():
                    yield child
                    yield from widgets(child)

            for child in widgets(root):
                if (
                    child.winfo_class() == 'TButton'
                    and child.cget('text') == 'Tentar novamente'
                ):
                    if child.winfo_manager():
                        child.invoke()
                        return
            root.after(40, retry)

        try:
            root.after(140, retry)
            with patch.object(runtime, 'download_tools', side_effect=fake_download):
                result = runtime.download_with_window(root)
            self.assertEqual(result, Path('recovered-tools'))
            self.assertEqual(len(calls), 2)
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
