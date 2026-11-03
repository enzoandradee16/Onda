from array import array
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from image_output import transform_image, open_preview, validate_options


class BackgroundRemovalTests(unittest.TestCase):
    def predict(self, model, values):
        self.assertEqual(len(values), 3 * 320 * 320 * 4)
        return array(
            'f',
            (
                1.0 if 80 < x < 240 and 80 < y < 240 else 0.0
                for y in range(320)
                for x in range(320)
            ),
        ).tobytes()

    def test_jpg_request_uses_png_and_preserves_existing_alpha(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            'image_background.model_path', return_value=Path('model.onnx')
        ), patch('image_background._native_predict', self.predict):
            source = Path(folder) / 'picture.png'
            Image.new('RGBA', (320, 320), (200, 30, 20, 128)).save(source)
            result = transform_image(
                source,
                dict(
                    format='JPG',
                    remove_background=True,
                    width=160,
                    height=160,
                    keep_ratio=True,
                ),
            )
            self.assertEqual(result.suffix, '.png')
            with Image.open(result) as image:
                self.assertEqual(image.size, (160, 160))
                self.assertEqual(image.getpixel((80, 80))[3], 128)
                self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_svg_retains_transparency_and_disabled_option_never_loads_model(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'picture.png'
            Image.new('RGB', (320, 320), 'red').save(source)
            with patch(
                'image_background.remove_background',
                side_effect=AssertionError('Disabled'),
            ):
                self.assertEqual(
                    transform_image(source, dict(format='Original')), source
                )
            with patch(
                'image_background.model_path', return_value=Path('model.onnx')
            ), patch('image_background._native_predict', self.predict):
                result = transform_image(
                    source, dict(format='SVG', remove_background=True)
                )
            with open_preview(result) as image:
                self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_invalid_option_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_options(dict(format='PNG', remove_background='yes'))
