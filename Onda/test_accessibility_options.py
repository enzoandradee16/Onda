import json
import os
import tempfile
import unittest
from unittest.mock import patch
from shortcut_options import validate_overrides,effective_bindings,canonical
from appearance import palette
from preferences import PreferenceStore

class OptionTests(unittest.TestCase):
    def test_conflicts_reserved_and_invalid_chords(self):
        for value in ({'links':'<Control-j>'},{'links':'<Control-c>'},{'links':'<Alt-F4>'},
                      {'links':'<Shift-a>'},{'links':'a'},{'unknown':'<F6>'},{'links':False}):
            with self.subTest(value=value),self.assertRaises(ValueError):validate_overrides(value)
        self.assertEqual(canonical('<Control-Shift-K>'),'<Control-Shift-k>')
        self.assertEqual(canonical('<Control-KP_Enter>'),'<Control-Return>')
        bindings=effective_bindings(json.dumps({'download':'<Control-k>','links':''}))
        self.assertEqual(bindings['<Control-k>'],'download')
        self.assertNotIn('<Control-Return>',bindings)
        self.assertNotIn('<Control-KP_Enter>',bindings)
        self.assertNotIn('<Control-l>',bindings)
        self.assertIn('<Control-l>',effective_bindings('invalid'))

    def test_contrast_and_preferences(self):
        def luminance(color):
            values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
            return sum(weight*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for v,weight in zip(values,(.2126,.7152,.0722)))
        def ratio(a,b):
            hi,lo=sorted((luminance(a),luminance(b)),reverse=True)
            return (hi+.05)/(lo+.05)
        c=palette('Alto contraste')
        for role in ('text','muted','line','accent'):
            self.assertGreaterEqual(ratio(c[role],c['bg']),7)
        self.assertGreaterEqual(ratio(c['text'],c['selected']),7)
        self.assertGreaterEqual(ratio(c['accent'],c['accent_text']),7)
        self.assertFalse(c['flat_black'])
        data=PreferenceStore.clean({'theme_mode':'Alto contraste','shortcut_keys':json.dumps({'links':'<Control-k>'})})
        self.assertEqual(data['theme_mode'],'Alto contraste')
        self.assertEqual(json.loads(data['shortcut_keys']),{'links':'<Control-k>'})

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class AccessibilityUiTests(unittest.TestCase):
    def test_live_shortcuts_persistence_and_reversible_theme(self):
        from app import App
        from tkinter import ttk
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.clipboard_watch.shutdown();app.update()
            try:
                app.shortcuts.set_shortcut('links','<Control-k>')
                app.pages.select(app.queue_page);app.focus_force();app.update()
                app.event_generate('<Control-k>');app.update()
                self.assertEqual(app.pages.select(),str(app.download_page))
                app.pages.select(app.queue_page);app.update()
                app.event_generate('<Control-l>');app.update()
                self.assertEqual(app.pages.select(),str(app.queue_page))
                with self.assertRaises(ValueError):app.shortcuts.set_shortcut('links','<Control-j>')
                app.shortcuts.show_help();app.update()
                app.shortcuts.reference_tree.selection_set('links')
                app.shortcuts.edit_selected();app.update()
                dialogs=app.shortcuts.window.winfo_children()
                from tkinter import Toplevel
                dialog=next(child for child in dialogs if isinstance(child,Toplevel))
                field=next(child for child in dialog.winfo_children()[0].winfo_children() if isinstance(child,ttk.Entry))
                field.event_generate('<Control-Shift-p>');app.update()
                buttons=dialog.winfo_children()[0].winfo_children()[-1].winfo_children()
                next(button for button in buttons if button.cget('text')=='Salvar').invoke();app.update()
                self.assertFalse(dialog.winfo_exists())
                self.assertEqual(json.loads(app.shortcut_keys.get()),{'links':'<Control-Shift-p>'})
                app.shortcuts.window.destroy()
                app.theme_mode.set('Alto contraste');app.update()
                style=ttk.Style(app)
                self.assertEqual(style.lookup('TEntry','foreground'),'#ffffff')
                self.assertEqual(int(style.lookup('TButton','focusthickness')),2)
                self.assertEqual(style.lookup('Treeview','background',('selected',)),'#003366')
                self.assertEqual(style.lookup('Accent.TButton','background',('disabled',)),'#000000')
                self.assertEqual(style.lookup('Accent.TButton','foreground',('disabled',)),'#a6a6a6')
                app.persist_preferences()
                loaded=app.preference_store.load()
                self.assertEqual(json.loads(loaded['shortcut_keys']),{'links':'<Control-Shift-p>'})
                self.assertEqual(loaded['theme_mode'],'Alto contraste')
                app.theme_mode.set('Claro');app.update()
                self.assertEqual(int(style.lookup('TButton','focusthickness')),0)
                self.assertNotEqual(style.lookup('TEntry','foreground'),'#ffffff')
                app.shortcut_keys.set('{}')
                self.assertIn('<Control-l>',app.shortcuts.bound)
                self.assertNotIn('<Control-k>',app.shortcuts.bound)
            finally:app.destroy()

if __name__=='__main__':unittest.main()
