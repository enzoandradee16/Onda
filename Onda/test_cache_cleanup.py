import tempfile,unittest,sqlite3
from contextlib import closing
from pathlib import Path
from cache_cleanup import cache_info,clear_cache
class CacheCleanupTests(unittest.TestCase):
    def test_only_reconstructible_files_are_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cache=root/'extractor-cache'/'nested';cache.mkdir(parents=True)
            (cache/'data.json').write_bytes(b'cached')
            (root/'preview-default.mp3').write_bytes(b'preview')
            images=root/'image-preview';images.mkdir();(images/'preview.png').write_bytes(b'image')
            for name in ('settings.json','library.sqlite3','spotify.json','cookies.txt','choice-cache.sqlite3','download.mp3'):(root/name).write_bytes(b'KEEP')
            db=sqlite3.connect(root/'artist-aliases.sqlite3');db.execute('CREATE TABLE aliases(key TEXT,data TEXT)');db.execute("INSERT INTO aliases VALUES('x','cached')");db.execute('CREATE TABLE gate(id INTEGER,next REAL)');db.execute('INSERT INTO gate VALUES(1,12345)');db.commit();db.close()
            self.assertGreater(cache_info(root)['bytes'],0)
            result=clear_cache(root);self.assertEqual(result['failed'],0)
            self.assertFalse((cache/'data.json').exists())
            self.assertFalse((root/'preview-default.mp3').exists())
            self.assertFalse((images/'preview.png').exists())
            for name in ('settings.json','library.sqlite3','spotify.json','cookies.txt','choice-cache.sqlite3','download.mp3'):self.assertEqual((root/name).read_bytes(),b'KEEP')
            with closing(sqlite3.connect(root/'artist-aliases.sqlite3')) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM aliases').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT next FROM gate').fetchone()[0],12345)
    def test_missing_cache_does_not_create_anything(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'missing'
            self.assertEqual(clear_cache(root),{'bytes':0,'removed':0,'failed':0})
            self.assertFalse(root.exists())

import os,time
from unittest.mock import patch
@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class CacheControlsTests(unittest.TestCase):
    def test_settings_control_clears_cache_and_blocks_during_download(self):
        from app import App
        from cache_ui import CacheControls
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.withdraw()
            try:
                def descendants(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from descendants(child)
                controls=next(w for w in descendants(app.settings_window) if isinstance(w,CacheControls))
                def wait():
                    deadline=time.monotonic()+3
                    while controls.working and time.monotonic()<deadline:app.update();time.sleep(.02)
                    self.assertFalse(controls.working)
                wait()
                cache=Path(folder)/'Onda'/'extractor-cache';cache.mkdir(parents=True)
                file=cache/'temporary';file.write_bytes(b'CACHE')
                app.running=True;controls.run(True);self.assertTrue(file.exists())
                app.running=False;controls.run(True);wait();self.assertFalse(file.exists())
            finally:app.destroy()
