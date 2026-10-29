"""Brand rendering retains theme contrast and legibility at native icon sizes."""

import unittest
from PIL import ImageColor
from appearance import ACCENTS, THEME_MODES, palette
from brand_mark import icon


class BrandMarkTests(unittest.TestCase):
    def test_all_theme_accents_render_with_the_selected_foreground_and_background(self):
        for mode in THEME_MODES:
            for accent in ACCENTS:
                colors = palette(mode, accent)
                image = icon(96, colors['accent'], colors['bg'])
                pixels = set(image.getdata())
                self.assertIn(
                    ImageColor.getcolor(colors['accent'], 'RGBA'),
                    pixels,
                    (mode, accent),
                )
                self.assertIn(
                    ImageColor.getcolor(colors['bg'], 'RGBA'), pixels, (mode, accent)
                )
                self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_wave_remains_visible_inside_the_canvas_at_every_windows_icon_size(self):
        for size in (16, 24, 32, 48, 64, 128, 256):
            image = icon(size, '#ff00ff', None)
            box = image.getbbox()
            self.assertIsNotNone(box, size)
            self.assertLess(box[0], size * 0.2)
            self.assertGreater(box[2], size * 0.8)
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertEqual(image.getpixel((size - 1, size - 1))[3], 0)
