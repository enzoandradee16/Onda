import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from credentials import CredentialError, CredentialStore


@unittest.skipUnless(os.name == "nt", "DPAPI is Windows-only")
class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private" / "spotify.dpapi"
        self.store = CredentialStore(self.path)

    def test_encrypted_persistence_and_separate_process(self):
        self.assertIsNone(self.store.load())
        self.store.save("fake-client-for-test", "fake-secret-for-test")
        encrypted = self.path.read_bytes()
        self.assertNotIn(b"fake-client-for-test", encrypted)
        self.assertNotIn(b"fake-secret-for-test", encrypted)
        self.assertEqual(
            CredentialStore(self.path).load(),
            ("fake-client-for-test", "fake-secret-for-test"),
        )
        script = (
            "from credentials import CredentialStore; import sys; "
            "assert CredentialStore(sys.argv[1]).load() == ('fake-client-for-test','fake-secret-for-test')"
        )
        subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            cwd=Path(__file__).parent,
            check=True,
        )

    def test_replace_and_forget(self):
        self.store.save("old-id", "old-secret")
        self.store.save("new-id", "new-secret")
        self.assertEqual(self.store.load(), ("new-id", "new-secret"))
        self.store.forget()
        self.store.forget()
        self.assertIsNone(self.store.load())

    def test_corrupt_data_fails_without_secret_details(self):
        self.store.save("id", "secret")
        self.path.write_bytes(b"invalid-protected-data")
        with self.assertRaises(CredentialError):
            self.store.load()

    def test_no_plaintext_fallback_or_partial_overwrite(self):
        self.store.save("old-id", "old-secret")
        encrypted = self.path.read_bytes()
        with patch(
            "credentials._crypt", side_effect=CredentialError("Protection unavailable")
        ):
            with self.assertRaises(CredentialError):
                self.store.save("new-id", "new-secret")
        self.assertEqual(self.path.read_bytes(), encrypted)
        with self.assertRaises(CredentialError):
            self.store.save("", "secret")
        self.assertEqual(self.store.load(), ("old-id", "old-secret"))


if __name__ == "__main__":
    unittest.main()
