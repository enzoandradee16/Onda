import tempfile
import unittest
from pathlib import Path
from download_feedback import download_detail, failure_advice
from library import LibraryStore

class DownloadFeedbackTests(unittest.TestCase):
    def test_unknown_metrics_are_omitted(self):
        self.assertEqual(download_detail({'type':'progress','speed':None}), 'Baixando')
        self.assertEqual(download_detail({'type':'processing'}), 'Convertendo')
        self.assertIn('1.00 MB/s',download_detail({'type':'progress','speed':1048576,'total':2097152,'downloaded':1048576}))

    def test_actions_follow_probable_cause(self):
        for message,action in [('HTTP 403','Verificar acesso'),('HTTP 404','Atualizar link'),('Connection timeout','Tentar novamente'),('Unexpected error','Tentar novamente')]:
            self.assertEqual(failure_advice(message)[1],action)

    def test_live_metrics_and_failure_advice_follow_ui_language(self):
        from i18n import tr
        detail=download_detail({'type':'progress','speed':1048576,'total':2097152,'downloaded':1048576})
        self.assertTrue(tr(detail,language='en').startswith('Downloading · '))
        self.assertTrue(tr(detail,language='es').startswith('Descargando · '))
        self.assertEqual(tr(failure_advice('HTTP 404')[1],language='en'),'Update link')

    def test_undo_preserves_new_download_and_original_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LibraryStore(Path(folder)/'library.db')
            store.add_history(Path(folder)/'old.jpg','jpg','https://example.com/post')
            original=store.history()[0]
            removed=store.remove_history(original['id'])
            store.add_history(Path(folder)/'new.jpg','jpg')
            store.restore_history(removed)
            rows=store.history()
            self.assertEqual(len(rows),2)
            restored=next(row for row in rows if row['name']=='old')
            for key in ('path','date','mode','source'):self.assertEqual(restored[key],original[key])
