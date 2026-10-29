import os
import tempfile
import unittest
from unittest.mock import patch
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from interface_fonts import DEFAULT_FONT, font_choices, font_family
from preferences import PreferenceStore


class FontPreferenceTests(unittest.TestCase):
    def test_font_persistence_and_rejection_of_invalid_values(self):
        with tempfile.TemporaryDirectory() as folder:
            from pathlib import Path

            store = PreferenceStore(Path(folder) / 'settings.json')
            store.save({'interface_font': 'Monoespaçada', 'theme_mode': 'Claro'})
            self.assertEqual(store.load()['interface_font'], 'Monoespaçada')
        for bad in (None, [], '', 'x' * 129, 'Arial\n', ' Arial'):
            self.assertNotIn(
                'interface_font', PreferenceStore.clean({'interface_font': bad})
            )


class FontUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        from app import App

        self.app = App(show_welcome=False)
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_live_font_preserves_styles_and_reaches_new_windows(self):
        app = self.app
        self.assertIn(DEFAULT_FONT, font_choices(app))
        self.assertEqual(font_family(app, 'Missing font 123', 'Segoe UI'), 'Segoe UI')
        label = ttk.Label(app, text='Teste', font=('Segoe UI', 19, 'bold italic'))
        canvas = tk.Canvas(app)
        item = canvas.create_text(10, 10, text='Teste', font=('Segoe UI', 13, 'bold'))
        app.theme_manager.walk(app)
        before = tkfont.Font(root=app, font=label.cget('font')).actual()
        app.interface_font.set('Monoespaçada')
        chosen = font_family(app, 'Monoespaçada')
        after = tkfont.Font(root=app, font=label.cget('font')).actual()
        self.assertEqual(after['family'], chosen)
        for key in ('size', 'weight', 'slant'):
            self.assertEqual(before[key], after[key])
        self.assertEqual(
            tkfont.Font(root=app, font=canvas.itemcget(item, 'font')).actual('family'),
            chosen,
        )
        self.assertEqual(
            tkfont.Font(
                root=app, font=ttk.Style(app).lookup('Accent.TButton', 'font')
            ).actual('family'),
            chosen,
        )
        window = tk.Toplevel(app)
        window.withdraw()
        new = ttk.Label(window, text='Nova janela', font=('Segoe UI', 15, 'bold'))
        app.theme_manager.walk(window)
        self.assertEqual(
            tkfont.Font(root=app, font=new.cget('font')).actual('family'), chosen
        )
        app.interface_font.set(DEFAULT_FONT)
        self.assertEqual(
            tkfont.Font(root=app, font=label.cget('font')).actual(), before
        )
        window.destroy()

    def test_save_reopen_and_reset_font_only(self):
        from reset_settings import apply_defaults, GROUPS

        app = self.app
        app.show_settings()
        app.settings_window.withdraw()
        self.assertIn('Monoespaçada', app.interface_font_combo.cget('values'))
        self.assertIn('interface_font', GROUPS['Aparência'])
        app.interface_font.set('Serifada')
        app.theme_accent.set('Roxo')
        app.remember_settings.set(True)
        app.persist_preferences()
        app.destroy()
        from app import App

        self.app = App(show_welcome=False)
        self.app.withdraw()
        app = self.app
        self.assertEqual(app.interface_font.get(), 'Serifada')
        apply_defaults(app, {'interface_font'})
        self.assertEqual(app.interface_font.get(), DEFAULT_FONT)
        self.assertEqual(app.theme_accent.get(), 'Roxo')
