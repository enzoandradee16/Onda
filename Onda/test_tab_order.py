import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from tab_order import DEFAULT_ORDER, normalize_order
from preferences import PreferenceStore


class TabPreferenceTests(unittest.TestCase):
    def test_normalize_old_or_invalid_order_preserves_all_tabs(self):
        self.assertEqual(normalize_order(['effects','catalog','effects','missing',{}]),['effects','catalog','downloads','images','playlists','history'])
        self.assertEqual(normalize_order('effects'),list(DEFAULT_ORDER))
        self.assertEqual(normalize_order(['downloads','catalog','playlists','history','effects'])[-1],'images')
        self.assertNotIn('tab_order',PreferenceStore.clean({'tab_order':'invalid'}))

    def test_saved_order_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            store=PreferenceStore(Path(folder)/'settings.json')
            order=list(reversed(DEFAULT_ORDER))
            store.save({'tab_order':tuple(order)})
            self.assertEqual(store.load()['tab_order'],order)


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class TabDragTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name})
        self.env.start()
        from app import App
        self.app=App(show_welcome=False)
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def center(self,key):
        notebook=self.app.pages
        tab=str(self.app.tab_reorder.pages[key])
        coords=[]
        import tkinter as tk
        for x in range(notebook.winfo_width()):
            try:
                if notebook.tabs()[notebook.index(f'@{x},15')]==tab:
                    coords.append(x)
            except tk.TclError:pass
        self.assertTrue(coords)
        return coords[len(coords)//2],15

    def drag(self,key,target,release=True):
        notebook=self.app.pages
        x,y=self.center(key)
        notebook.event_generate('<ButtonPress-1>',x=x,y=y)
        x,y=self.center(target)
        notebook.event_generate('<B1-Motion>',x=x,y=y)
        if release:notebook.event_generate('<ButtonRelease-1>',x=x,y=y)
        self.app.update()

    def test_real_drag_keeps_active_tab_and_saves_order_on_restart(self):
        app=self.app
        app.remember_settings.set(True)
        app.pages.select(app.effects_page)
        app.update()
        self.drag('images','catalog')
        self.assertEqual(app.tab_reorder.order()[0],'images')
        self.assertEqual(app.pages.select(),str(app.effects_page))
        app.persist_preferences()
        order=app.tab_reorder.order()
        app.destroy()
        from app import App
        self.app=App(show_welcome=False)
        self.app.update()
        self.assertEqual(self.app.tab_reorder.order(),order)

    def test_click_selection_cancel_and_context_moves(self):
        app=self.app
        notebook=app.pages
        x,y=self.center('images')
        notebook.event_generate('<ButtonPress-1>',x=x,y=y)
        notebook.event_generate('<ButtonRelease-1>',x=x,y=y)
        app.update()
        self.assertEqual(notebook.select(),str(app.images_page))
        before=app.tab_reorder.order()
        self.drag('effects','catalog',release=False)
        notebook.focus_force()
        app.update()
        notebook.event_generate('<Escape>')
        app.update()
        self.assertEqual(app.tab_reorder.order(),before)
        app.tab_reorder.context_tab=str(app.images_page)
        app.tab_reorder.move(-1)
        self.assertEqual(app.tab_reorder.order()[1],'images')
        app.tab_reorder.reset()
        self.assertEqual(app.tab_reorder.order(),list(DEFAULT_ORDER))
        self.assertEqual(notebook.select(),str(app.images_page))

    def test_session_only_does_not_persist_and_queue_actions_follow_identity(self):
        app=self.app
        self.drag('downloads','effects')
        self.assertFalse(app.preference_store.path.exists())
        self.assertEqual(app.tab_order.get(),tuple(app.tab_reorder.order()))
        app.folder.set(self.temp.name)
        items=app.add(lines=['https://example.com/a','https://example.com/b'])
        app.pages.select(app.download_page)
        app.select_all_items()
        self.assertEqual(set(app.tree.selection()),set(items))
