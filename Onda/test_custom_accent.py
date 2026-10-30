import unittest

from appearance import palette, THEME_MODES
from custom_accent import normalize_color, contrast
from preferences import PreferenceStore


class CustomAccentTests(unittest.TestCase):
    def test_only_six_opaque_hex_digits_are_accepted_and_persisted(self):
        for value in ('#7c4dff', '7c4dff', '  #7C4DFF  '):
            self.assertEqual(normalize_color(value), '#7C4DFF')
            self.assertEqual(
                PreferenceStore.clean({'theme_accent': value})['theme_accent'],
                '#7C4DFF',
            )
        for value in (
            '#123',
            '#12345678',
            '##123456',
            '#GG0000',
            '',
            None,
            ['#123456'],
        ):
            self.assertFalse(normalize_color(value))
            self.assertNotIn(
                'theme_accent', PreferenceStore.clean({'theme_accent': value})
            )

    def test_custom_colors_remain_readable_on_buttons_and_every_theme_surface(self):
        for value in (
            '#000000',
            '#FFFFFF',
            '#FFFF00',
            '#00FF00',
            '#FF0000',
            '#0000FF',
            '#7C4DFF',
            '#222A35',
            '#E7EDF4',
        ):
            for mode in THEME_MODES:
                if mode == 'Seguir o sistema':
                    continue
                colors = palette(mode, value, separators=True)
                self.assertGreaterEqual(
                    contrast(colors['accent'], colors['accent_text']),
                    4.5,
                    (mode, value),
                )
                for surface in ('bg', 'surface', 'input'):
                    self.assertGreaterEqual(
                        contrast(colors['accent'], colors[surface]),
                        4.5,
                        (mode, value, surface),
                    )
