import base64
import io
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
from PIL import Image
from image_output import transform_image, open_preview


class SvgTests(unittest.TestCase):
    def test_self_contained_svg_dimensions_transparency_and_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'photo.png'
            Image.new('RGBA',(400,200),(10,20,30,0)).save(source)
            result=transform_image(source,{'format':'SVG','width':100,'height':100,'keep_ratio':True})
            self.assertEqual(result.suffix,'.svg')
            root=ET.fromstring(result.read_bytes())
            self.assertEqual(root.attrib['viewBox'],'0 0 100 50')
            self.assertEqual(root.attrib['width'],'100')
            image=root.find('{http://www.w3.org/2000/svg}image')
            embedded=image.get('href')
            self.assertTrue(embedded.startswith('data:image/png;base64,'))
            with Image.open(io.BytesIO(base64.b64decode(embedded.split(',',1)[1]))) as raster:
                self.assertEqual(raster.size,(100,50))
                self.assertEqual(raster.getpixel((0,0))[3],0)
            with open_preview(result) as preview:self.assertEqual(preview.size,(100,50))

    def test_worker_publishes_svg_and_reports_final_format(self):
        from social_media import save_media
        payload=io.BytesIO()
        Image.new('RGB',(20,10),'red').save(payload,format='PNG')
        response=MagicMock()
        response.headers={'Content-Type':'image/png','Content-Length':str(len(payload.getvalue()))}
        response.iter_content.return_value=[payload.getvalue()]
        session=MagicMock()
        session.get.return_value.__enter__.return_value=response
        with tempfile.TemporaryDirectory() as folder:
            events=[]
            config={'url':'https://example.test/photo','folder':folder,'mode':'photos','image_options':{'format':'SVG','width':0,'height':0,'keep_ratio':True}}
            result=save_media(session,config['url'],{'extension':'png'},config,lambda event,**data:events.append((event,data)),None,1)
            self.assertTrue(Path(result).exists())
            report=next(data for event,data in events if event=='file')
            self.assertEqual(report['mode'],'SVG')
            self.assertEqual(report['size'],Path(result).stat().st_size)

    @unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
    def test_ui_svg_preview_and_queue_options(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False)
            try:
                app.folder.set(folder)
                pane=app.images_page
                pane.format.set('SVG')
                pane.url.set('https://example.test/photo.png')
                payload=io.BytesIO()
                Image.new('RGB',(100,50),'red').save(payload,format='PNG')
                pane.preview_bytes=payload.getvalue()
                pane.render_preview()
                self.assertIn('100 × 50',pane.status.get())
                self.assertIsNotNone(pane.photo)
                self.assertTrue(pane.format_note.grid_info())
                pane.enqueue()
                self.assertEqual(app.library.load_queue()[0]['image_options']['format'],'SVG')
            finally:app.destroy()
