import os
import tempfile
import unittest
from pathlib import Path
from session_cookies import cookie_source, migrate_windows_session


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI')
class ProtectedSessionTests(unittest.TestCase):
    def test_account_switch_and_disconnect_keep_active_cookie_snapshot(self):
        from social_media import session_for
        from download_defaults import download_cookies
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def save(account):
                (root / 'instagram-session.txt').write_bytes((
                    '# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t' + account + '\n'
                ).encode())
                return migrate_windows_session(root)
            protected = save('account-a')
            with session_for(str(protected)) as active:
                save('account-b')
                with session_for(str(protected)) as next_request:
                    self.assertEqual(active.cookies.get('sessionid'), 'account-a')
                    self.assertEqual(next_request.cookies.get('sessionid'), 'account-b')
                protected.unlink()
                self.assertEqual(active.cookies.get('sessionid'), 'account-a')
                self.assertEqual(download_cookies('https://instagram.com/p/test', '', '', ''), '')

    def test_disconnect_during_real_local_download_does_not_break_stream(self):
        import http.server
        import threading
        from social_media import session_for
        started, release = threading.Event(), threading.Event()
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', '8192')
                self.end_headers()
                self.wfile.write(b'a' * 4096); self.wfile.flush(); started.set()
                release.wait(5)
                self.wfile.write(b'b' * 4096)
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'instagram-session.txt').write_bytes(b'# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tsynthetic\n')
                protected = migrate_windows_session(root)
                with session_for(str(protected)) as session:
                    with session.get(f'http://127.0.0.1:{server.server_port}/video', stream=True, timeout=10) as response:
                        self.assertTrue(started.wait(5))
                        self.assertEqual(response.raw.read(4096), b'a' * 4096)
                        protected.unlink(); release.set()
                        self.assertEqual(response.raw.read(), b'b' * 4096)
        finally:
            release.set(); server.shutdown(); server.server_close(); thread.join(5)

    def test_migration_encrypts_and_loads_without_plaintext_temp_files(self):
        text = '# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tsynthetic-only\n'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plain = root / 'instagram-session.txt'
            plain.write_bytes(text.encode('utf-8'))
            protected = migrate_windows_session(root)
            self.assertFalse(plain.exists())
            self.assertNotIn(b'synthetic-only', protected.read_bytes())
            self.assertEqual(cookie_source(str(protected)).getvalue(), text)
            from social_media import session_for
            with session_for(str(protected)) as session:
                self.assertEqual(session.cookies.get('sessionid'), 'synthetic-only')
            from yt_dlp import YoutubeDL
            with YoutubeDL({'cookiefile': cookie_source(str(protected)), 'quiet': True}) as downloader:
                self.assertEqual(next(iter(downloader.cookiejar)).value, 'synthetic-only')
            self.assertEqual(list(root.iterdir()), [protected])

    def test_corrupted_protected_session_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'instagram-session.dpapi'
            target.write_bytes(b'not an encrypted session')
            with self.assertRaises(ValueError):
                cookie_source(str(target))
