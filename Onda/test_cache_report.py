import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cache_report import report,remove
from cache_cleanup import clear_cache


class CacheReportTests(unittest.TestCase):
    def test_each_report_and_cleanup_scans_playback_entries_once(self):
        from playback_cache_budget import _entries
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.group(root,1,True)
            with patch('playback_cache_budget._entries', wraps=_entries) as scan:
                report(root)
                self.assertEqual(scan.call_count,1)
            with patch('playback_cache_budget._entries', wraps=_entries) as scan:
                clear_cache(root)
                self.assertEqual(scan.call_count,1)

    def group(self,root,index,played=False):
        path=root/'jukebox'/f'{index:064x}';path.mkdir(parents=True)
        (path/'audio.wav').write_bytes(b'a'*100)
        (path/'effects-85-0-False.wav').write_bytes(b'b'*60)
        (path/'analysis.json').write_text(json.dumps({'title':'Música '+str(index)}))
        if played:(path/'.played').touch()
        for item in path.iterdir():os.utime(item,(index,index))
        os.utime(path,(index,index));return path

    def test_totals_count_protected_audio_and_split_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=self.group(root,1)
            info=report(root,[str(path/'audio.wav')])
            self.assertEqual(info['bytes'],sum(p.stat().st_size for p in path.iterdir()))
            self.assertEqual(info['protected_bytes'],info['bytes'])
            self.assertEqual(next(row['bytes'] for row in info['categories'] if row['name']=='Efeitos'),60)
            self.assertTrue(info['tracks'][0]['protected'])

    def test_clear_preserves_current_and_recent_tracks_and_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=self.group(root,1);recent=self.group(root,2,True);current=self.group(root,3)
            download=root/'my-download.mp3';download.write_bytes(b'original')
            clear_cache(root,protected=[current])
            self.assertFalse((old/'audio.wav').exists())
            self.assertTrue((recent/'audio.wav').exists());self.assertTrue((current/'audio.wav').exists())
            self.assertEqual(download.read_bytes(),b'original')

    def test_targeted_removal_rejects_protected_and_outside_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=self.group(root,1,True)
            with self.assertRaises(ValueError):remove(root,path.name)
            with self.assertRaises(ValueError):remove(root,'../../my-download.mp3')
            self.assertTrue((path/'audio.wav').exists())

    def test_empty_and_metadata_only_directories_are_not_listed_as_tracks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=self.group(root,1)
            (root/'jukebox'/('a'*64)).mkdir()
            metadata=root/'jukebox'/('b'*64);metadata.mkdir();(metadata/'analysis.json').write_text('{}')
            info=report(root)
            self.assertEqual([row['id'] for row in info['tracks']],[path.name])

    def test_saved_session_recovers_names_of_legacy_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=self.group(root,1);(path/'analysis.json').write_text('{}')
            (root/'playback-session.json').write_text(json.dumps({'jukebox':{'model':{'cache':str(path),'media_title':'Nome recuperado'}}}))
            self.assertEqual(report(root)['tracks'][0]['name'],'Nome recuperado')


if __name__=='__main__':unittest.main()
