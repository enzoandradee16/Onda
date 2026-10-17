import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tab_order import normalize_hidden,DEFAULT_ORDER,REQUIRED_TABS
from preferences import PreferenceStore

class VisibilityPreferenceTests(unittest.TestCase):
    def test_required_unknown_and_duplicates_are_removed(self):
        self.assertEqual(normalize_hidden(['queue','images','images','missing',None,'catalog']),['images'])
        self.assertEqual(normalize_hidden('images'),[])
        self.assertEqual(set(normalize_hidden(DEFAULT_ORDER)),set(DEFAULT_ORDER)-REQUIRED_TABS)
    def test_restart_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            store=PreferenceStore(Path(root)/'settings.json');store.save({'hidden_tabs':['images','history','queue']})
            self.assertEqual(PreferenceStore(store.path).load()['hidden_tabs'],['images','history'])

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class VisibilityUiTests(unittest.TestCase):
    def test_hide_reorder_shortcuts_reset_and_restart(self):
        from app import App
        from reset_settings import apply_defaults
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'LOCALAPPDATA':root}):
            app=App(show_welcome=False);app.update()
            try:
                app.pages.select(app.images_page);app.update()
                app.hidden_tabs.set(('images','history'));app.update()
                self.assertNotEqual(app.pages.select(),str(app.images_page))
                app.pages.select(app.history_page)
                self.assertNotEqual(app.pages.select(),str(app.history_page))
                app.tab_reorder.apply(list(reversed(DEFAULT_ORDER)))
                self.assertEqual(app.pages.tab(app.images_page,'state'),'hidden')
                self.assertEqual(len(app.pages.visible_tabs()),7)
                from keyboard_shortcuts import KeyboardShortcuts
                shortcuts=KeyboardShortcuts(app)
                app.pages.select(app.queue_page);shortcuts.dispatch('next');app.update()
                self.assertNotIn(app.pages.select(),[str(app.images_page),str(app.history_page)])
                app.persist_preferences()
            finally:app.destroy()
            app=App(show_welcome=False);app.update()
            try:
                self.assertEqual(set(app.hidden_tabs.get()),{'images','history'})
                self.assertEqual(app.pages.tab(app.images_page,'state'),'hidden')
                apply_defaults(app,['hidden_tabs']);app.update()
                self.assertEqual(len(app.pages.visible_tabs()),9)
                app.hidden_tabs.set(tuple(DEFAULT_ORDER));app.update()
                self.assertEqual(len(app.pages.visible_tabs()),3)
                self.assertTrue(all(app.pages.tab(app.tab_reorder.pages[k],'state')=='normal' for k in REQUIRED_TABS))
            finally:app.destroy()
