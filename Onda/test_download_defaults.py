import os,tempfile,unittest
from unittest.mock import patch,Mock
from download_defaults import effective_download,automatic_social
from advanced_options import DEFAULTS

class EffectiveDownloadTests(unittest.TestCase):
    def test_defaults_and_independence(self):
        self.assertFalse(DEFAULTS['simple_download_ui']);self.assertTrue(DEFAULTS['social_best_quality'])
        for simple in (False,True):
            config={'url':'https://instagram.com/p/test','mode':'mp3','simple_download_ui':simple,'social_best_quality':True,'hidden_tabs':['images']}
            self.assertEqual(effective_download(config)['mode'],'social')
            self.assertEqual(config['mode'],'mp3')
        self.assertEqual(effective_download({'url':'https://instagram.com/p/x','mode':'mp3','social_best_quality':False})['mode'],'mp3')
    def test_host_boundaries_and_other_platforms(self):
        for url in ['https://instagram.com.evil.test/x','https://evilinstagram.com/x','https://x.com/p/1','https://youtube.com/watch?v=x']:
            self.assertFalse(automatic_social({'url':url,'social_best_quality':True}))
        for host in ['instagram.com','www.tiktok.com','vm.tiktok.com','kw.ai','www.kwai.com']:
            self.assertTrue(automatic_social({'url':'https://'+host+'/x','social_best_quality':True}))
    def test_simple_video_catalog_and_photo_quality(self):
        for url,mode,quality in [('https://youtube.com/watch?v=x','video',None),('https://open.spotify.com/track/x','mp3','320 kbps')]:
            result=effective_download({'url':url,'mode':'mp4','simple_download_ui':True,'height':480,'fps':24})
            self.assertEqual(result['mode'],mode);self.assertIsNone(result['height']);self.assertIsNone(result['fps']);self.assertEqual(result['audio_quality'],quality)
        self.assertEqual(effective_download({'url':'https://open.spotify.com/track/x','mode':'photos','simple_download_ui':True})['mode'],'mp3')
        result=effective_download({'url':'https://example.com/image.jpg','mode':'photos','simple_download_ui':True})
        self.assertEqual(result['image_options'],{'format':'Original','width':0,'height':0,'keep_ratio':True})
    def test_legacy_jobs_and_operations_unchanged(self):
        for config in [{'mode':'mp3','url':'https://tiktok.com/x'}, {'_operation':'video_convert','simple_download_ui':True,'social_best_quality':True,'mode':'mp4','height':480}]:
            self.assertEqual(effective_download(config),config)
    def test_social_auto_preserves_picker_but_locks_quality(self):
        from social_media import download_post
        config={'url':'https://instagram.com/p/x','mode':'mp3','social_best_quality':True}
        picker=Mock()
        with patch('social_media._download_post',return_value=True) as download:
            download_post(config,Mock(),Mock(),picker)
            wrapped=download.call_args.args[3]
            self.assertIsNotNone(wrapped);self.assertEqual(download.call_args.args[0]['mode'],'social')
            picker.return_value={'selected_ids':['1'],'media_modes':{'1':'mp3'}}
            self.assertEqual(wrapped([]),{'selected_ids':['1'],'media_modes':{}})
            download_post(dict(config,social_best_quality=False),Mock(),Mock(),picker)
            self.assertIs(download.call_args.args[3],picker)

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class SimpleUiTests(unittest.TestCase):
    def test_immediate_toggle_saved_values_jobs_and_restart(self):
        from app import App
        from preferences import PreferenceStore
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.update()
            try:
                self.assertFalse(app.simple_download_ui.get());self.assertTrue(app.social_best_quality.get())
                saved_mode=app.mode.get();saved_height=app.height.get();saved_spacing=app.interface_spacing.get()
                app.simple_download_ui.set(True);app.update()
                self.assertFalse(app.format_box.winfo_ismapped())
                self.assertEqual(app.mode.get(),saved_mode);self.assertEqual(app.height.get(),saved_height)
                self.assertEqual(app.interface_spacing.get(),saved_spacing);self.assertEqual(tuple(app.hidden_tabs.get()),())
                app.detect_duplicates.set(False)
                ids=app.add(lines=['https://instagram.com/p/test'],overrides={'display_name':'fixture'})
                self.assertEqual(app.jobs[ids[0]]['mode'],'social')
                self.assertIsNone(app.jobs[ids[0]]['height'])
                ids=app.add(lines=['https://open.spotify.com/track/fixture'],overrides={'display_name':'catalog fixture','mode':'photos'})
                self.assertEqual(app.jobs[ids[0]]['mode'],'mp3');self.assertEqual(app.jobs[ids[0]]['audio_quality'],'320 kbps')
                app.pages.select(app.images_page);app.update()
                self.assertEqual(app.images_page.options(),{'format':'Original','width':0,'height':0,'keep_ratio':True})
                self.assertFalse(app.images_page.custom.winfo_ismapped())
                app.pages.select(app.playlist_page);app.update()
                self.assertFalse(app.playlist_page.quality_combo.winfo_ismapped())
                app.simple_download_ui.set(False);app.pages.select(app.download_page);app.update()
                self.assertTrue(app.format_box.winfo_ismapped())
                self.assertEqual(app.mode.get(),saved_mode)
                app.simple_download_ui.set(True);app.persist_preferences()
                loaded=PreferenceStore().load();self.assertTrue(loaded['simple_download_ui']);self.assertTrue(loaded['social_best_quality'])
            finally:app.destroy()
