import os
import tempfile
import unittest
from unittest.mock import Mock, patch


class EnterSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name})
        self.env.start()
        from app import App
        self.app=App(show_welcome=False);self.app.withdraw()

    def tearDown(self):
        self.app.destroy();self.env.stop();self.temp.cleanup()

    def test_enter_searches_once_and_does_not_cancel_running_query(self):
        page=self.app.catalog_page
        page.query.set('  Artista\nMúsica  ')
        page.search=Mock(side_effect=lambda:page.search_button.configure(text='Cancelar'))
        self.assertEqual(page.enter_search(),'break')
        self.assertEqual(page.query.get(),'Artista Música')
        page.search.assert_called_once_with()
        self.assertEqual(page.enter_search(),'break')
        page.search.assert_called_once_with()
        self.assertIn('enter_search',page.entry.bind('<Return>'))
        self.assertIn('enter_search',page.entry.bind('<KP_Enter>'))
        # Queue's text area retains the standard multiline Enter binding.
        self.assertEqual(self.app.urls.bind('<Return>'),'')

    def test_metadata_enter_submits_instead_of_inserting_newline(self):
        from metadata_ui import MetadataWindow
        window=MetadataWindow(self.app,[]);window.withdraw()
        try:
            window.fetch=Mock()
            self.assertEqual(window.enter_fetch(),'break')
            window.fetch.assert_called_once_with()
            self.assertIn('enter_fetch',window.links.bind('<Return>'))
        finally:window.close()
