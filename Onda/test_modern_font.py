import json, unittest
from pathlib import Path


class ModernFontTests(unittest.TestCase):
    def test_bundled_font_license_and_platforms_match(self):
        root = Path(__file__).resolve().parents[1]
        font = root / 'Onda/assets/fonts/Inter.ttf'
        self.assertEqual(font.read_bytes()[:4], b'\x00\x01\x00\x00')
        self.assertEqual(
            font.read_bytes(),
            (root / 'Android/app/src/main/res/font/onda_modern.ttf').read_bytes(),
        )
        self.assertIn(
            'SIL OPEN FONT LICENSE', (font.parent / 'OFL-Inter.txt').read_text()
        )

    def test_new_default_legacy_and_custom_fonts(self):
        from preferences import PreferenceStore
        from interface_fonts import DEFAULT_FONT, qt_font_family

        schema = json.loads(
            (Path(__file__).parent / 'settings_schema/desktop.json').read_text(
                encoding='utf-8'
            )
        )
        self.assertEqual(schema['defaults']['interface_font'], DEFAULT_FONT)
        field = next(
            field for field in schema['fields'] if field['key'] == 'interface_font'
        )
        self.assertIn('ONDA Legacy', field['choices'])
        self.assertEqual(qt_font_family(DEFAULT_FONT), 'Inter')
        self.assertEqual(qt_font_family('ONDA Legacy'), 'Segoe UI')
        self.assertEqual(
            PreferenceStore.clean({'interface_font': 'Padrão do sistema'})[
                'interface_font'
            ],
            DEFAULT_FONT,
        )
        self.assertEqual(
            PreferenceStore.clean({'interface_font': 'Arial'})['interface_font'],
            'Arial',
        )
