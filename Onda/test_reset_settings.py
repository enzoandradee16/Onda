import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from reset_settings import GROUPS,apply_defaults,show_reset


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class ResetSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name})
        self.env.start()
        from app import App
        self.app=App(show_welcome=False)
        self.app.folder.set(self.temp.name)

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_every_preference_is_listed_and_partial_reset_preserves_other_values(self):
        app=self.app
        listed={name for fields in GROUPS.values() for name in fields}
        self.assertEqual(listed,set(app.preference_fields)|{'remember_settings','social_cookies','youtube_cookies'})
        app.remember_settings.set(True)
        app.image_format.set('SVG');app.image_size.set('Personalizado');app.image_width.set('640')
        app.mp3_quality.set('128 kbps')
        app.spotify_client_id.set('unchanged')
        apply_defaults(app,{'image_format','image_width'})
        self.assertEqual(app.image_format.get(),'Original')
        self.assertEqual(app.image_width.get(),'1920')
        self.assertEqual(app.image_size.get(),'Personalizado')
        self.assertEqual(app.mp3_quality.get(),'128 kbps')
        self.assertEqual(app.spotify_client_id.get(),'unchanged')
        app.qt_animations.set(False)
        apply_defaults(app,{'qt_animations'})
        self.assertTrue(app.qt_animations.get())
        saved=app.preference_store.load()
        self.assertEqual(saved['image_format'],'Original')
        self.assertEqual(saved['mp3_quality'],'128 kbps')

    def test_all_reset_preserves_user_data_and_removes_saved_preferences(self):
        app=self.app
        original=Path(self.temp.name)/'song.mp3'
        original.write_bytes(b'music')
        app.library.add_history(original,'MP3','https://example.test/song')
        items=app.add(lines=['https://example.com/song'])
        app.remember_settings.set(True)
        app.image_format.set('SVG');app.background_preview.set(True)
        app.social_cookies.set('cookies.txt')
        app.tab_reorder.apply(list(reversed(app.tab_order.get())))
        app.tab_order.set(tuple(app.tab_reorder.order()))
        app.persist_preferences()
        apply_defaults(app,{name for fields in GROUPS.values() for name in fields})
        self.assertEqual({name:var.get() for name,var in app.preference_fields.items()},app.preference_defaults)
        self.assertEqual(app.tab_reorder.order(),list(app.preference_defaults['tab_order']))
        self.assertTrue(app.remember_settings.get())
        self.assertTrue(app.preference_store.path.exists())
        self.assertEqual(app.social_cookies.get(),'')
        self.assertEqual(original.read_bytes(),b'music')
        self.assertEqual(len(app.library.history()),1)
        self.assertEqual(set(app.jobs),set(items))
        self.assertEqual(len(app.library.load_queue()),1)

    def test_dialog_selection_decline_and_confirm(self):
        app=self.app
        app.image_format.set('SVG');app.mp3_quality.set('128 kbps')
        window=show_reset(app)
        self.assertFalse(any(var.get() for var in window.choices.values()))
        self.assertEqual(str(window.apply_button.cget('state')),'disabled')
        window.choices['image_format'].set(True)
        with patch('reset_settings.messagebox.askyesno',return_value=False):window.restore()
        self.assertEqual(app.image_format.get(),'SVG')
        with patch('reset_settings.messagebox.askyesno',return_value=True):window.restore()
        self.assertEqual(app.image_format.get(),'Original')
        self.assertEqual(app.mp3_quality.get(),'128 kbps')
        window=show_reset(app,True)
        self.assertTrue(all(var.get() for var in window.choices.values()))
        window.select(False)
        self.assertFalse(any(var.get() for var in window.choices.values()))
        window.destroy()
