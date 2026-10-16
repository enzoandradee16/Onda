from copy import deepcopy
from unittest.mock import Mock,patch
import unittest
from failure_report import failed_rows,report_text,replace_metadata
from test_dynamic_downloads import App
from parallel_queue import ParallelQueue

class FailureReportTests(unittest.TestCase):
    def test_report_only_contains_attempted_failures_and_no_config_secrets(self):
        jobs={"old":dict(state="Falhou",url="old"),"ok":dict(state="Concluído",url="ok"),"cancel":dict(state="Cancelado",url="cancel"),"bad":dict(state="Falhou",url="track",display_name="Artist - Song",last_error="Network error",spotify_client_secret="SECRET",cookies_file="PRIVATE")}
        rows=failed_rows(jobs,{"bad","ok","cancel"})
        self.assertEqual(len(rows),1)
        text=report_text(rows)
        for value in ("Artist - Song","track","Network error"):self.assertIn(value,text)
        for value in ("SECRET","PRIVATE","cancel","old"):self.assertNotIn(value,text)
    def test_metadata_repair_keeps_format_folder_group_and_original_link(self):
        job=dict(state="Falhou",url="https://open.spotify.com/track/original",mode="flac",folder="output",playlist=False,playlist_title="My playlist",audio_quality="lossless",catalog_record={"stale":True},selected_catalog_url="old",last_error="failure")
        record=dict(source_url="https://www.deezer.com/track/123",title="Song",artists=["Artist"],album="Album")
        original=deepcopy(record)
        self.assertTrue(replace_metadata(job,record))
        self.assertEqual(job['state'],'Na fila');self.assertEqual(job['url'],record['source_url'])
        self.assertEqual(job['failure_original_url'],'https://open.spotify.com/track/original')
        self.assertEqual((job['folder'],job['mode'],job['playlist_title'],job['audio_quality']),('output','flac','My playlist','lossless'))
        self.assertNotIn('catalog_record',job);self.assertNotIn('selected_catalog_url',job);self.assertEqual(record,original)
        self.assertTrue(replace_metadata(job,dict(record,source_url="https://www.deezer.com/track/456")))
        self.assertEqual(job['failure_original_url'],'https://open.spotify.com/track/original')
    def test_metadata_repair_rejects_non_audio_and_whole_playlists(self):
        record=dict(source_url="https://www.deezer.com/track/123")
        for job in (dict(mode="social"),dict(mode="mp3",playlist=True)):
            before=deepcopy(job);self.assertFalse(replace_metadata(job,record));self.assertEqual(job,before)
        with self.assertRaises(ValueError):replace_metadata(dict(mode="mp3"),dict(source_url="https://example.com/secret"))
    def test_summary_once_after_last_worker_only_for_current_run(self):
        app=App(2);app.show_failures=Mock();scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(('first','second'))
            scheduler.finish('first',{'success':False,'cancelled':False});app.show_failures.assert_not_called()
            scheduler.finish('second',{'success':True,'cancelled':False})
        app.show_failures.assert_called_once_with({'first','second'})
        scheduler.fill();app.show_failures.assert_called_once()
    def test_failure_reason_and_original_url_survive_restart(self):
        import tempfile
        from pathlib import Path
        from library import LibraryStore
        with tempfile.TemporaryDirectory() as folder:
            store=LibraryStore(Path(folder)/'library.sqlite3')
            job=dict(url='https://www.deezer.com/track/123',failure_original_url='https://open.spotify.com/track/original',mode='mp3',folder=folder,state='Falhou',last_error='No compatible recording')
            store.save_queue([job]);restored=LibraryStore(store.path).load_queue()[0]
            self.assertEqual(restored['last_error'],job['last_error'])
            self.assertEqual(restored['failure_original_url'],job['failure_original_url'])
    def test_stopping_does_not_open_summary(self):
        app=App(1);app.show_failures=Mock();scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(('first',));app.cancelled.is_set=lambda:True
            scheduler.finish('first',{'success':False,'cancelled':True})
        app.show_failures.assert_not_called()

if __name__=='__main__':unittest.main()
