import json,unittest,threading
from unittest.mock import MagicMock,patch
from lyrics_service import fetch_lyrics

class LyricsServiceTests(unittest.TestCase):
    def run_fetch(self,payload,status=200):
        session=MagicMock();response=session.get.return_value.__enter__.return_value
        response.status_code=status;response.iter_content.return_value=[json.dumps(payload).encode()]
        with patch('lyrics_service.read_audio',return_value={'title':'Test','artists':['Artist'],'duration':123}):
            return fetch_lyrics('test.mp3',session=session)
    def test_synced(self):
        result=self.run_fetch({'syncedLyrics':'[00:01.00]Test'})
        self.assertTrue(result['synced']);self.assertEqual(result['lines'],[(1,'Test')])
    def test_plain_does_not_invent_timestamps(self):
        result=self.run_fetch({'plainLyrics':'Test'})
        self.assertFalse(result['synced']);self.assertEqual(result['lines'],[(0,'Test')])
    def test_missing_does_not_replace_current_lyrics(self):
        with self.assertRaises(ValueError):self.run_fetch({},404)
    def test_instrumental(self):
        with self.assertRaises(ValueError):self.run_fetch({'instrumental':True})

    def test_alternatives_offer_versions_without_loading_first_result(self):
        session=MagicMock();response=session.get.return_value.__enter__.return_value
        response.status_code=200
        response.iter_content.return_value=[json.dumps([{'id':1,'trackName':'Test','artistName':'Artist','albumName':'Album','duration':120,'syncedLyrics':'[00:01]First'},{'id':2,'trackName':'Test','artistName':'Artist','duration':125,'plainLyrics':'Other'}]).encode()]
        with patch('lyrics_service.read_audio',return_value={'title':'Test','artists':['Artist']}):
            result=fetch_lyrics('test.mp3',session=session,alternatives=True)
        self.assertEqual(len(result['candidates']),2)
        self.assertTrue(result['candidates'][0]['synced'])
        self.assertFalse(result['candidates'][1]['synced'])
        self.assertTrue(result['candidates'][0]['title'].endswith(' · 2:00'))
        self.assertTrue(result['candidates'][1]['title'].endswith(' · 2:05'))
        self.assertIn('/search',session.get.call_args.args[0])

    def test_lyricsfile_word_timing_preserves_spaces_and_precision(self):
        import yaml
        from lyrics_service import timed_record
        from synced_lyrics import karaoke_at
        raw=yaml.safe_dump({'version':'1.0','lines':[{'start_ms':1200,'text':'Hello world','words':[{'start_ms':1200,'text':'Hello '},{'start_ms':1905,'text':'world'}]}]})
        rows,word_sync=timed_record({'lyricsfile':raw,'syncedLyrics':'[00:01.20]Fallback'})
        self.assertTrue(word_sync)
        self.assertIn('<00:01.905>world',rows[0][1])
        self.assertIn('<b>Hello </b>world',karaoke_at(rows,1.5))
        self.assertIn('<b>world</b>',karaoke_at(rows,1.906))

    def test_malformed_lyricsfile_falls_back_to_line_timing(self):
        from lyrics_service import timed_record
        for raw in ("version: '2.0'", "lines: [broken", "version: '1.0'\nversion: '1.0'", "a: &x [1]\nb: *x"):
            rows,word_sync=timed_record({'lyricsfile':raw,'syncedLyrics':'[00:01]Fallback'})
            self.assertEqual(rows,[(1,'Fallback')]);self.assertFalse(word_sync)

    def test_word_only_service_result(self):
        import yaml
        result=self.run_fetch({'hasWordSync':True,'lyricsfile':yaml.safe_dump({'version':'1.0','lines':[{'text':'Test','start_ms':1000,'words':[{'text':'Test','start_ms':1000}]}]})})
        self.assertTrue(result['synced']);self.assertTrue(result['word_synced'])

    def test_catalog_metadata_survives_untagged_cache_file(self):
        session=MagicMock();response=session.get.return_value.__enter__.return_value
        response.status_code=200;response.iter_content.return_value=[b'{"plainLyrics":"Hello"}']
        with patch('lyrics_service.read_audio',return_value={'title':'audio','artists':[],'duration':120}):
            fetch_lyrics('audio.wav',{'title':'Correct title','artists':['Correct artist'],'album':'Album'},session=session)
        params=session.get.call_args.kwargs['params']
        self.assertEqual(params['track_name'],'Correct title')
        self.assertEqual(params['artist_name'],'Correct artist')
        self.assertEqual(params['duration'],120)

    def test_supplied_recording_is_not_replaced_by_download_tags(self):
        session=MagicMock();response=session.get.return_value.__enter__.return_value
        response.status_code=200;response.iter_content.return_value=[b'{"plainLyrics":"Hello"}']
        with patch('lyrics_service.read_audio',return_value={'title':'Video title','artists':['Channel'],'album':'Video'}):
            fetch_lyrics('audio.webm',{'title':'Catalog title','artists':['Artist'],'album':'Album'},session=session)
        self.assertEqual(session.get.call_args.kwargs['params'],{'track_name':'Catalog title','artist_name':'Artist','album_name':'Album'})

    def test_automatic_choice_prefers_matching_duration_over_first_result(self):
        from lyrics_service import best_recording
        rows=[dict(trackName='Song',artistName='Artist',duration=260,syncedLyrics='[00:01]Wrong'),dict(trackName='Song',artistName='Artist',duration=201,syncedLyrics='[00:01]Right')]
        self.assertIs(best_recording(rows,'Song','Artist',duration=200),rows[1])
    def test_automatic_choice_rejects_wrong_artist_and_version(self):
        from lyrics_service import best_recording
        rows=[dict(trackName='Song',artistName='Someone else',duration=200,plainLyrics='Wrong'),dict(trackName='Song Live',artistName='Artist',duration=200,plainLyrics='Wrong')]
        self.assertIsNone(best_recording(rows,'Song','Artist',duration=200))
    def test_automatic_choice_prefers_synced_same_recording(self):
        from lyrics_service import best_recording
        rows=[dict(trackName='Song',artistName='Artist',duration=200,plainLyrics='Plain'),dict(trackName='Song',artistName='Artist',duration=200,syncedLyrics='[00:01]Synced')]
        self.assertIs(best_recording(rows,'Song','Artist',duration=200),rows[1])
    def test_missing_exact_result_searches_and_selects_automatically(self):
        session=MagicMock();response=session.get.return_value.__enter__.return_value
        response.status_code=200
        response.iter_content.side_effect=[[],[json.dumps([dict(trackName='Song',artistName='Artist',duration=200,syncedLyrics='[00:01]Chosen')]).encode()]]
        response.status_code=404
        def get(*args,**kwargs):
            response.status_code=404 if args[0].endswith('/get') else 200
            return session.get.return_value
        session.get.side_effect=get
        response.iter_content.side_effect=None
        response.iter_content.return_value=[json.dumps([dict(trackName='Song',artistName='Artist',duration=200,syncedLyrics='[00:01]Chosen')]).encode()]
        with patch('lyrics_service.read_audio',return_value={'title':'Song','artists':['Artist'],'duration':200}):
            result=fetch_lyrics('audio.wav',session=session)
        self.assertEqual(result['lines'],[(1,'Chosen')])
        self.assertEqual(session.get.call_count,2)
