import ast
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from window_icons import icon_kind, draw_icon

class WindowIconTests(unittest.TestCase):
    def test_every_secondary_window_title_has_a_function_icon(self):
        for path in Path(__file__).parent.glob('*.py'):
            if path.name.startswith('test_'):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='title' and node.args:
                    value=node.args[0]
                    title=value.value if isinstance(value,ast.Constant) else ''.join(x.value for x in value.values if isinstance(x,ast.Constant)) if isinstance(value,ast.JoinedStr) else None
                    if isinstance(title,str) and not title.startswith('Onda • Vídeo'):
                        self.assertIsNotNone(icon_kind(title),(path.name,title))
    def test_icon_drawing_uses_selected_accent(self):
        for kind in ('onda','crop','settings','metadata','version','download','media','duplicate','help','log'):
            red=draw_icon(kind,96,{'accent':'#ff0000','bg':'#000000'})
            blue=draw_icon(kind,96,{'accent':'#0000ff','bg':'#000000'})
            self.assertIn((255,0,0,255),red.getdata())
            self.assertIn((0,0,255,255),blue.getdata())
            self.assertNotEqual(red.tobytes(),blue.tobytes())

    def test_crop_icon_has_all_window_sizes(self):
        self.assertEqual(icon_kind('ONDA • Ajustar capa'),'crop')
        for size in (16,32,48):
            self.assertEqual(draw_icon('crop',size).size,(size,size))
    @unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
    def test_cropper_gets_icon_when_opened(self):
        from PIL import Image
        from cover_crop_ui import CoverCropper
        from window_position import install_window_centering
        root=tk.Tk()
        try:
            install_window_centering(root)
            with tempfile.TemporaryDirectory() as folder:
                source=Path(folder)/'cover.png'
                Image.new('RGB',(200,200),'blue').save(source)
                window=CoverCropper(root,source,Path(folder)/'cropped.png',lambda _:None)
                root.update()
                self.assertEqual(window._function_icon_kind,'crop')
                self.assertEqual([image.width() for image in window._function_icons],[16,32,48])
                window.destroy()
        finally:
            root.destroy()
