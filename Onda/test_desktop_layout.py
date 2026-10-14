"""Small-window navigation and real inline audio editing."""
import os, tempfile, time, tkinter as tk, unittest, wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class DesktopLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name});self.env.start()
        from app import App
        self.app=App(show_welcome=False);self.app.geometry('840x720');self.app.update()
        self.source=Path(self.temp.name)/'sample.wav'
        with wave.open(str(self.source),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000);f.writeframes(b'\0\0'*8000)
    def tearDown(self):
        self.app.destroy();self.env.stop();self.temp.cleanup()
    def wait_save(self,editor):
        deadline=time.monotonic()+10
        while editor.busy and time.monotonic()<deadline:self.app.update();time.sleep(.02)
        self.assertFalse(editor.busy);self.assertTrue(editor.status.get().startswith('Salvo:'),editor.status.get())
    def test_album_scroll_with_cover_and_large_font(self):
        app=self.app;app.pages.select(app.playlist_page);app.update();pane=app.playlist_page.ensure_ready()
        pane.display({'title':'Album','kind':'album','note':'','tracks':[{'title':f'Track {i}','artists':['Artist'],'duration_ms':180000,'source_url':f'https://example.com/{i}'} for i in range(20)]})
        pane.test_cover=tk.PhotoImage(master=app,width=124,height=124);pane.collection_cover.configure(image=pane.test_cover,width=0)
        app.interface_font_size.set('130%');app.update();canvas=app.playlist_page._scroller.canvas
        self.assertGreater(pane.table.winfo_height(),100);self.assertLess(canvas.yview()[1],1)
        from settings_scroll import scroll_page
        scroll_page(SimpleNamespace(widget=pane.collection_name,delta=-120));app.update();self.assertGreater(canvas.yview()[0],0)
        before=canvas.yview();scroll_page(SimpleNamespace(widget=pane.table,delta=-120));self.assertEqual(canvas.yview(),before)
        canvas.yview_moveto(1);app.update()
        self.assertLess(pane.table.winfo_rooty(),canvas.winfo_rooty()+canvas.winfo_height())
        self.assertGreater(pane.table.winfo_rooty()+pane.table.winfo_height(),canvas.winfo_rooty())
    def test_album_appearing_after_layout_and_window_resize(self):
        app = self.app
        app.pages.select(app.playlist_page)
        app.update()
        pane = app.playlist_page.ensure_ready()
        canvas = app.playlist_page._scroller.canvas
        pane.display({'title': 'Album', 'kind': 'album', 'note': '', 'tracks': [
            {'title': 'Track', 'artists': ['Artist'], 'duration_ms': 180000,
             'source_url': 'https://example.com/track'}]})
        pane.test_cover = tk.PhotoImage(master=app, width=124, height=124)
        pane.collection_cover.configure(image=pane.test_cover, width=0)
        app.update()
        for geometry in ('980x780', '840x720', '1200x900', '840x720'):
            app.geometry(geometry)
            app.update()
            self.assertGreaterEqual(pane.table.winfo_height(), 220)
            self.assertLess(canvas.yview()[1] - canvas.yview()[0], 1)
            canvas.yview_moveto(1)
            app.update()
            footer = pane.grid_slaves(row=9)[0]
            self.assertLessEqual(footer.winfo_rooty() + footer.winfo_height(),
                                 canvas.winfo_rooty() + canvas.winfo_height())
    def test_album_cover_uses_load_generation_not_render_generation(self):
        import threading
        from catalog_ui import cover_png
        app = self.app
        app.pages.select(app.playlist_page)
        app.update()
        pane = app.playlist_page.ensure_ready()
        pane.generation = 7
        pane._render_generation = 2
        image = tk.PhotoImage(master=app, width=124, height=124)
        image.write(str(self.source.with_suffix('.png')), format='png')
        png = self.source.with_suffix('.png').read_bytes()
        started, release = threading.Event(), threading.Event()
        def delayed_cover(url):
            started.set()
            release.wait(3)
            return png
        with patch('catalog_ui.cover_png', side_effect=delayed_cover):
            pane.display({'title': 'Album', 'kind': 'album', 'note': '',
                          'cover_url': 'https://example.com/cover.png', 'tracks': [
                              {'title': 'Track', 'artists': ['Artist'], 'duration_ms': 1}]})
            self.assertTrue(started.wait(2))
            release.set()
            deadline = time.monotonic() + 3
            while pane.cover_image is None and time.monotonic() < deadline:
                app.update()
                time.sleep(.02)
        self.assertIsNotNone(pane.cover_image)
        self.assertEqual(pane.cover_image.width(), 124)
        self.assertIn(str(pane.cover_image), str(pane.collection_cover.cget('image')))
    def test_complete_history_reads_tags_cover_and_switches_back(self):
        from audio_library import write_audio
        from PIL import Image
        from preferences import PreferenceStore
        cover=self.source.with_suffix('.png');Image.new('RGB',(400,400),'blue').save(cover)
        write_audio(self.source,{'title':'Song title','artists':['Artist'],'album':'Album title','release_date':'2026','genre':'House'},str(cover))
        app=self.app;app.library.add_history(self.source,'WAV');app.pages.select(app.history_page);app.update()
        pane=app.history_page.ensure_ready()
        app.history_view.set('Completa');app.update()
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            app.update();time.sleep(.02)
            if pane._cards and next(iter(pane._cards.values()))[1].cget('text')=='Song title':break
        widgets=next(iter(pane._cards.values()))
        self.assertEqual(widgets[1].cget('text'),'Song title')
        self.assertEqual(widgets[2].cget('text'),'Artist')
        self.assertIn('Album title',widgets[3].cget('text'))
        self.assertTrue(widgets[0].cget('image'))
        large_height=widgets[0].master.winfo_height()
        app.history_card_size.set('Pequeno');app.update()
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            app.update();time.sleep(.02)
            widgets=next(iter(pane._cards.values()))
            if getattr(widgets[0],'_history_image',None):break
        self.assertEqual(widgets[0]._history_image.width(),80)
        self.assertLess(widgets[0].master.winfo_height(),large_height)
        self.assertEqual(app.notice_duration.get(),'Após 3 segundos')
        key=next(iter(pane.rows));pane.card_action(key,pane.edit_audio);app.update()
        self.assertEqual(app.pages.select(),str(app.metadata_page))
        app.history_view.set('Compacto');app.pages.select(app.history_page);app.update()
        self.assertTrue(pane.panel.winfo_ismapped());self.assertFalse(pane.cards.winfo_ismapped())
        self.assertEqual(PreferenceStore.clean({'history_view':'Completa'})['history_view'],'Completa')
    def test_complete_history_selects_only_one_card(self):
        app=self.app
        for _ in range(2):app.library.add_history(self.source,'WAV')
        app.history_view.set('Completa');app.pages.select(app.history_page);app.update()
        pane=app.history_page.ensure_ready();keys=list(pane.rows)
        pane.select_card(keys[0]);pane.select_card(keys[1])
        self.assertEqual(pane.table.selection(),(keys[1],))
        self.assertEqual(pane._selected_card.get(),keys[1])
        self.assertEqual(pane._cards[keys[0]][0].master.cget('style'),'Card.TFrame')
        self.assertEqual(pane._cards[keys[1]][0].master.cget('style'),'HistorySelected.TFrame')
    def test_control_wheel_resizes_complete_history_and_preserves_selection(self):
        app=self.app;app.library.add_history(self.source,'WAV')
        app.history_view.set('Completa');app.pages.select(app.history_page);app.update()
        pane=app.history_page.ensure_ready();key=next(iter(pane.rows));pane.select_card(key)
        for delta,expected in ((-120,'Médio'),(-120,'Pequeno'),(-120,'Pequeno'),(120,'Médio'),(120,'Grande'),(120,'Grande')):
            pane._cards[key][1].event_generate('<Control-MouseWheel>',delta=delta)
            app.update()
            self.assertEqual(app.history_card_size.get(),expected)
            self.assertEqual(pane.table.selection(),(key,))
        app.history_view.set('Compacto');app.update()
        pane.table.event_generate('<Control-MouseWheel>',delta=-120);app.update()
        self.assertEqual(app.history_card_size.get(),'Grande')
    def test_history_redirects_without_popup_and_keeps_unsaved_fields(self):
        app=self.app;app.library.add_history(self.source,'WAV');app.pages.select(app.history_page);app.update()
        history=app.history_page.ensure_ready();history.refresh();history.table.selection_set(history.table.get_children()[0])
        before=[w for w in app.winfo_children() if isinstance(w,tk.Toplevel)]
        history.edit_audio();app.update();editor=app.metadata_page.editor
        self.assertEqual(app.pages.select(),str(app.metadata_page));self.assertNotIsInstance(editor,tk.Toplevel)
        self.assertEqual(before,[w for w in app.winfo_children() if isinstance(w,tk.Toplevel)])
        self.assertEqual(editor.source.resolve(),self.source.resolve());editor.fields['title'].set('Unsaved edit')
        app.pages.select(app.history_page);app.update();app.pages.select(app.metadata_page);app.update()
        self.assertIs(app.metadata_page.editor,editor);self.assertEqual(editor.fields['title'].get(),'Unsaved edit')
    def test_inline_copy_overwrite_and_busy_close_guard(self):
        from audio_library import read_audio
        app=self.app;app.metadata_page.open_file(self.source);app.pages.select(app.metadata_page);app.update();editor=app.metadata_page.editor
        original=self.source.read_bytes();editor.fields['title'].set('Edited copy');editor.run(False);self.wait_save(editor)
        self.assertEqual(self.source.read_bytes(),original);rows=app.library.history();self.assertEqual(len(rows),1)
        self.assertEqual(read_audio(rows[0]['path'])['title'],'Edited copy')
        editor.overwrite.set(True);editor.fields['title'].set('Edited original');editor.run(False);self.wait_save(editor)
        self.assertEqual(read_audio(self.source)['title'],'Edited original');self.assertEqual(len(app.library.history()),1)
        editor.busy=True
        try:
            self.assertFalse(app.metadata_page.open_file(self.source));self.assertIs(app.metadata_page.editor,editor)
            with patch('app.messagebox.showinfo') as notice:app.close();notice.assert_called_once()
            self.assertTrue(app.winfo_exists())
        finally:editor.busy=False
