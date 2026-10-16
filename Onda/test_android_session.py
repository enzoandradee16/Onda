"""Android session-policy regressions without network or account credentials."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'Celular/app/src/main/python/mobile_backend.py'
spec=importlib.util.spec_from_file_location('android_session_adapter',path)
backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)

class AndroidSessionTests(unittest.TestCase):
    def test_spotify_audio_lookup_uses_youtube_session_and_browser_agent(self):
        config={'url':'https://open.spotify.com/playlist/fixture','cookies_file':'general.txt','youtube_cookies_file':'youtube.txt','youtube_user_agent':'Session browser'}
        params={'http_headers':{'Referer':'https://youtube.com'},'cookiefile':'stale.txt'}
        options=backend.session_options(params,config)
        self.assertEqual(options['cookiefile'],'youtube.txt')
        self.assertEqual(options['http_headers']['User-Agent'],'Session browser')
        self.assertEqual(options['http_headers']['Referer'],'https://youtube.com')
        self.assertEqual(params['cookiefile'],'stale.txt')
        self.assertNotIn('User-Agent',params['http_headers'])
    def test_general_cookie_import_remains_supported(self):
        self.assertEqual(backend.session_options({}, {'url':'https://youtube.com/watch?v=x','cookies_file':'import.txt'})['cookiefile'],'import.txt')
    def test_removing_session_does_not_reuse_stale_cookie_file(self):
        self.assertNotIn('cookiefile',backend.session_options({'cookiefile':'old.txt'},{'url':'https://youtube.com/watch?v=x','cookies_file':'','youtube_cookies_file':''}))
    def test_social_downloads_keep_separate_cookies(self):
        for url in ('https://instagram.com/p/fixture/','https://tiktok.com/@fixture/video/1','https://x.com/fixture/status/1'):
            with self.subTest(url=url):
                options=backend.session_options({}, {'url':url,'cookies_file':'social.txt','youtube_cookies_file':'youtube.txt','youtube_user_agent':'private-session-agent'})
                self.assertEqual(options['cookiefile'],'social.txt');self.assertNotIn('http_headers',options)
    def test_rejected_saved_session_is_not_reported_as_missing_login(self):
        try:
            backend._local.state={'config':{'youtube_cookies_file':'saved.txt'}}
            self.assertIn('não aceitou a sessão atual',backend.readable_error("Sign in to confirm you're not a bot"))
            backend._local.state={'config':{}}
            self.assertIn('Abra Menu',backend.readable_error("Sign in to confirm you're not a bot"))
        finally:backend._local.state=None
    def test_android_search_forwards_auto_metadata_independently(self):
        from unittest.mock import Mock,patch
        for enabled in (True,False):
            with self.subTest(enabled=enabled):
                client=Mock();client.resolve.return_value={'title':'Selected metadata'}
                with patch.object(backend,'client',return_value=client):
                    result=backend.perform('search',{'query':'https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl','auto_metadata':enabled,'auto_match':not enabled})
                self.assertEqual(result['tracks'][0]['title'],'Selected metadata')
                self.assertEqual(client.resolve.call_args.kwargs.get('automatic',False),enabled)
                client.close.assert_called_once()
    def test_no_user_agent_is_invented_for_imported_cookies(self):
        options=backend.session_options({}, {'url':'https://youtube.com/watch?v=x','youtube_cookies_file':'imported.txt'})
        self.assertNotIn('http_headers',options)

if __name__=='__main__':unittest.main()
