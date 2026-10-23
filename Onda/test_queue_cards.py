import os,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch,MagicMock

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class QueueCardsTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.folder.name});self.env.start()
        from app import App
        self.app=App(show_welcome=False);self.app.withdraw();self.app.folder.set(self.folder.name)
    def tearDown(self):
        self.app.destroy();self.env.stop();self.folder.cleanup()
        from i18n import set_language
        set_language('pt-BR')
    def test_scroll_callbacks_are_reused_across_queue_refreshes(self):
        app=self.app
        app.queue_view.set('Compacto');app.queue_cards.refresh()
        def count():return len(app.tk.splitlist(app.tk.call('info','commands')))
        before=count()
        for _ in range(100):app.queue_cards.refresh()
        self.assertEqual(count(),before)
        app.queue_filter.query.set('missing');app.queue_cards.refresh()
        for _ in range(3):
            app.queue_filter.query.set('');app.queue_cards.refresh()
            app.queue_filter.query.set('missing');app.queue_cards.refresh()
        before=count()
        for _ in range(20):
            app.queue_filter.query.set('');app.queue_cards.refresh()
            app.queue_filter.query.set('missing');app.queue_cards.refresh()
        self.assertEqual(count(),before)

    def test_search_and_state_filters_leave_execution_model_intact(self):
        app=self.app
        first=app.add(lines=['https://example.com/a'],overrides={'display_name':'Antônio - Colette','queue_info':{'artists':['Piero Piccioni'],'album':'Cinema'}})[0]
        second=app.add(lines=['https://example.com/b'],overrides={'display_name':'Daft Punk - One More Time'})[0]
        app.jobs[second]['state']='Falhou'
        app.queue_view.set('Compacto');app.queue_filter.query.set('antonio');app.update()
        self.assertEqual(app.queue_filter.visible_keys(),(first,))
        self.assertEqual(app.queue_filter.view.get_children(),(first,))
        self.assertEqual(app.tree.get_children(),(first,second))
        app.queue_view.set('Completa');app.update()
        self.assertEqual(tuple(app.queue_cards.rows),(first,))
        app.queue_filter.query.set('');app.queue_filter.state.set('Com falha');app.update()
        self.assertEqual(tuple(app.queue_cards.rows),(second,))
        app.queue_filter.query.set('nonexistent');app.update()
        self.assertFalse(app.queue_cards.rows)
        self.assertEqual(len(app.jobs),2)
        app.queue_filter.clear();app.update()
        self.assertEqual(app.queue_filter.visible_keys(),(first,second))

    def test_compact_history_loads_metadata_icon(self):
        import json,time
        from pathlib import Path
        app=self.app
        path=Path(self.folder.name)/'track.mp3';path.write_bytes(b'fixture')
        Path(str(path)+'.metadata.json').write_text(json.dumps({'catalog':{'platform':'Apple / iTunes'}}))
        app.library.add_history(str(path),'mp3','https://music.apple.com/song/123')
        app.history_view.set('Compacto')
        app.pages.select(app.history_page);app.update()
        page=app.history_page.ensure_ready();page.refresh()
        key=page.table.get_children()[0]
        deadline=time.monotonic()+3
        while not page.table.item(key,'image') and time.monotonic()<deadline:
            app.update();time.sleep(.02)
        image=page.table.item(key,'image')
        self.assertTrue(image)
        self.assertEqual(int(app.tk.call('image','width',image[0])),18)
        self.assertEqual(page.table.column('#0','width'),52)
        page.table.selection_set(key);app.update()
        self.assertEqual(str(page.origin_button.cget('state')),'normal')

    def test_compact_restores_platform_icon_in_separate_column(self):
        app=self.app
        key=app.add(lines=['https://example.com/song'],overrides={'queue_info':{'platform':'Spotify'}})[0]
        app.queue_view.set('Completa');app.update()
        app.tree.item(key,image='')
        app.queue_view.set('Compacto');app.update()
        image=app.tree.item(key,'image')
        self.assertTrue(image)
        width=int(app.tk.call('image','width',image[0]))
        self.assertEqual(width,18)
        self.assertGreaterEqual(app.tree.column('#0','width'),width+30)
        self.assertIn('tree',str(app.tree.cget('show')))

    def test_card_selection_refreshes_visible_rows_once(self):
        key=self.app.add(lines=['https://example.com/song'])[0]
        self.app.queue_view.set('Completa')
        cards=self.app.queue_cards
        with patch.object(cards,'refresh',wraps=cards.refresh) as refresh:
            cards.select(key,True)
            self.assertEqual(refresh.call_count,1)
        self.assertIn(key,self.app.tree.selection())

    def test_cards_resize_select_update_and_keep_compact_model(self):
        app=self.app
        keys=app.add(lines=['https://youtu.be/abcdefghijk','https://youtu.be/lmnopqrstuv'])
        app.queue_view.set('Completa');app.update()
        cards=app.queue_cards
        self.assertEqual(set(cards.rows),set(keys))
        self.assertEqual(app.tree.winfo_manager(),'')
        cards.select(keys[0],True)
        self.assertIn(keys[0],app.tree.selection())
        old_history=app.history_card_size.get()
        for expected in ('Médio','Pequeno','Pequeno'):
            self.assertEqual(cards.resize_cards(SimpleNamespace(delta=-120)),'break')
            self.assertEqual(app.queue_card_size.get(),expected)
        self.assertEqual(app.history_card_size.get(),old_history)
        app.tree.set(keys[0],'name','Artist - Song');cards.refresh()
        self.assertEqual(cards.rows[keys[0]][2].cget('text'),'Artist - Song')
        app.pages.select(app.queue_page)
        app.event_generate('<Control-MouseWheel>',delta=120)
        self.assertEqual(app.queue_card_size.get(),'Médio')
        self.assertEqual(app.history_card_size.get(),old_history)
        app.queue_view.set('Compacto')
        self.assertEqual(app.tree.winfo_manager(),'pack')
        self.assertIn(keys[0],app.tree.selection())
    def test_artwork_metadata_persist_and_history_toolbar_is_centered(self):
        import io,time
        from PIL import Image
        image=io.BytesIO();Image.new('RGB',(90,90),'red').save(image,format='PNG')
        app=self.app
        info={'album':'Album','artists':['Artist'],'cover_url':'https://example.com/cover.png','duration_ms':240000,'release_date':'2024-01-01'}
        with patch('catalog_ui.cached_cover_png',return_value=image.getvalue()) as fetch:
            key=app.add(lines=['https://example.com/song'],overrides={'display_name':'My chosen title','queue_info':info})[0]
            app.queue_view.set('Completa')
            deadline=time.monotonic()+3
            while time.monotonic()<deadline and not getattr(app.queue_cards.covers[key],'_queue_image',None):
                time.sleep(.01);app.queue_cards.refresh()
            self.assertTrue(app.queue_cards.covers[key].cget('image'))
            fetch.assert_called_once_with(info['cover_url'])
            self.assertIn('Album',app.queue_cards.rows[key][3].cget('text'))
            self.assertIn('2024-01-01',app.queue_cards.rows[key][3].cget('text'))
            app.events.put((key,{'type':'queue_title','url':'https://example.com/song','title':'Other name','queue_info':{'genre':'House'}}))
            app.after_cancel(app._poll_after);app.poll_events()
            self.assertEqual(app.jobs[key]['display_name'],'My chosen title')
            self.assertEqual(app.library.load_queue()[0]['queue_info']['genre'],'House')
        app.history_page.ensure_ready()
        history=app.history_page
        app.history_view.set('Completa')
        app.pages.select(history);app.deiconify();app.update()
        toolbar=history.size_controls.master
        children=toolbar.winfo_children()
        centers=[w.winfo_y()+w.winfo_height()/2 for w in children if w.winfo_manager()]
        self.assertLess(max(centers)-min(centers),2)
        self.assertAlmostEqual(toolbar.winfo_x()+toolbar.winfo_width()/2,toolbar.master.winfo_width()/2,delta=2)

    def test_pending_restart_button_reverts_and_preserves_queue(self):
        app=self.app
        app.add(lines=['https://youtu.be/abcdefghijk'])
        self.assertEqual(app.restart_button.winfo_manager(),'')
        app.language.set('en')
        self.assertEqual(app.restart_button.winfo_manager(),'pack')
        app.language.set('pt-BR')
        self.assertEqual(app.restart_button.winfo_manager(),'')
        app.theme_mode.set('Escuro');self.assertEqual(app.restart_button.winfo_manager(),'')
        app.language.set('es')
        app.running=True
        with patch('app.messagebox.showinfo') as notice:
            app.restart_app();notice.assert_called_once()
        self.assertIsNot(getattr(app,'restart_requested',False),True)
        app.running=False
        with patch.object(app,'close') as close:
            app.restart_app();close.assert_called_once()
        self.assertIs(app.restart_requested,True)
        app.restart_requested=False
    def test_actual_restart_recreates_localized_window_with_queue(self):
        from app import App
        app=self.app
        app.add(lines=['https://youtu.be/abcdefghijk'])
        app.language.set('en')
        app.restart_app()
        self.app=App(show_welcome=False)
        self.app.withdraw()
        self.assertEqual(self.app.language.get(),'en')
        self.assertEqual(self.app.restart_button.winfo_manager(),'')
        self.assertTrue(any(job.get('url')=='https://youtu.be/abcdefghijk' for job in self.app.jobs.values()))

    def test_preferences_export_accept_queue_display(self):
        from preferences import PreferenceStore
        from advanced_options import export_settings,import_settings
        values={'queue_view':'Completa','queue_card_size':'Pequeno'}
        self.assertEqual(PreferenceStore.clean(values),dict(values,confirm_version=False))
        self.assertEqual(import_settings(export_settings(values,'windows'),'windows')['queue_card_size'],'Pequeno')

