import os
import tempfile
import unittest
from unittest.mock import patch
from preferences import PreferenceStore


class ImagePreferenceValidationTests(unittest.TestCase):
    def test_invalid_values_are_ignored_and_valid_dimensions_normalized(self):
        invalid={'image_format':'EXE','image_size':'random','image_width':'9999999999999999999','image_height':'-1','image_keep_ratio':'false'}
        self.assertEqual(PreferenceStore.clean(invalid),{})
        valid={'image_format':'SVG','image_size':'Personalizado','image_width':'00500','image_height':'300','image_keep_ratio':False}
        self.assertEqual(PreferenceStore.clean(valid),dict(valid,image_width='500'))


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class ImagePreferenceUiTests(unittest.TestCase):
    def test_close_reopen_restores_all_image_options(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False)
            try:
                app.remember_settings.set(True)
                pane=app.images_page
                pane.format.set('SVG')
                pane.size.set('Personalizado')
                pane.width.set('640');pane.height.set('480')
                pane.keep_ratio.set(False)
                app.close()
                app=App(show_welcome=False)
                pane=app.images_page
                self.assertTrue(app.remember_settings.get())
                self.assertEqual(pane.options(),{'format':'SVG','width':640,'height':480,'keep_ratio':False})
                self.assertTrue(pane.custom.grid_info())
                self.assertTrue(pane.format_note.grid_info())
                pane.format.set('WebP');pane.size.set('Até 1280 × 720');pane.keep_ratio.set(True)
                app.close()
                app=App(show_welcome=False)
                self.assertEqual(app.images_page.options(),{'format':'WebP','width':1280,'height':720,'keep_ratio':True})
            finally:app.destroy()

    def test_without_remember_options_reset_next_launch(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False)
            try:
                app.remember_settings.set(False)
                app.toggle_remember_settings()
                app.images_page.format.set('JPG')
                app.images_page.keep_ratio.set(False)
                app.close()
                app=App(show_welcome=False)
                self.assertFalse(app.remember_settings.get())
                self.assertEqual(app.images_page.format.get(),'Original')
                self.assertTrue(app.images_page.keep_ratio.get())
                self.assertFalse(app.preference_store.path.exists())
            finally:app.destroy()
