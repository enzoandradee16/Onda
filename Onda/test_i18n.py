"""Locale persistence, canonical choices and translated desktop rendering."""
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from i18n import english_catalog, set_language, tr
from preferences import PreferenceStore

class LocalizationTests(unittest.TestCase):
    def tearDown(self):set_language("pt-BR")
    def test_defaults_brand_and_dynamic_values(self):
        self.assertEqual(tr("Configurações"),"Configurações")
        set_language("en")
        self.assertEqual(tr("Configurações"),"Settings")
        self.assertEqual(tr("ONDA"),"ONDA")
        self.assertEqual(tr("Onda • Vídeo, áudio & fotos"),"ONDA • Video, audio & photos")
        self.assertEqual(tr("Minha música favorita"),"Minha música favorita")
        self.assertEqual(tr("Fila da pesquisa · 2 de 5 concluídas"),"Search queue · 2 of 5 completed")
        self.assertEqual(tr("MP3 · Concluído"),"MP3 · Completed")
        self.assertEqual(tr("Velocidade · 85% · Slowed"),"Speed · 85% · Slowed")
        self.assertEqual(tr("Cards: Pequeno ▾"),"Cards: Small ▾")
        from history_details import detail_lines
        self.assertEqual(detail_lines({"album":"Original","genre":"House"},translate=tr),"Album / single: Original · Genre: House")
        self.assertFalse(any("Wave" in value for key,value in english_catalog().items() if "ONDA" in key or "Onda" in key))
    def test_public_album_note_and_visible_count(self):
        set_language('en')
        self.assertEqual(tr('14 de 14'),'14 of 14')
        self.assertEqual(tr('Álbum Spotify público. A página pública pode omitir faixas; conecte Spotify se a lista estiver incompleta.'),'Public Spotify album. The public page may omit tracks; connect Spotify if the list is incomplete.')
        set_language('es')
        self.assertEqual(tr('Álbum Spotify público. A página pública pode omitir faixas; conecte Spotify se a lista estiver incompleta.'),'Álbum público de Spotify. La página pública puede omitir canciones; conecta Spotify si la lista está incompleta.')

    def test_secondary_messages_and_spotify_callback(self):
        set_language("en")
        self.assertEqual(tr("Spotify conectado"),"Spotify connected")
        self.assertEqual(tr("VERSÃO NO YOUTUBE"),"VERSION ON YOUTUBE")
        self.assertEqual(tr("Álbum · 14 músicas"),"Album · 14 tracks")
        self.assertEqual(tr("Discovery · 14 itens. Spotify conectado: 14 músicas; 0 itens locais/indisponíveis/episódios ignorados."),"Discovery · 14 items. Spotify connected: 14 tracks; 0 local/unavailable items/episodes skipped.")
        self.assertEqual(tr("Pesquisa · 25 segundos"),"Search · 25 seconds")
        from spotify_account import callback_page
        page=callback_page(True,True,translate=tr,language="en").decode()
        self.assertIn("lang='en'",page)
        self.assertIn("Authorization received. Return to ONDA.",page)
        self.assertIn("Returning in {seconds} seconds",page)
        self.assertNotIn("Volte para",page)
        self.assertNotIn("Voltando",page)

    def test_language_persists_independently_of_remember_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            store=PreferenceStore(Path(folder)/"settings.json")
            self.assertEqual(store.load_language(),"pt-BR")
            store.save_language("en")
            self.assertIsNone(store.load())
            self.assertEqual(store.load_language(),"en")
            self.assertEqual(PreferenceStore.clean({"language":"en"}),{"language":"en"})
            self.assertEqual(PreferenceStore.clean({"language":"invalid"}),{})
            with self.assertRaises(ValueError):store.save_language("invalid")
    def test_import_export_keeps_canonical_language(self):
        from advanced_options import export_settings,import_settings
        payload=export_settings({"language":"en","mode":"Áudio · MP3 (320 kbps)"},"windows")
        self.assertEqual(payload["settings"]["language"],"en")
        self.assertEqual(import_settings(payload,"windows")["language"],"en")

