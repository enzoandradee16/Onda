import os,tempfile,unittest
from unittest.mock import patch
from settings_search import normalize
class SearchNormalizeTests(unittest.TestCase):
    def test_accents_and_case(self):self.assertEqual(normalize('ÁUDIO Conexão'),'audio conexao')
@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class SettingsSearchTests(unittest.TestCase):
    def test_finds_actual_option_and_opens_its_category(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.withdraw()
            try:
                search=app.settings_search
                search.query.set('limpar cache');search.search()
                self.assertTrue(search.results)
                tab,widget,text,category=search.results[0]
                search.open();app.update()
                self.assertEqual(app.settings_pages.select(),tab)
                self.assertEqual(text,'Limpar cache')
                search.query.set('configuracao impossivelxyz');search.search()
                self.assertFalse(search.results)
                self.assertEqual(str(search.status.cget('text')),'Nenhuma configuração encontrada.')
                search.query.set('');search.search()
                self.assertFalse(search.list.winfo_manager())
            finally:app.destroy()
