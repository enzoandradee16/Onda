"""Regression coverage for request counts, preserved evidence and actual worker overlap."""
import threading
import unittest
from unittest.mock import Mock, MagicMock, patch
from matching import find_youtube, revalidate_match, resolve_youtube, AmbiguousMatch, NoCompatibleMatch
from metadata import MetadataClient
from test_spotify_priority import api_track, ID, URL
from metadata import spotify_record
from test_artist_alias_lookup import RECORD, VIDEO, ID as MBID
from test_dynamic_downloads import App
from parallel_queue import ParallelQueue

class DownloadPerformanceTests(unittest.TestCase):
    def test_complete_spotify_record_needs_no_optional_catalog_requests(self):
        client=MetadataClient();self.addCleanup(client.close)
        client.search=Mock(side_effect=AssertionError("Unnecessary search"));client.get_json=Mock(side_effect=AssertionError("Unnecessary ISRC fetch"))
        anchor=spotify_record(api_track(),ID,URL)
        self.assertIsNone(anchor['genre'])
        self.assertEqual(client.complete_spotify(anchor,automatic=True)['title'],anchor['title'])
        client.search.assert_not_called();client.get_json.assert_not_called()
    def test_existing_youtube_results_are_reused_for_verified_catalog_alias(self):
        anchor=dict(title='Localized title',artists=['Artist'],duration_ms=200000,album='Album')
        video=dict(id='abcdefghijk',title='Artist Original title',duration=200)
        downloader=MagicMock();extract=downloader.__enter__.return_value.extract_info
        extract.return_value=dict(entries=[video])
        alias=dict(title='Original title',artists=['Artist'],album='Album',source_url='https://www.deezer.com/track/1',identity_evidence='isrc')
        with patch('yt_dlp.YoutubeDL',return_value=downloader),patch('artist_alias_lookup.discover_aliases',return_value=[]),patch('catalog_aliases.alternate_records',return_value=[alias]):
            result=find_youtube(anchor,Mock(),prefer_best=True)
        self.assertEqual(result['id'],video['id']);self.assertEqual(extract.call_count,2)
    def test_verified_artist_alias_survives_fresh_extractor_revalidation(self):
        groups=[dict(artist_id=MBID,aliases=['Original Artist Name','Stage Name'],source_url='https://musicbrainz.org/artist/'+MBID)]
        downloader=MagicMock();downloader.__enter__.return_value.extract_info.return_value=dict(entries=[VIDEO])
        with patch('yt_dlp.YoutubeDL',return_value=downloader),patch('artist_alias_lookup.discover_aliases',return_value=groups):
            chosen=find_youtube(RECORD,Mock(),prefer_best=True)
        self.assertEqual(revalidate_match(RECORD,chosen,VIDEO),VIDEO)
        with self.assertRaises(NoCompatibleMatch):revalidate_match(RECORD,chosen,dict(VIDEO,duration=400))
    def test_automatic_never_opens_picker_for_unapproved_candidates(self):
        chooser=Mock()
        with patch('matching.find_youtube',side_effect=AmbiguousMatch([dict(VIDEO,manual_review=True)])):
            with self.assertRaises(NoCompatibleMatch):resolve_youtube(RECORD,Mock(),chooser,automatic=True)
        chooser.assert_not_called()
    def test_five_workers_really_overlap_with_live_preferences(self):
        app=App(5);app.auto_match.set(True);app.auto_metadata.set(True)
        app.jobs={str(i):dict(state='Na fila') for i in range(8)}
        gate=threading.Event();ready=threading.Event();lock=threading.Lock();observed=[]
        def work(item,config):
            with lock:
                observed.append(config)
                if len(observed)==5:ready.set()
            gate.wait(5)
        app.supervise=work
        scheduler=ParallelQueue(app)
        try:
            scheduler.start(None)
            self.assertTrue(ready.wait(3),'Five workers should start without waiting for previous downloads')
            self.assertEqual(len(scheduler.workers),5)
            self.assertEqual(sum(row['state']=='Na fila' for row in app.jobs.values()),3)
            self.assertTrue(all(row['auto_match'] and row['auto_metadata'] for row in observed))
        finally:gate.set()

if __name__=='__main__':unittest.main()
