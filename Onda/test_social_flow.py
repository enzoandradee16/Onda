import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from instagram_media import product_items
from media_selection import validate_selection
from photo_music import direct_audio, instagram_audio, render_photo_video
from social_media import download_selected, kwai_images, session_for
from tiktok_media import post_items


class SocialFlowTests(unittest.TestCase):
    def test_single_photo_asks_even_with_mp3_and_without_music(self):
        for audio in (None, direct_audio('https://cdn.example/song.mp3')):
            choose=Mock(return_value={'selected_ids':['1']})
            items=[('https://cdn.example/photo.jpg',{'extension':'jpg','_photo_audio':audio})]
            with patch('social_media.save_media',return_value='photo.jpg') as save:
                download_selected(items,Mock(),{'mode':'mp3','url':'https://www.tiktok.com/@a/photo/123'},Mock(),Mock(),choose)
            candidate=choose.call_args.args[0][0]
            self.assertTrue(candidate['photo_choice'])
            self.assertEqual(candidate['has_audio'],bool(audio))
            self.assertEqual(save.call_args.args[3]['mode'],'photos')
            self.assertNotIn('_photo_audio',candidate)

    def test_single_photo_mp4_selected_explicitly(self):
        items=[('https://cdn.example/photo.jpg',{'extension':'jpg','_photo_audio':direct_audio('https://cdn.example/audio.mp3')})]
        choice=Mock(return_value={'selected_ids':['1'],'media_modes':{'1':'photo_video'}})
        with patch('social_media.save_media',return_value='photo.mp4') as save:
            download_selected(items,Mock(),{'mode':'mp3','url':'https://www.instagram.com/p/a/'},Mock(),Mock(),choice)
        self.assertEqual(save.call_args.args[3]['mode'],'photo_video')

    def test_photo_video_requires_single_photo_and_soundtrack(self):
        reply={'selected_ids':['1'],'media_modes':{'1':'photo_video'}}
        for candidate in ({'id':'1','kind':'Foto'}, {'id':'1','kind':'Foto','photo_choice':True}, {'id':'1','kind':'Vídeo'}):
            with self.assertRaises(ValueError):validate_selection(reply,[candidate])
        self.assertEqual(validate_selection(reply,[{'id':'1','kind':'Foto','photo_choice':True,'has_audio':True}]),(['1'],{'1':'photo_video'}))

    def test_video_respects_mp3_mp4_and_mkv(self):
        for mode in ('mp3','mp4','video'):
            with patch('social_media.save_media',return_value='saved') as save:
                download_selected([('https://cdn.example/v.mp4',{'extension':'mp4'})],Mock(),{'mode':mode},Mock(),Mock(),Mock())
            self.assertEqual(save.call_args.args[3]['mode'],mode)

    def test_mixed_post_per_video_output_and_automatic_photo(self):
        items=[('https://cdn.example/p.jpg',{'extension':'jpg'}),('https://cdn.example/v.mp4',{'extension':'mp4'})]
        choice=Mock(return_value={'selected_ids':['1','2'],'media_modes':{'2':'mp3'}})
        with patch('social_media.save_media',side_effect=['photo.jpg','audio.mp3']) as save:
            result=download_selected(items,Mock(),{'mode':'mp4'},Mock(),Mock(),choice)
        self.assertEqual(result,['photo.jpg','audio.mp3'])
        self.assertEqual([c.args[3]['mode'] for c in save.call_args_list],['photos','mp3'])
        choice.assert_called_once()

    def test_instagram_and_tiktok_extract_only_post_audio(self):
        music={'music_info':{'music_asset_info':{'progressive_download_url':'https://cdn.example/a.m4a'},'music_consumption_info':{'audio_asset_start_time_in_ms':2000,'audio_asset_end_time_in_ms':5000}}}
        product={'music_metadata':music,'image_versions2':{'candidates':[{'url':'https://cdn.example/p.jpg'}]}}
        audio=list(product_items(Mock(),product))[0][1]['_photo_audio']
        self.assertEqual(audio,{'url':'https://cdn.example/a.m4a','start':2,'duration':3})
        source=Mock();source._match_id.return_value='123'
        post={'id':'123','music':{'playUrl':'https://cdn.example/t.mp3'},'imagePost':{'images':[{'imageURL':{'urlList':['https://cdn.example/p.jpg']}}]}}
        self.assertEqual(list(post_items(source,post,'https://www.tiktok.com/@a/photo/123'))[0][1]['_photo_audio']['url'],'https://cdn.example/t.mp3')
        self.assertIsNone(direct_audio('file:///private/file'))
        self.assertIsNone(direct_audio('https://cdn.example/a',float('nan')))

    def test_kwai_photo_music_and_nuxt_state(self):
        node={'photo_id_str':'123','music':{'playUrl':'https://cdn.example/a.mp3'},'atlas':{'images':['https://cdn.example/p.jpg']}}
        html='<script>window.__NUXT__=(function(){x[0]='+json.dumps(node)+';return {videoList:x}}());</script>'
        items=list(kwai_images(html,'https://www.kwai.com/@a/photo/123'))
        self.assertEqual(len(items),1)
        self.assertEqual(items[0][1]['_photo_audio']['url'],'https://cdn.example/a.mp3')

    @unittest.skipUnless(os.environ.get('ONDA_FFMPEG'),'FFmpeg integration')
    def test_real_photo_music_mp4_contains_both_streams_and_original_photo_unchanged(self):
        from audio_tools import executable
        from PIL import Image
        from social_media import save_media
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);photo=root/'image.png';song=root/'song.wav'
            Image.new('RGB',(161,123),'blue').save(photo)
            original=photo.read_bytes()
            subprocess.run([executable('ffmpeg'),'-y','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',str(song)],check=True,capture_output=True)
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=folder))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}'
                events=[]
                config={'url':'https://www.tiktok.com/@test/photo/123','mode':'photo_video','folder':str(root/'out'),'ffmpeg':os.environ['ONDA_FFMPEG']}
                with session_for() as session:
                    target=save_media(session,url+'/image.png',{'extension':'png','_photo_audio':direct_audio(url+'/song.wav')},config,lambda kind,**data:events.append((kind,data)),Mock(),1)
                info=json.loads(subprocess.check_output([executable('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',target]))
                self.assertEqual({s['codec_type'] for s in info['streams']},{'video','audio'})
                self.assertAlmostEqual(float(info['format']['duration']),1,delta=.3)
                self.assertEqual(photo.read_bytes(),original)
                self.assertTrue(target.endswith('.mp4'))
                self.assertFalse((root/'out'/'.onda-work').exists())
                self.assertEqual([d['mode'] for k,d in events if k=='file'],['MP4'])
            finally:server.shutdown();server.server_close();thread.join()

    def test_missing_audio_never_renders_or_publishes(self):
        with self.assertRaisesRegex(ValueError,'Só foto'):
            render_photo_video(Path('photo.jpg'),None,Mock(),{}, {},Mock())



@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class SinglePhotoPickerTests(unittest.TestCase):
    def test_picker_returns_photo_music_choice(self):
        import tkinter as tk
        from media_picker import MediaPicker
        root=tk.Tk();root.social_cookies=tk.StringVar()
        confirm=Mock()
        picker=MediaPicker(root,{'candidates':[{'id':'1','number':1,'kind':'Foto','title':'Foto','photo_choice':True,'has_audio':True}]},confirm,Mock())
        try:
            root.update()
            self.assertEqual(picker.video_modes['1'].get(),'Só foto')
            picker.video_modes['1'].set('Foto com música · MP4')
            picker.accept()
            confirm.assert_called_once_with({'selected_ids':['1'],'media_modes':{'1':'photo_video'}})
        finally:picker.destroy();root.destroy()

if __name__=='__main__':unittest.main()