class RestartLoopTests(unittest.TestCase):
    def test_new_queue_controls_share_all_language_translations(self):
        from i18n import tr,set_language
        try:
            for language,view,size,restart in (('pt-BR','Completa ▾','Cards: Pequeno ▾','Reiniciar'),('es','Completa ▾','Tarjetas: Pequeño ▾','Reiniciar'),('en','Full ▾','Cards: Small ▾','Restart')):
                set_language(language)
                self.assertEqual(tr('Completa ▾'),view)
                self.assertEqual(tr('Cards: Pequeno ▾'),size)
                self.assertEqual(tr('Reiniciar'),restart)
        finally:set_language('pt-BR')

    def test_restart_reuses_single_instance_guard(self):
        from single_instance import run_single_instance
        first=SimpleNamespace(restart_requested=True,mainloop=MagicMock())
        second=SimpleNamespace(restart_requested=False,mainloop=MagicMock())
        factory=MagicMock(side_effect=[first,second])
        with patch('single_instance.SingleInstance') as instance:
            instance.return_value.__enter__.return_value.primary=True
            self.assertEqual(run_single_instance(factory),0)
            self.assertEqual(factory.call_count,2)
            self.assertEqual(instance.return_value.__enter__.return_value.watch.call_count,2)

if __name__=='__main__':unittest.main()
