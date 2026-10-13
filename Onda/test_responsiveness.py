import os
import tempfile
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class ResponsivenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.environment.start()
        from app import App
        self.app = App(show_welcome=False)

    def tearDown(self):
        self.app.destroy()
        self.environment.stop()
        self.temp.cleanup()

    def test_opening_each_tab_keeps_identity_theme_and_close_safe(self):
        app = self.app
        self.assertIsNone(app.effects_page._content)
        self.assertFalse(app.effects_page.busy)
        app.record_history(__file__, "PY", "")
        self.assertIsNone(app.history_page._content)
        app.theme_mode.set("Claro")
        for page in (app.catalog_page, app.images_page, app.playlist_page, app.history_page, app.effects_page):
            identity = str(page)
            app.pages.select(page)
            app.update()
            self.assertIsNotNone(page._content)
            self.assertEqual(app.pages.select(), identity)
            self.assertIs(page.ensure_ready(), page.ensure_ready())
        app.catalog_page.stop_preview()
        app.effects_page.stop_preview()

    def test_large_playlist_yields_and_filter_actions_use_latest_text(self):
        page=self.app.playlist_page.ensure_ready()
        tracks=[{"title":f"Música {i}","artists":[f"ArtistaZ{i%20}"],"source_url":f"https://example.com/{i}"} for i in range(5000)]
        page.display({"title":"Teste","tracks":tracks,"note":""})
        self.assertTrue(page.busy)
        self.assertLess(len(page.table.get_children()),5000)
        deadline=time.monotonic()+10
        while page.busy and time.monotonic()<deadline:
            self.app.update();time.sleep(.001)
        self.assertFalse(page.busy)
        self.assertEqual(len(page.table.get_children()),5000)
        page.filter_text.set("artista")
        first=page._filter_after
        page.filter_text.set("artistaz19")
        self.assertNotEqual(first,page._filter_after)
        keys=page.selected_keys()
        self.assertEqual(len(keys),250)
        self.assertTrue(all(page.records[key]["artists"]==["ArtistaZ19"] for key in keys))
        page.filter_text.set("");page.filter_records()
        self.assertEqual(len(page.table.get_children()),5000)
        page.display({"title":"Substituição","tracks":tracks,"note":""})
        page.shutdown()  # No callback may access destroyed widgets.
        self.app.update()
