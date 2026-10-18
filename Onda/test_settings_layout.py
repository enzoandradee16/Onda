import os,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from settings_layout import CATEGORIES
from reset_settings import GROUPS
class SettingsLayoutTests(unittest.TestCase):
    def test_shared_categories_and_resets_match(self):
        expected=('Geral','Aparência','Downloads','Imagens','Áudio','Contas','Ferramentas')
        self.assertEqual(CATEGORIES,expected)
        self.assertEqual(tuple(GROUPS),(*expected,"Desempenho"))
        self.assertIn('check_updates',GROUPS['Ferramentas'])
        self.assertNotIn('check_updates',GROUPS['Geral'])
        self.assertIn('tab_order',GROUPS['Aparência'])
@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class SettingsLayoutUiTests(unittest.TestCase):
    def test_each_common_option_exists_in_its_category_on_both_platforms(self):
        from app import App
        from settings_layout import LAYOUT
        from tkinter import ttk
        from engine import MODES
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.withdraw()
            try:
                labels={}
                def walk(parent):
                    for widget in parent.winfo_children():
                        if isinstance(widget,(ttk.Label,ttk.Button,ttk.Checkbutton)):yield str(widget.cget('text'))
                        yield from walk(widget)
                for tab in app.settings_pages.tabs():labels[app.settings_pages.tab(tab,'text')]=set(walk(app.settings_categories[tab].content))
                android=json.loads((Path(__file__).parent.parent/'Celular/app/src/main/assets/settings_search.json').read_text(encoding='utf-8'))
                for category,options in LAYOUT['common_options'].items():
                    for label in options:
                        self.assertIn(label,labels[category],(category,label))
                        self.assertTrue(any(entry['category']==category and entry['label']==label for entry in android),(category,label))
                app.confirm_version.set(True)
                self.assertTrue(app.preference_store.clean({'confirm_version':True})['confirm_version'])
                app.queue_actions_at_top.set(False);self.assertEqual(int(app.queue_actions_frame.grid_info()['row']),6)
                app.queue_actions_at_top.set(True);self.assertEqual(int(app.queue_actions_frame.grid_info()['row']),2)
                app.mode.set(next(key for key,value in MODES.items() if value=='mp4'))
                self.assertIn('Resolução máxima',set(walk(app.settings_categories[app.settings_pages.tabs()[2]].content)))
                app.youtube_cookies.set('youtube.txt');app.social_cookies.set('social.txt')
                self.assertEqual(app.download_cookies('https://open.spotify.com/track/abc'),'youtube.txt')
                self.assertEqual(app.download_cookies('https://instagram.com/p/abc'),'social.txt')
            finally:app.destroy()

    def test_controls_are_centralized_and_saved_values_survive(self):
        from app import App
        from preferences import PreferenceStore
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            PreferenceStore().save({'check_updates':False,'concurrent_downloads':'3','theme_mode':'Escuro','mp3_quality':'128 kbps'})
            app=App(show_welcome=False);app.withdraw()
            try:
                tabs=app.settings_pages.tabs()
                self.assertEqual(tuple(app.settings_pages.tab(tab,'text') for tab in tabs),(*CATEGORIES,'Desempenho'))
                self.assertEqual(app.concurrent_downloads.get(),'3')
                self.assertEqual(app.mp3_quality.get(),'128 kbps')
                self.assertFalse(app.check_updates.get())
                for query,category in [('Agendar downloads','Downloads'),('Verificar atualizações do ONDA ao abrir','Ferramentas'),('Manter proporção','Imagens'),('Tamanho dos cards da fila','Aparência')]:
                    app.settings_search.query.set(query);app.settings_search.search()
                    self.assertTrue(app.settings_search.results,query)
                    self.assertEqual(app.settings_search.results[0][3],category)
            finally:app.destroy()
