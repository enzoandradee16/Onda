import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from matching import AmbiguousMatch, resolve_youtube, select_candidate
from preferences import PreferenceStore
from test_automation import catalog, candidate


class AutoMatchTests(unittest.TestCase):
    def test_automatic_chooses_best_compatible_result_without_picker(self):
        record = catalog()
        best = candidate(id="best1234567")
        similar = candidate(id="near1234567", duration=201)
        with self.assertRaises(AmbiguousMatch):
            select_candidate(record, [similar, best])
        choose = Mock(return_value=best)
        def find(row, logger, *, prefer_best=False):
            return select_candidate(row, [similar, best], prefer_best=prefer_best)
        with patch("matching.find_youtube", side_effect=find) as search:
            match = resolve_youtube(record, Mock(), choose, automatic=True, confirm=True)
        self.assertEqual(match["id"], best["id"])
        self.assertTrue(search.call_args.kwargs["prefer_best"])
        choose.assert_not_called()

    def test_tie_is_deterministic_and_incompatible_versions_are_not_chosen(self):
        first = candidate(id="first123456")
        second = candidate(id="other123456")
        remix = candidate(id="remix123456", title="Artista Exemplo Canção Azul Remix")
        chosen=select_candidate(catalog(), [remix, first, second], prefer_best=True)
        self.assertEqual(chosen['id'],first['id'])
        with self.assertRaisesRegex(ValueError, "não foi baixado"):
            select_candidate(catalog(), [remix], prefer_best=True)

    def test_manual_only_results_fail_without_opening_a_picker(self):
        different = candidate(duration=380)
        with self.assertRaises(AmbiguousMatch):
            select_candidate(catalog(), [different])
        choose = Mock()
        with patch("matching.find_youtube", side_effect=lambda row, logger, **kwargs: select_candidate(row, [different], **kwargs)):
            with self.assertRaisesRegex(ValueError, "seleção automática"):
                resolve_youtube(catalog(), Mock(), choose, automatic=True)
        choose.assert_not_called()

    def test_manual_confirmation_is_preserved_when_setting_is_off(self):
        match = select_candidate(catalog(), [candidate()])
        choose = Mock(return_value=match)
        with patch("matching.find_youtube", return_value=match):
            resolve_youtube(catalog(), Mock(), choose, confirm=True)
        choose.assert_called_once_with(catalog(), [match])

    def test_preferences_require_boolean(self):
        self.assertTrue(PreferenceStore.clean({"auto_match": True})["auto_match"])
        for value in ("true", 1, None):
            self.assertNotIn("auto_match", PreferenceStore.clean({"auto_match": value}))


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class AutoMatchUiTests(unittest.TestCase):
    def test_remember_and_playlist_confirmation_are_consistent(self):
        with tempfile.TemporaryDirectory() as profile, patch.dict(os.environ, {"LOCALAPPDATA": profile}):
            from app import App
            store = PreferenceStore()
            store.save({"auto_match": True,"auto_metadata":True})
            app = App(show_welcome=False)
            app.withdraw()
            try:
                self.assertTrue(app.auto_match.get())
                self.assertTrue(app.auto_metadata.get())
                page = app.playlist_page
                self.assertIn("disabled", page.confirm_version_check.state())
                self.assertIn("Seleção automática", page.confirm_version_check.cget("text"))
                app.auto_match.set(False)
                self.assertTrue(app.auto_metadata.get())
                self.assertNotIn("disabled", page.confirm_version_check.state())
                self.assertTrue(page.confirm_version.get())
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
