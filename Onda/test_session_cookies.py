import os
import tempfile
import unittest
from pathlib import Path
from session_cookies import cookie_source, migrate_windows_session


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI')
class ProtectedSessionTests(unittest.TestCase):
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
