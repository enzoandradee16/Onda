"""Spanish catalog parity, persistence, canonical options and secondary windows."""
import collections
import os
from pathlib import Path
import re
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from i18n import LANGUAGES,catalog,set_language,tr
from preferences import PreferenceStore

class SpanishTests(unittest.TestCase):
    def tearDown(self):set_language('pt-BR')
    def test_complete_catalog_and_placeholders(self):
        self.assertEqual(LANGUAGES,('pt-BR','es','en'))
        english,spanish=catalog('en'),catalog('es')
        self.assertEqual(english.keys(),spanish.keys())
        placeholders=r'\{[a-zA-Z_][a-zA-Z_0-9]*\}'
        for source,translated in spanish.items():
            self.assertTrue(translated,source)
            self.assertEqual(collections.Counter(re.findall(placeholders,source)),collections.Counter(re.findall(placeholders,translated)),source)
            self.assertEqual(tr(source,'es'),translated)
            if re.search(r'\bONDA\b|\bOnda\b',source):self.assertIn('ONDA',translated)
    def test_language_caches_dynamic_messages_and_callback(self):
        self.assertEqual(tr('Configurações','en'),'Settings')
        self.assertEqual(tr('Configurações','es'),'Configuración')
        self.assertEqual(tr('Configurações','en'),'Settings')
        set_language('es')
        self.assertEqual(tr('Fila da pesquisa · 2 de 5 concluídas'),'Cola de búsqueda · 2 de 5 completadas')
        self.assertEqual(tr('MP3 · Concluído'),'MP3 · Completado')
        self.assertEqual(tr('Álbum · 14 músicas'),'Álbum · 14 canciones')
        self.assertEqual(tr('Cards: Pequeno ▾'),'Tarjetas: Pequeño ▾')
        self.assertEqual(tr('Não foi possível exportar: Não foi possível ler este arquivo.'),'No se pudo exportar: No se pudo leer este archivo.')
        from spotify_account import callback_page
        page=callback_page(True,True,translate=tr,language='es').decode()
        self.assertIn("lang='es'",page)
        self.assertIn('Autorización recibida. Vuelve a ONDA.',page)
        self.assertNotIn('Voltando',page)
    def test_persistence_import_and_default(self):
        from advanced_options import export_settings,import_settings
        with tempfile.TemporaryDirectory() as folder:
            store=PreferenceStore(Path(folder)/'settings.json')
            self.assertEqual(store.load_language(),'pt-BR')
            store.save_language('es')
            self.assertEqual(store.load_language(),'es')
            self.assertIsNone(store.load())
            self.assertEqual(PreferenceStore.clean({'language':'es'}),{'confirm_version':False,'language':'es'})
        payload=export_settings({'language':'es'},'windows')
        self.assertEqual(import_settings(payload,'windows')['language'],'es')

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class SpanishWindowTests(unittest.TestCase):
    def tearDown(self):set_language('pt-BR')
    def test_app_pages_settings_and_secondary_windows(self):
        from app import App
        from catalog_picker import CatalogPicker
        from spotify_account_ui import SpotifyConnection
        from metadata_ui import MetadataWindow
        from i18n_tk import TranslatedCombobox,display_var
        from tkinter import ttk
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            PreferenceStore().save_language('es')
            app=App(show_welcome=False);windows=[]
            try:
                app.update()
                tabs=[app.pages.tab(page,'text') for page in app.pages.tabs()]
                self.assertIn('Buscar música',tabs);self.assertIn('Historial',tabs)
                self.assertIn('Editar metadatos',tabs)
                self.assertEqual(app.mode.get(),'Vídeo · melhor qualidade (MKV)')
                def descendants(widget):
                    for child in widget.winfo_children():yield child;yield from descendants(child)
                selectors=[w for w in descendants(app.settings_window) if isinstance(w,TranslatedCombobox) and w._canonical is app.language]
                self.assertEqual(len(selectors),1)
                self.assertEqual(selectors[0].cget('values'),('Português (Brasil)','Español','English'))
                for name in ('catalog_page','playlist_page','images_page','effects_page','metadata_page'):
                    page=getattr(app,name);page.ensure_ready()
                account=SimpleNamespace(connected=True,warning='',client_id='',remember=False)
                page=SimpleNamespace(app=app,spotify_account=account,spotify_button=ttk.Button(app))
                spotify=SpotifyConnection(page);windows.append(spotify)
                self.assertIn('Cuenta conectada.',display_var(spotify.status).get())
                record={'title':'Configurações','artists':['Original'],'album':'Original','duration':240,'match_score':.5,'manual_review':True,'platform':'Deezer','explicit':True,'source_url':'https://example.com/track'}
                picker=CatalogPicker(app,{'title':record['title'],'candidates':[record]},lambda row:None,lambda:None);windows.append(picker)
                self.assertEqual(picker.select_button.cget('text'),'Usar estos metadatos')
                self.assertEqual(picker.table.heading('artist','text'),'ARTISTA / CATÁLOGO')
                self.assertEqual(picker.table.item('0','values')[0],'Configurações')
                metadata=MetadataWindow(app);windows.append(metadata)
                metadata.records=[record];metadata.table.insert('','end',iid='0');metadata.table.selection_set('0');metadata.select()
                self.assertIn('Título: Configurações',metadata.details.get('1.0','end'))
                self.assertIn('Explícita: Sí',metadata.details.get('1.0','end'))
            finally:
                for window in reversed(windows):
                    if isinstance(window,(SpotifyConnection,MetadataWindow)):window.close()
                    else:window.destroy()
                app.destroy()

if __name__=='__main__':unittest.main()