@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"),"Tk integration")
class DesktopEnglishTests(unittest.TestCase):
    def tearDown(self):set_language("pt-BR")
    def test_translated_choices_keep_values_and_support_rebinding(self):
        from i18n_tk import TranslatedCombobox,display_var
        root=tk.Tk();root.withdraw();set_language("en")
        try:
            mode=tk.StringVar(root,value="Preto puro")
            combo=TranslatedCombobox(root,textvariable=mode,values=("Escuro","Preto puro","Claro"),state="readonly")
            self.assertEqual(root.tk.call(combo._w,"get"),"Pure black")
            self.assertEqual(combo.get(),"Preto puro")
            combo.current(2);root.update()
            self.assertEqual(mode.get(),"Claro")
            quality=tk.StringVar(root,value="Original")
            combo.configure(textvariable=quality,values=("Original","Melhor disponível"))
            combo.current(1);root.update()
            self.assertEqual(quality.get(),"Melhor disponível")
            self.assertEqual(mode.get(),"Claro")
            status=tk.StringVar(root,value="Pendente");rendered=display_var(status)
            status.set("Concluído");self.assertEqual(rendered.get(),"Completed")
            self.assertEqual(status.get(),"Concluído")
        finally:root.destroy()
    def test_secondary_windows_translate_labels_and_keep_metadata(self):
        from types import SimpleNamespace
        from spotify_account_ui import SpotifyConnection
        from catalog_picker import CatalogPicker
        from metadata_ui import MetadataWindow
        from tkinter import ttk
        set_language("en")
        root=tk.Tk();root.withdraw()
        root.spotify_client_id=tk.StringVar(root,value="")
        root.spotify_client_secret=tk.StringVar(root,value="")
        root.language=tk.StringVar(root,value="en")
        root.credential_status=tk.StringVar(root,value="")
        root.save_spotify_credentials=lambda:None
        root.forget_spotify_credentials=lambda:None
        root.write_log=lambda value:None
        windows=[]
        try:
            account=SimpleNamespace(connected=True,warning="",client_id="",remember=False)
            page=SimpleNamespace(app=root,spotify_account=account,spotify_button=ttk.Button(root))
            spotify=SpotifyConnection(page);windows.append(spotify)
            from i18n_tk import display_var
            self.assertIn("Account connected.",display_var(spotify.status).get())
            record={"title":"Original","artists":["Spotify conectado"],"album":"Original","duration":240,"match_score":.5,"manual_review":True,"platform":"Deezer","source_url":"https://example.com/track"}
            picker=CatalogPicker(root,{"title":"Original","duration_ms":240000,"candidates":[record]},lambda row:None,lambda:None);windows.append(picker)
            self.assertEqual(picker.select_button.cget("text"),"Use this metadata")
            self.assertEqual(picker.table.heading("artist","text"),"ARTIST / CATALOG")
            metadata=MetadataWindow(root);windows.append(metadata)
            metadata.records=[record];metadata.table.insert("","end",iid="0");metadata.table.selection_set("0");metadata.select()
            detail=metadata.details.get("1.0","end")
            self.assertIn("Title: Original",detail)
            self.assertIn("Artists: Spotify conectado",detail)
            self.assertIn("Album: Original",detail)
            self.assertNotIn("Título:",detail)
        finally:
            for window in reversed(windows):
                if isinstance(window,SpotifyConnection):window.close()
                elif isinstance(window,MetadataWindow):window.close()
                else:window.destroy()
            root.destroy()

    def test_english_app_tabs_settings_and_song_content(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"LOCALAPPDATA":folder}):
            store=PreferenceStore();store.save_language("en")
            from app import App
            app=App(show_welcome=False)
            try:
                app.update()
                labels=[app.pages.tab(page,"text") for page in app.pages.tabs()]
                self.assertIn("Search music",labels)
                self.assertIn("History",labels)
                self.assertIn("Edit metadata",labels)
                self.assertEqual(app.mode.get(),"Vídeo · melhor qualidade (MKV)")
                self.assertIn("ONDA",app.title())
                app.catalog_page.ensure_ready()
                pane=app.catalog_page._content
                pane.track_title.set("Original")
                self.assertEqual(pane.title_label.cget("textvariable"),str(pane.track_title))
            finally:app.destroy()

if __name__=="__main__":unittest.main()
