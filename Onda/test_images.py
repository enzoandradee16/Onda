import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
from image_output import transform_image, validate_options


def options(fmt='Original', width=0, height=0, ratio=True):
    return {'format':fmt,'width':width,'height':height,'keep_ratio':ratio}


class ImageExportTests(unittest.TestCase):
    def test_original_unchanged_and_proportional_resize(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'landscape.png'
            Image.new('RGBA',(600,300),(255,0,0,0)).save(source)
            original=source.read_bytes()
            self.assertEqual(transform_image(source,options()).read_bytes(),original)
            result=transform_image(source,options('PNG',200,200))
            with Image.open(result) as image:
                self.assertEqual(image.size,(200,100))
                self.assertEqual(image.getpixel((0,0))[3],0)
            result=transform_image(result,options('PNG',1000,1000))
            with Image.open(result) as image:
                self.assertEqual(image.size,(200,100))

    def test_jpeg_white_transparency_and_exact_dimensions(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'transparent.png'
            Image.new('RGBA',(80,40),(0,0,0,0)).save(source)
            result=transform_image(source,options('JPG',30,30,False))
            self.assertEqual(result.suffix,'.jpg')
            self.assertFalse(source.exists())
            with Image.open(result) as image:
                self.assertEqual(image.size,(30,30))
                self.assertEqual(image.mode,'RGB')
                self.assertEqual(image.getpixel((0,0)),(255,255,255))

    def test_animation_webp_preserved_and_jpeg_first_frame_warns(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'animation.gif'
            frames=[Image.new('RGB',(50,50),color) for color in ('red','blue')]
            frames[0].save(source,save_all=True,append_images=frames[1:],duration=[100,200],loop=0)
            result=transform_image(source,options('WebP',25,25))
            with Image.open(result) as image:
                self.assertEqual(image.n_frames,2)
                self.assertEqual(image.size,(25,25))
            events=[]
            transform_image(result,options('JPG'),lambda event,**data:events.append(data))
            self.assertTrue(any('primeiro quadro' in e['message'] for e in events))

    def test_options_reject_invalid_dimensions_and_format(self):
        for value in (options('exe'),options('PNG',-1,100),options('PNG',20000,1),options('PNG',True,100),options('PNG',0,100)):
            with self.assertRaises(ValueError):validate_options(value)

    def test_download_converts_before_publish_and_reports_final_file(self):
        from social_media import save_media
        payload=io.BytesIO()
        Image.new('RGBA',(200,100),'red').save(payload,format='PNG')
        response=MagicMock()
        response.headers={'Content-Type':'image/png','Content-Length':str(len(payload.getvalue()))}
        response.iter_content.return_value=[payload.getvalue()]
        session=MagicMock()
        session.get.return_value.__enter__.return_value=response
        with tempfile.TemporaryDirectory() as folder:
            events=[]
            config={'url':'https://example.test/photo','folder':folder,'mode':'photos','image_options':options('WebP',50,50)}
            result=save_media(session,config['url'],{'extension':'png','title':'Photo'},config,lambda event,**data:events.append((event,data)),None,1)
            self.assertEqual(Path(result).suffix,'.webp')
            with Image.open(result) as image:self.assertEqual(image.size,(50,25))
            report=next(data for event,data in events if event=='file')
            self.assertEqual(report['mode'],'WEBP')
            self.assertEqual(report['size'],Path(result).stat().st_size)


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class ImagesUiTests(unittest.TestCase):
    def test_tab_queue_options_independence_persistence_and_minimum_layout(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False)
            try:
                app.folder.set(folder)
                app.geometry('840x720')
                app.pages.select(app.images_page)
                app.update()
                pane=app.images_page
                self.assertEqual(len(app.pages.tabs()),8)
                visible_tabs=set()
                import tkinter as tk
                for x in range(app.pages.winfo_width()):
                    try:
                        visible_tabs.add(app.pages.index(f'@{x},15'))
                    except tk.TclError:
                        pass
                self.assertEqual(visible_tabs,set(range(8)))
                self.assertLess(pane.winfo_rooty()+pane.winfo_height(),app.winfo_rooty()+app.winfo_height()+1)
                pane.url.set('https://example.com/image.png')
                pane.format.set('WebP')
                pane.size.set('Personalizado')
                pane.width.set('500');pane.height.set('300')
                original_mode=app.mode.get()
                pane.enqueue()
                jobs=list(app.jobs.values())
                self.assertEqual(len(jobs),1)
                self.assertEqual(jobs[0]['mode'],'photos')
                self.assertEqual(jobs[0]['image_options'],options('WebP',500,300))
                self.assertEqual(app.mode.get(),original_mode)
                self.assertEqual(app.library.load_queue()[0]['image_options'],options('WebP',500,300))
                pane.format.set('PNG');pane.enqueue()
                self.assertEqual(len(app.jobs),2)
                with patch.object(app,'start') as start:
                    pane.enqueue(True)
                    start.assert_called_once()
                    self.assertIn(start.call_args.kwargs['only_item'],app.jobs)
                pane.preview_bytes=io.BytesIO()
                Image.new('RGB',(100,50),'red').save(pane.preview_bytes,format='PNG')
                pane.preview_bytes=pane.preview_bytes.getvalue()
                pane.render_preview()
                self.assertIn('100 × 50',pane.status.get())
                self.assertIsNotNone(pane.photo)
            finally:
                app.destroy()
