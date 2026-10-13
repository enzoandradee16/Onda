import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from first_run import FirstRunStore
from preferences import PreferenceStore


class FirstRunStoreTests(unittest.TestCase):
    def test_only_one_claim_independent_of_remember_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            state = FirstRunStore(Path(folder) / "profile" / "welcome-seen.json")
            self.assertTrue(state.claim())
            self.assertFalse(FirstRunStore(state.path).claim())
            preferences = PreferenceStore(state.path.with_name("settings.json"))
            preferences.save({"playlist_limit": "500"})
            preferences.forget()
            self.assertFalse(state.claim())


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class WelcomeUiTests(unittest.TestCase):
    def test_first_launch_close_without_changes_and_no_repeat(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            try:
                app.update()
                welcome = app.welcome_window
                self.assertIsNotNone(welcome)
                self.assertEqual(welcome._function_icon_kind, "help")
                before = {name: value.get() for name, value in app.preference_fields.items()}
                welcome.folder.set(str(Path(folder) / "Not applied"))
                welcome.limit.set("5000")
                welcome.tk.eval(welcome.protocol("WM_DELETE_WINDOW"))
                self.assertFalse(welcome.winfo_exists())
                self.assertEqual({name: value.get() for name, value in app.preference_fields.items()}, before)
                self.assertFalse(app.remember_settings.get())
                self.assertFalse(app.preference_store.path.exists())
                app.withdraw()
                app.deiconify()
                app.update()
                self.assertFalse(welcome.winfo_exists())
            finally:
                app.destroy()
            app = App()
            try:
                app.update()
                self.assertIsNone(app.welcome_window)
            finally:
                app.destroy()

    def test_apply_saves_settings_and_invalid_folder_keeps_welcome_open(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            try:
                app.update()
                welcome = app.welcome_window
                welcome.folder.set("")
                welcome.apply()
                self.assertTrue(welcome.winfo_exists())
                self.assertIn("pasta", welcome.status.get())
                destination = str(Path(folder) / "Minhas músicas")
                welcome.folder.set(destination)
                welcome.mode.set("Áudio · MP3 (320 kbps)")
                welcome.provider.set("Apple / iTunes")
                welcome.limit.set("2000")
                welcome.apply()
                self.assertFalse(welcome.winfo_exists())
                saved = app.preference_store.load()
                self.assertEqual(Path(saved["folder"]).resolve(), Path(destination).resolve())
                self.assertEqual(saved["playlist_limit"], "2000")
                self.assertEqual(saved["catalog_provider"], "Apple / iTunes")
                self.assertEqual(saved["mode"], "Áudio · MP3 (320 kbps)")
            finally:
                app.destroy()

    def test_apply_without_remember_is_session_only(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            try:
                app.update()
                welcome = app.welcome_window
                welcome.limit.set("5000")
                welcome.remember.set(False)
                welcome.apply()
                self.assertEqual(app.playlist_limit.get(), "5000")
                self.assertFalse(app.preference_store.path.exists())
                self.assertTrue((Path(folder) / "Onda" / "welcome-seen.json").is_file())
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
