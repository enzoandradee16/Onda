import os
import tempfile
import unittest
from unittest.mock import patch
from interface_spacing import SPACING_MODES, spacing_scale
from preferences import PreferenceStore


class SpacingPreferencesTests(unittest.TestCase):
    def test_valid_modes_round_trip_and_invalid_values_are_discarded(self):
        with tempfile.TemporaryDirectory() as root:
            from pathlib import Path

            store = PreferenceStore(Path(root) / 'settings.json')
            for mode in SPACING_MODES:
                store.save({'interface_spacing': mode})
                self.assertEqual(store.load()['interface_spacing'], mode)
        for value in ('Other', None, [], 23):
            self.assertNotIn(
                'interface_spacing', PreferenceStore.clean({'interface_spacing': value})
            )
        self.assertEqual(spacing_scale('Other'), 1)

    def test_cross_platform_transfer_keeps_spacing_and_android_notice_option(self):
        from advanced_options import export_settings, import_settings

        for mode in SPACING_MODES:
            payload = export_settings(
                {'interface_spacing': mode, 'notice_animation': False}, 'android'
            )
            self.assertEqual(
                import_settings(payload, 'android')['interface_spacing'], mode
            )
            self.assertFalse(import_settings(payload, 'android')['notice_animation'])
            self.assertEqual(
                import_settings(payload, 'windows')['interface_spacing'], mode
            )
        invalid = {
            'schema': 'onda-preferences',
            'version': 1,
            'settings': {'interface_spacing': 'Other', 'notice_animation': 'false'},
        }
        self.assertNotIn('interface_spacing', import_settings(invalid, 'android'))
        self.assertNotIn('notice_animation', import_settings(invalid, 'android'))


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class SpacingUiTests(unittest.TestCase):
    def test_live_spacing_is_reversible_keeps_font_and_restores_defaults(self):
        from app import App
        from tkinter import ttk
        from reset_settings import apply_defaults

        with (
            tempfile.TemporaryDirectory() as root,
            patch.dict(os.environ, {'LOCALAPPDATA': root}),
        ):
            app = App(show_welcome=False)
            try:
                frame = ttk.Frame(app, padding=(12, 8))
                frame.pack(padx=10, pady=8)
                app.update()
                font = ttk.Style(app).lookup('TButton', 'font')
                for _ in range(3):
                    app.interface_spacing.set('Confortável')
                    app.update()
                    self.assertEqual(int(frame.pack_info()['padx']), 12)
                    app.interface_spacing.set('Compacto')
                    app.update()
                    self.assertEqual(int(frame.pack_info()['padx']), 8)
                    self.assertEqual(ttk.Style(app).lookup('TButton', 'font'), font)
                    app.interface_spacing.set('Padrão')
                    app.update()
                    self.assertEqual(int(frame.pack_info()['padx']), 10)
                app.interface_spacing.set('Confortável')
                apply_defaults(app, {'interface_spacing'})
                self.assertEqual(app.interface_spacing.get(), 'Padrão')
            finally:
                app.destroy()
