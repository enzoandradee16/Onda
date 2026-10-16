from copy import deepcopy
import json
import unittest
from unittest.mock import Mock,patch
from metadata import MetadataClient,MetadataError,spotify_record,base_record
from spotify_metadata import supplement_metadata,prepare_spotify_config,source_label
from spotify_search import cached_record
from spotify_account import SpotifyAccount

ID="A"*22
URL="https://open.spotify.com/track/"+ID

def api_track():
    return dict(id=ID,name="Original title",artists=[{"name":"Original artist"}],album={"name":"Original album","release_date":"2000-01-01","artists":[{"name":"Album artist"}],"images":[{"url":"https://spotify.test/cover.jpg"}]},duration_ms=200000,track_number=3,disc_number=1,explicit=False,external_ids={"isrc":"USABC0000001"})

class SpotifyPriorityTests(unittest.TestCase):
    def test_preserves_every_spotify_field_and_fills_only_missing_values(self):
        anchor=spotify_record(api_track(),ID,URL)
        other=dict(anchor,platform="Deezer",source_url="https://www.deezer.com/track/123",title="Translated title",album="Reissue",artists=["Other credit"],cover_url="https://deezer.test/cover.jpg",explicit=True,genre="Pop")
        original=deepcopy(anchor);result=supplement_metadata(anchor,other,{"selection":"automatic"})
        for key in ("title","artists","album","album_artists","release_date","duration_ms","track_number","disc_number","isrc","explicit","cover_url","platform","source_url","id"):
            self.assertEqual(result[key],anchor[key],key)
        self.assertEqual(result['genre'],'Pop');self.assertEqual(anchor,original)
        self.assertEqual(result['metadata_sources']['genre']['platform'],'Deezer')
        self.assertEqual(result['metadata_sources']['cover_url']['platform'],'Spotify')
        self.assertEqual(source_label(result),'Spotify + Deezer')
    def test_connected_account_used_for_individual_spotify_track_only(self):
        client=MetadataClient();self.addCleanup(client.close)
        getter=Mock(return_value=api_track());client.spotify_get=getter;client.get_json=Mock(return_value={'id':123,'title':'Deezer song','artist':{'name':'Artist'}})
        self.assertEqual(client.fetch(URL)['album'],'Original album');getter.assert_called_once_with('tracks/'+ID)
        getter.reset_mock();client.fetch('https://www.deezer.com/track/123');getter.assert_not_called()
    def test_oauth_failure_keeps_public_fallback(self):
        client=MetadataClient();self.addCleanup(client.close)
        client.spotify_get=Mock(side_effect=MetadataError('Unavailable'))
        client.get_json=Mock(return_value={'title':'Public title','thumbnail_url':'https://spotify.test/public.jpg'})
        self.assertEqual(client.fetch(URL)['title'],'Public title')
    def test_normalized_record_passes_to_worker_without_tokens_or_mutating_queue(self):
        account=Mock(connected=True);account.get.return_value=dict(api_track(),access_token="SECRET",refresh_token="PRIVATE")
        config={'url':URL,'mode':'mp3'};result=prepare_spotify_config(config,account)
        self.assertNotIn('catalog_record',config)
        self.assertEqual(result['catalog_record']['source_url'],URL)
        self.assertNotIn('SECRET',json.dumps(result));self.assertNotIn('PRIVATE',json.dumps(result))
        account.get.assert_called_once_with('tracks/'+ID)
    def test_non_spotify_links_never_use_priority_or_authorization(self):
        account=Mock(connected=True)
        for url in ('https://www.deezer.com/track/123','https://music.apple.com/us/song/123','https://youtube.com/watch?v=abcdefghijk','https://open.spotify.com.evil.test/track/'+ID):
            config={'url':url};self.assertIs(prepare_spotify_config(config,account),config)
        account.get.assert_not_called()
        client=MetadataClient();self.addCleanup(client.close);client.fetch=Mock(return_value={'platform':'Deezer','title':'Untouched'})
        client.complete_spotify=Mock(side_effect=AssertionError('Must not enrich Deezer'))
        self.assertEqual(client.resolve('https://www.deezer.com/track/123'),{'platform':'Deezer','title':'Untouched'})
    def test_playlist_reuses_full_api_metadata(self):
        account=SpotifyAccount.__new__(SpotifyAccount);account.client_id="id";account.refresh_token="refresh";account.access_token=""
        account.get=Mock(side_effect=[{'name':'Playlist'},{'items':[{'item':dict(api_track(),type='track')}],'next':None,'total':1}])
        row=account.playlist(ID)['tracks'][0]
        for key in ('album','album_artists','release_date','track_number','disc_number','isrc','explicit','cover_url'):
            self.assertEqual(row[key],spotify_record(api_track(),ID,URL)[key],key)
        config={'url':URL,'catalog_record':row};self.assertIs(prepare_spotify_config(config,account),config)
        self.assertEqual(account.get.call_count,2)
    def test_partial_cached_spotify_record_is_completed_by_spotify_first(self):
        account=Mock(connected=True);account.get.return_value=api_track()
        partial=base_record('Spotify',ID,URL,'Spotify Embed público');partial.update(title='Original spelling',artists=['Original artist'],duration_ms=200000)
        result=prepare_spotify_config({'url':URL,'catalog_record':partial},account)['catalog_record']
        self.assertEqual(result['title'],'Original spelling');self.assertEqual(result['album'],'Original album')
    def test_isrc_supplement_requires_compatible_recording_and_no_explicit_conflict(self):
        client=MetadataClient();self.addCleanup(client.close)
        anchor=spotify_record(api_track(),ID,URL);anchor['track_number']=None
        other=dict(id=123,title='Original title',artist={'name':'Original artist'},album={'title':'Original album'},duration=200,track_position=3,isrc='USABC0000001',genres='ignored',explicit_lyrics=False)
        client.get_json=Mock(return_value=other);client.search=Mock(return_value=[])
        result=client.complete_spotify(anchor)
        self.assertEqual(result['source_url'],URL);client.search.assert_not_called()
        other['explicit_lyrics']=True
        self.assertNotIn('metadata_supplements',client.complete_spotify(anchor))
    def test_supplement_outage_does_not_discard_usable_spotify_identity(self):
        client=MetadataClient();self.addCleanup(client.close)
        client.get_json=Mock(side_effect=MetadataError('outage'));client.search=Mock(side_effect=MetadataError('outage'))
        anchor=spotify_record(api_track(),ID,URL)
        self.assertEqual(client.complete_spotify(anchor)['title'],anchor['title'])
    def test_android_download_prepares_spotify_record_but_not_other_links(self):
        from test_android_session import backend
        account=Mock(connected=True);account.get.return_value=api_track()
        with patch.object(backend,'account',return_value=account),patch('engine.run_worker',return_value=0) as worker:
            backend.perform('download',{'url':URL,'mode':'mp3'})
            self.assertEqual(worker.call_args.args[0]['catalog_record']['album'],'Original album')
            account.get.reset_mock()
            backend.perform('download',{'url':'https://www.deezer.com/track/123','mode':'mp3'})
            self.assertNotIn('catalog_record',worker.call_args.args[0]);account.get.assert_not_called()
    def test_existing_supplement_provenance_is_not_relabelled_as_spotify(self):
        from spotify_metadata import original_metadata
        anchor=spotify_record(api_track(),ID,URL)
        supplemented=supplement_metadata(anchor,dict(platform='Deezer',source_url='https://www.deezer.com/track/123',genre='Pop'),{})
        self.assertEqual(original_metadata(supplemented)['metadata_sources']['genre']['platform'],'Deezer')
    def test_cached_provenance_survives_without_copying_unknown_sensitive_fields(self):
        anchor=spotify_record(api_track(),ID,URL)
        result=supplement_metadata(anchor,dict(platform='Deezer',source_url='https://www.deezer.com/track/123',genre='Pop'),{})
        result['access_token']='SECRET';result['metadata_sources']['genre']['refresh_token']='PRIVATE'
        cached=cached_record(result,URL)
        self.assertEqual(cached['metadata_sources']['genre']['platform'],'Deezer')
        self.assertNotIn('SECRET',json.dumps(cached));self.assertNotIn('PRIVATE',json.dumps(cached))

if __name__=='__main__':unittest.main()
