import os
import tempfile
import unittest
from unittest.mock import patch

from appearance import ACCENTS, THEME_MODES, palette
from preferences import PreferenceStore


class PaletteTests(unittest.TestCase):
    def test_pure_black_has_no_surface_separations_unless_enabled(self):
        flat=palette('Preto puro')
        for key in ('bg','surface','input','line','hover','selected'):
            self.assertEqual(flat[key],'#000000',key)
        separated=palette('Preto puro',separators=True)
        self.assertNotEqual(separated['input'],separated['bg'])
        self.assertNotEqual(separated['line'],separated['bg'])
        self.assertEqual(flat['accent'],separated['accent'])
        self.assertEqual(PreferenceStore.clean({'pure_black_separators':True}),{'pure_black_separators':True})

    def test_all_accents_have_readable_button_text_in_both_modes(self):
        def luminance(color):
            values = [int(color[i:i+2],16)/255 for i in (1,3,5)]
            values = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
            return sum(v*w for v,w in zip(values,(.2126,.7152,.0722)))
        def contrast(first,second):
            values = sorted((luminance(first),luminance(second)))
            return (values[1]+.05)/(values[0]+.05)
        for mode in ('Claro','Escuro'):
            for accent in ACCENTS:
                c = palette(mode,accent)
                self.assertGreaterEqual(contrast(c['accent'],c['accent_text']),4.5,(mode,accent))
                self.assertGreaterEqual(contrast(c['text'],c['bg']),7)
                self.assertGreaterEqual(contrast(c['muted'],c['bg']),4.5)

    def test_old_accent_spelling_is_migrated(self):
        self.assertEqual(PreferenceStore.clean({"theme_accent":"Verde-água"}),{"theme_accent":"Verde-Água"})

    def test_persistence_rejects_unknown_modes_and_colors(self):
        self.assertEqual(PreferenceStore.clean({'theme_mode':'Other','theme_accent':['Azul']}),{})
        for mode in THEME_MODES:
            self.assertEqual(PreferenceStore.clean({'theme_mode':mode,'theme_accent':'Roxo'}),
                             {'theme_mode':mode,'theme_accent':'Roxo'})


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class AppearanceUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA':self.temp.name})
        self.env.start()
        from app import App
        self.app = App(show_welcome=False)
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_live_theme_changes_existing_text_canvas_and_new_windows(self):
        from tkinter import ttk
        from metadata_ui import MetadataWindow
        app = self.app
        app.theme_mode.set('Claro')
        app.theme_accent.set('Roxo')
        c = palette('Claro','Roxo')
        self.assertEqual(app.urls.cget('background'),c['input'])
        self.assertEqual(app.cget('background'),c['bg'])
        self.assertEqual(ttk.Style(app).lookup('Accent.TButton','background'),c['accent'])
        window = MetadataWindow(app, [])
        app.theme_manager.walk(window)
        self.assertEqual(window.links.cget('background'),c['surface'])
        self.assertEqual(window._function_icon_key[1],c['accent'])
        self.assertEqual(app._function_icon_key[1],c['accent'])
        app.theme_mode.set('Escuro')
        self.assertEqual(window._function_icon_key[1],palette('Escuro','Roxo')['accent'])
        self.assertEqual(app._function_icon_key[1],palette('Escuro','Roxo')['accent'])
        self.assertEqual(window.links.cget('background'),palette('Escuro','Roxo')['surface'])
        window.close()

    def test_system_changes_apply_only_when_following_system(self):
        app = self.app
        with patch('appearance.system_mode',return_value='Claro'):
            app.theme_mode.set('Seguir o sistema')
            app.theme_manager.apply()
            self.assertEqual(app.theme_manager.colors['mode'],'Claro')
        with patch('appearance.system_mode',return_value='Escuro'):
            app.theme_manager.apply()
            self.assertEqual(app.theme_manager.colors['mode'],'Escuro')
            app.theme_mode.set('Claro')
            app.theme_manager.apply()
            self.assertEqual(app.theme_manager.colors['mode'],'Claro')

    def test_remember_and_selective_reset(self):
        from reset_settings import apply_defaults
        app = self.app
        app.theme_mode.set('Claro')
        app.theme_accent.set('Rosa')
        app.remember_settings.set(True)
        app.persist_preferences()
        app.destroy()
        from app import App
        self.app = App(show_welcome=False)
        app = self.app
        app.withdraw()
        self.assertEqual(app.theme_mode.get(),'Claro')
        self.assertEqual(app.theme_accent.get(),'Rosa')
        apply_defaults(app,{'theme_accent'})
        self.assertEqual(app.theme_mode.get(),'Claro')
        self.assertEqual(app.theme_accent.get(),'Verde-Água')
        self.assertEqual(app.theme_manager.colors['accent'],palette('Claro')['accent'])
