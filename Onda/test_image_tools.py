"""Pixel-level checks for lightweight image edits and excerpt boundaries."""

import tempfile
import unittest
from pathlib import Path
from PIL import Image
from image_output import edit_frame, transform_image, validate_options
from effects_export import segment_times


class ImageToolsTests(unittest.TestCase):
    def test_crop_rotate_and_background_preserve_alpha_and_dimensions(self):
        image = Image.new('RGBA', (160, 90), (200, 10, 20, 0))
        image.putpixel((80, 45), (200, 10, 20, 255))
        cropped = edit_frame(image, dict(crop='1:1', rotation=90))
        self.assertEqual(cropped.size, (90, 90))
        colored = edit_frame(
            cropped, dict(background='color', background_color='#123456')
        )
        self.assertEqual(colored.getpixel((0, 0)), (18, 52, 86, 255))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'background.png'
            Image.new('RGB', (30, 50), 'blue').save(source)
            result = edit_frame(
                cropped, dict(background='image', background_image=str(source))
            )
            self.assertEqual(result.size, cropped.size)
            self.assertEqual(result.getpixel((0, 0)), (0, 0, 255, 255))
            original = Path(directory) / 'photo.png'
            Image.new('RGB', (160, 90), 'red').save(original)
            result = transform_image(
                original, dict(format='Original', crop='1:1', width=0, height=0)
            )
            with Image.open(result) as output:
                self.assertEqual(output.size, (90, 90))

    def test_invalid_edits_and_excerpt_boundaries_are_rejected(self):
        for extra in (dict(rotation=45), dict(crop='0:1'), dict(background='unknown')):
            with self.assertRaises(ValueError):
                validate_options(dict(format='PNG', **extra))
        self.assertEqual(segment_times('1:30', '2:05'), (90, 125))
        self.assertEqual(segment_times('', ''), (0, None))
        for start, end in [('2:00', '1:30'), ('-1', ''), ('nan', ''), ('1:99', '')]:
            with self.assertRaises(ValueError):
                segment_times(start, end)
