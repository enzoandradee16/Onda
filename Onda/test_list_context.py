import os,tempfile,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"),"Tk integration")
class ListContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"LOCALAPPDATA":self.temp.name});self.env.start()
        from app import App
        self.app=App(show_welcome=False);self.app.withdraw();self.app.folder.set(self.temp.name)
    def tearDown(self):
        self.app.destroy();self.env.stop();self.temp.cleanup()
        from i18n import set_language
        set_language("pt-BR")
    def menu(self,table):
        context=table._list_context
        with patch.object(tk.Menu,"tk_popup"):
            context.popup(20,20)
        self.assertTrue(context.menu.winfo_exists())
        return context.menu
    def entry(self,menu,label):
        for i in range(menu.index("end")+1):
            if menu.type(i)!="separator" and menu.entrycget(i,"label")==label:return i
        self.fail("Missing menu entry: "+label)
    def invoke(self,menu,label):menu.invoke(self.entry(menu,label))
    def test_queue_selection_copy_remove_and_reorder(self):
        app=self.app
        keys=app.add(lines=["https://example.com/a","https://example.com/b","https://example.com/c"])
        app.tree.selection_set(keys[:2]);app.refresh_queue()
        app.tree._list_context.select(keys[1]);self.assertEqual(app.tree.selection(),tuple(keys[:2]))
        menu=self.menu(app.tree)
        self.invoke(menu,"Copiar link");self.assertEqual(app.clipboard_get(),"https://example.com/a\nhttps://example.com/b")
        self.invoke(menu,"Mover para baixo");self.assertEqual(app.tree.get_children(),(keys[2],keys[0],keys[1]))
        app.tree._list_context.select(keys[2]);self.assertEqual(app.tree.selection(),(keys[2],))
        menu=self.menu(app.tree);self.invoke(menu,"Remover selecionados")
        self.assertNotIn(keys[2],app.jobs)
    def test_queue_failure_running_and_empty_states(self):
        app=self.app;key=app.add(lines=["https://example.com/a"])[0]
        app.tree._list_context.select(key);app.set_state(key,"Falhou");app.refresh_queue()
        menu=self.menu(app.tree);self.invoke(menu,"Tentar novamente")
        self.assertEqual(app.jobs[key]["state"],"Na fila")
        app.set_state(key,"Em andamento");menu=self.menu(app.tree)
        self.assertEqual(menu.entrycget(self.entry(menu,"Mover para cima"),"state"),"disabled")
        self.assertEqual(menu.entrycget(self.entry(menu,"Baixar selecionados"),"state"),"disabled")
        app.tree.selection_remove(app.tree.selection());app.refresh_queue();menu=self.menu(app.tree)
        self.assertEqual(menu.entrycget(self.entry(menu,"Remover selecionados"),"state"),"disabled")
    def test_cards_and_keyboard_share_context(self):
        app=self.app;keys=app.add(lines=["https://example.com/a","https://example.com/b"])
        app.queue_view.set("Completa");app.update()
        card=app.queue_cards.rows[keys[1]][0]
        self.assertTrue(card.bind("<Button-3>"))
        self.assertTrue(card.winfo_children()[0].bind("<Shift-F10>"))
        app.tree.selection_set(keys[0]);app.tree.focus(keys[0])
        with patch.object(app.tree._list_context,"popup",return_value="break") as popup:
            self.assertEqual(app.tree._list_context.keyboard(None),"break");popup.assert_called_once()
        menu=self.menu(app.tree);self.invoke(menu,"Compacto")
        self.assertEqual(app.queue_view.get(),"Compacto")
        menu=self.menu(app.tree);self.assertEqual(menu.entrycget(self.entry(menu,"Cards: Pequeno"),"state"),"disabled")
    def test_history_actions_keep_files_and_cards_bound(self):
        app=self.app;file=Path(self.temp.name)/"song.mp3";file.write_bytes(b"fixture")
        app.library.add_history(file,"mp3");page=app.history_page.ensure_ready();page.refresh()
        key=page.table.get_children()[0];page.table._list_context.select(key)
        with patch.object(page,"open") as opened:
            self.invoke(self.menu(page.table),"Abrir arquivo");opened.assert_called_once()
        self.invoke(self.menu(page.table),"Copiar caminho");self.assertEqual(Path(app.clipboard_get()).resolve(),file.resolve())
        self.invoke(self.menu(page.table),"Completa")
        self.assertTrue(page._cards[key][0].master.bind("<Button-3>"))
        self.assertTrue(file.exists())
    def test_catalog_playlist_and_metadata_menus_follow_controls(self):
        app=self.app
        for page in (app.catalog_page,app.playlist_page):
            menu=self.menu(page.table)
            self.assertEqual(menu.entrycget(self.entry(menu,"Copiar"),"state"),"disabled")
        from metadata_ui import MetadataWindow
        page=MetadataWindow(app)
        try:
            menu=self.menu(page.table)
            self.assertEqual(menu.entrycget(self.entry(menu,"Abrir capa"),"state"),"disabled")
        finally:page.close()
    def test_labels_translate_in_both_languages(self):
        from i18n import set_language
        for language,copy,download in (("en","Copy","Download selected"),("es","Copiar","Descargar seleccionados")):
            set_language(language);menu=self.menu(self.app.tree)
            self.entry(menu,copy);self.entry(menu,download)

    def test_version_and_catalog_match_menus_reuse_their_actions(self):
        from version_picker import VersionPicker
        from catalog_picker import CatalogPicker
        selected=[]
        event={"title":"Song","candidates":[{"id":"video-id","title":"Song","match_score":0.99,"source_url":"https://example.com/song","artists":["Artist"],"platform":"Deezer"}]}
        for cls,label in ((VersionPicker,"Baixar esta versão"),(CatalogPicker,"Usar estes metadados")):
            window=cls(self.app,event,selected.append,lambda:None)
            try:
                window.table._list_context.select("0")
                menu=self.menu(window.table)
                self.invoke(menu,label)
                self.assertEqual(selected[-1],"video-id")
                if cls is CatalogPicker:
                    labels=[menu.entrycget(i,"label") for i in range(menu.index("end")+1) if menu.type(i)!="separator"]
                    self.assertNotIn("Ouvir / parar prévia",labels)
            finally:window.destroy()
    def test_readonly_playlist_keeps_source_identity_after_refresh(self):
        from playlist_list_ui import PlaylistListWindow
        page=self.app.playlist_page
        page.records={"track-key":{"title":"Song","artists":["Artist"],"source_url":"https://example.com/song"}}
        page.playlist_title="Album"
        window=PlaylistListWindow(page)
        try:
            window.table._list_context.select("track-key")
            with patch("webbrowser.open") as opened:
                self.invoke(self.menu(window.table),"Abrir na plataforma")
                opened.assert_called_once_with("https://example.com/song")
            window.refresh(page)
            self.assertEqual(window.table.get_children(),("track-key",))
        finally:window.destroy()

    def test_right_click_targets_the_row_and_blank_area_clears_selection(self):
        app=self.app;keys=app.add(lines=["https://example.com/a","https://example.com/b"])
        context=app.tree._list_context
        event=SimpleNamespace(x=10,y=40,x_root=100,y_root=200)
        app.tree.selection_set(keys[0])
        with patch.object(app.tree,"identify_region",return_value="cell"),patch.object(app.tree,"identify_row",return_value=keys[1]),patch.object(context,"popup",return_value="break") as popup:
            self.assertEqual(context.mouse(event),"break")
            popup.assert_called_once_with(100,200)
            self.assertEqual(app.tree.selection(),(keys[1],))
        with patch.object(app.tree,"identify_region",return_value="nothing"),patch.object(app.tree,"identify_row",return_value=""),patch.object(context,"popup",return_value="break"):
            context.mouse(event)
            self.assertEqual(app.tree.selection(),())
        with patch.object(app.tree,"identify_region",return_value="heading"),patch.object(context,"popup") as popup:
            context.mouse(event);popup.assert_not_called()
