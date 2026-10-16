from pathlib import Path
import hashlib,json,tempfile,unittest
from unittest.mock import patch
from file_output import cleanup_completed_work

class WorkCleanupTests(unittest.TestCase):
    def stage(self,root,name='a'*20):
        staging=root/'.onda-work'/name;staging.mkdir(parents=True)
        (staging/'nested').mkdir();(staging/'nested'/'thumbnail.webp').write_bytes(b'temporary')
        return staging
    def test_last_success_removes_nonempty_staging_and_root_but_keeps_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);staging=self.stage(root)
            output=root/'song.mp3';output.write_bytes(b'completed')
            self.assertTrue(cleanup_completed_work(staging,root))
            self.assertFalse((root/'.onda-work').exists());self.assertEqual(output.read_bytes(),b'completed')
    def test_other_worker_or_interrupted_partial_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);first=self.stage(root);second=self.stage(root,'b'*20)
            partial=second/'song.part';partial.write_bytes(b'resumable')
            self.assertTrue(cleanup_completed_work(first,root))
            self.assertTrue((root/'.onda-work').exists());self.assertEqual(partial.read_bytes(),b'resumable')
            self.assertTrue(cleanup_completed_work(second,root));self.assertFalse((root/'.onda-work').exists())
    def test_catalog_and_playlist_subfolders_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);staging=self.stage(root/'Artist'/'Album')
            self.assertTrue(cleanup_completed_work(staging,root));self.assertFalse(staging.parent.exists())
    def test_paths_outside_selected_root_and_unowned_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outside=self.stage(root/'outside');allowed=root/'allowed';allowed.mkdir()
            self.assertFalse(cleanup_completed_work(outside,allowed));self.assertTrue(outside.exists())
            wrong=self.stage(allowed,'user-folder')
            self.assertFalse(cleanup_completed_work(wrong,allowed));self.assertTrue(wrong.exists())
            self.assertFalse(cleanup_completed_work(allowed,allowed));self.assertTrue(allowed.exists())
    def test_reparse_points_are_not_followed(self):
        import stat
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);staging=self.stage(root)
            with patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0x400)):
                self.assertFalse(cleanup_completed_work(staging,root))
            self.assertTrue(staging.exists())
    def test_locked_temporary_files_do_not_turn_success_into_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);staging=self.stage(root)
            with patch('file_output.shutil.rmtree',side_effect=PermissionError('locked')):
                self.assertFalse(cleanup_completed_work(staging,root))
            self.assertTrue(staging.exists())
    def test_social_cleanup_waits_for_entire_post_and_does_not_run_for_android(self):
        from social_media import download_post
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config={'folder':str(root),'url':'https://instagram.com/p/fixture','mode':'photos','_cleanup_work':True}
            identity=hashlib.sha256(json.dumps({key:config.get(key) for key in ('url','mode','audio_quality','height','fps','work_id','_identity')},sort_keys=True).encode()).hexdigest()[:20]
            staging=self.stage(root,identity)
            with patch('social_media._download_post',side_effect=ValueError('interrupted')):
                with self.assertRaises(ValueError):download_post(config,lambda *a,**k:None,None)
            self.assertTrue(staging.exists())
            with patch('social_media._download_post',return_value=True):
                self.assertTrue(download_post(dict(config,_cleanup_work=False),lambda *a,**k:None,None))
            self.assertTrue(staging.exists())
            with patch('social_media._download_post',return_value=True):
                self.assertTrue(download_post(config,lambda *a,**k:None,None))
            self.assertFalse(staging.parent.exists())

if __name__=='__main__':unittest.main()
