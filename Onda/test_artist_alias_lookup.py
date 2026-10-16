from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch,MagicMock
from artist_alias_lookup import AliasCache,discover_aliases,context_key,get_json,LookupUnavailable
from matching import score_candidate,find_youtube

ID='11111111-1111-4111-8111-111111111111'
OTHER='22222222-2222-4222-8222-222222222222'
RECORD=dict(title='My song',artists=['Original Artist Name'],album='My album',duration_ms=200000)
ROW={'id':OTHER,'title':'My song','length':200000,'releases':[{'title':'My album'}],'artist-credit':[{'name':'Stage Name','artist':{'id':ID,'name':'Stage Name'}}]}
PROFILE={'id':ID,'name':'Stage Name','aliases':[{'name':'Original Artist Name','type':'Legal name'},{'name':'名義 名前','type':'Artist name'},{'name':'Wrong Speling','type':'Search hint'}],'relations':[]}
VIDEO=dict(id='abcdefghijk',title='Stage Name - My song',channel='Stage Name - Topic',duration=200)

class ArtistAliasLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cache=AliasCache(Path(self.temp.name)/'cache.sqlite3')
    def fetch(self,path,params,cache):
        if path=='recording':return {'recordings':[deepcopy(ROW)]}
        if path=='artist/'+ID:return deepcopy(PROFILE)
        return {'artists':[]}
    def test_verified_recording_loads_multilingual_aliases_and_ignores_search_hints(self):
        original=deepcopy(RECORD);fetch=Mock(side_effect=self.fetch)
        groups=discover_aliases(RECORD,cache=self.cache,fetch=fetch)
        self.assertEqual(fetch.call_count,2);self.assertIn('名義 名前',groups[0]['aliases'])
        self.assertNotIn('Wrong Speling',groups[0]['aliases']);self.assertEqual(RECORD,original)
        self.assertIsNone(score_candidate(RECORD,VIDEO))
        self.assertEqual(score_candidate(dict(RECORD,_verified_artist_aliases=groups),VIDEO),1)
    def test_cache_survives_new_instance_without_network(self):
        groups=discover_aliases(RECORD,cache=self.cache,fetch=self.fetch)
        restored=AliasCache(self.cache.path);fetch=Mock(side_effect=AssertionError('network'))
        self.assertEqual(discover_aliases(RECORD,cache=restored,fetch=fetch),groups);fetch.assert_not_called()
    def test_expiration_and_negative_cache(self):
        fetch=Mock(return_value={'recordings':[],'artists':[]})
        with patch('artist_alias_lookup.time.time',return_value=100):
            self.assertEqual(discover_aliases(RECORD,cache=self.cache,fetch=fetch),[])
        count=fetch.call_count
        with patch('artist_alias_lookup.time.time',return_value=200):discover_aliases(RECORD,cache=self.cache,fetch=fetch)
        self.assertEqual(fetch.call_count,count)
        with patch('artist_alias_lookup.time.time',return_value=100000):discover_aliases(RECORD,cache=self.cache,fetch=fetch)
        self.assertGreater(fetch.call_count,count)
    def test_wrong_duration_title_album_and_version_are_rejected(self):
        for changes in ({'title':'Other song'},{'length':260000},{'releases':[{'title':'Other album'}]},{'title':'My song Remix'}):
            with self.subTest(changes=changes),tempfile.TemporaryDirectory() as folder:
                cache=AliasCache(Path(folder)/'db')
                def fetch(path,params,cache):return {'recordings':[dict(ROW,**changes)]} if path=='recording' else {'artists':[]}
                self.assertEqual(discover_aliases(RECORD,cache=cache,fetch=fetch),[])
    def test_homonyms_are_not_merged(self):
        other=dict(ROW,**{'artist-credit':[{'artist':{'id':OTHER,'name':'Original Artist Name'}}]})
        fetch=Mock(return_value={'recordings':[ROW,other]})
        self.assertEqual(discover_aliases(RECORD,cache=self.cache,fetch=fetch),[]);self.assertEqual(fetch.call_count,1)
    def test_profile_must_include_exact_original_name_not_just_similar_name(self):
        def fetch(path,params,cache):return {'recordings':[ROW]} if path=='recording' else dict(PROFILE,aliases=[{'name':'Original Name','type':'Artist name'}])
        self.assertEqual(discover_aliases(RECORD,cache=self.cache,fetch=fetch),[])
    def test_artist_search_fallback_requires_recording_confirmation(self):
        seen=[]
        def fetch(path,params,cache):
            seen.append((path,params))
            if path=='recording':return {'recordings':[ROW] if 'arid:' in params['query'] else []}
            if path=='artist':return {'artists':[{'id':ID,'name':'Stage Name','aliases':[{'name':'Original Artist Name'}]}]}
            return PROFILE
        self.assertTrue(discover_aliases(RECORD,cache=self.cache,fetch=fetch))
        self.assertEqual(len(seen),4);self.assertIn('arid:'+ID,seen[-1][1]['query'])
    def test_same_artist_id_cache_only_with_explicit_spotify_relation(self):
        anchor=dict(RECORD,spotify_artist_ids=['A'*22])
        def fetch(path,params,cache):
            value=self.fetch(path,params,cache)
            if path=='artist/'+ID:value['relations']=[{'url':{'resource':'https://open.spotify.com/artist/'+'A'*22}}]
            return value
        groups=discover_aliases(anchor,cache=self.cache,fetch=fetch)
        blocked=Mock(side_effect=AssertionError('network'))
        self.assertEqual(discover_aliases(dict(anchor,title='Another song'),cache=self.cache,fetch=blocked),groups);blocked.assert_not_called()
        different=Mock(return_value={'recordings':[],'artists':[]})
        self.assertEqual(discover_aliases(dict(anchor,spotify_artist_ids=['B'*22]),cache=self.cache,fetch=different),[])
        self.assertTrue(different.called)
    def test_without_stable_artist_relation_cache_is_specific_to_recording(self):
        discover_aliases(RECORD,cache=self.cache,fetch=self.fetch)
        fetch=Mock(return_value={'recordings':[],'artists':[]})
        self.assertEqual(discover_aliases(dict(RECORD,title='Another song'),cache=self.cache,fetch=fetch),[])
        self.assertTrue(fetch.called)
    def test_transient_failure_does_not_become_negative_identity(self):
        failed=Mock(side_effect=LookupUnavailable())
        self.assertEqual(discover_aliases(RECORD,cache=self.cache,fetch=failed),[])
        self.assertIsNone(self.cache.read(context_key(RECORD)))
        self.assertTrue(discover_aliases(RECORD,cache=self.cache,fetch=self.fetch))
    def test_rate_limit_is_shared_by_cache_instances(self):
        other=AliasCache(self.cache.path)
        with patch('artist_alias_lookup.time.time',return_value=100),patch('artist_alias_lookup.time.sleep') as sleep:
            self.cache.request_slot();other.request_slot();self.assertAlmostEqual(sleep.call_args.args[0],1.1)
            self.cache.cool_down(120)
            with self.assertRaises(LookupUnavailable):other.request_slot()
    def test_http_uses_identified_agent_timeout_no_redirect_and_bounded_response(self):
        response=Mock(status_code=200);response.iter_content.return_value=[b'{"recordings": []}']
        context=MagicMock();context.__enter__.return_value=response
        with patch('artist_alias_lookup.requests.get',return_value=context) as get:
            cache=Mock();self.assertEqual(get_json('recording',{'query':'safe'},cache),{'recordings':[]})
            options=get.call_args.kwargs;self.assertIn('ONDA/',options['headers']['User-Agent']);self.assertFalse(options['allow_redirects']);self.assertEqual(options['timeout'],(4,8))
            response.iter_content.return_value=[b'x'*1048577]
            with self.assertRaises(LookupUnavailable):get_json('recording',{},cache)
            response.status_code=429;response.headers={'Retry-After':'120'}
            with self.assertRaises(LookupUnavailable):get_json('recording',{},cache)
            cache.cool_down.assert_called_with(120)
    def test_find_reuses_original_youtube_candidates_after_discovery(self):
        groups=discover_aliases(RECORD,cache=self.cache,fetch=self.fetch)
        downloader=MagicMock();downloader.__enter__.return_value.extract_info.return_value={'entries':[VIDEO]}
        with patch('yt_dlp.YoutubeDL',return_value=downloader),patch('artist_alias_lookup.discover_aliases',return_value=groups):
            result=find_youtube(RECORD,Mock(),prefer_best=True)
        self.assertEqual(downloader.__enter__.return_value.extract_info.call_count,2)
        self.assertEqual(result['artist_alias']['matched_alias'],'Stage Name')
        self.assertIn(ID,result['artist_alias']['source_url'])
    def test_incomplete_identity_does_not_request_database(self):
        fetch=Mock();self.assertEqual(discover_aliases(dict(RECORD,album=None),cache=self.cache,fetch=fetch),[]);fetch.assert_not_called()

if __name__=='__main__':unittest.main()
