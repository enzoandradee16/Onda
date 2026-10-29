import os, tempfile, tkinter as tk, unittest
from tkinter import ttk
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class CatalogDisplayTests(unittest.TestCase):
    def test_badge_comparison_warning_and_short_mp3_label(self):
        from app import App
        from engine import MODES
        from i18n_tk import TranslatedCombobox

        with (
            tempfile.TemporaryDirectory() as root,
            patch.dict(os.environ, {'LOCALAPPDATA': root}),
        ):
            app = App(show_welcome=False)
            app.clipboard_watch.shutdown()
            app.update()
            try:
                pane = app.catalog_page
                pane.records = [
                    {
                        'title': 'Song',
                        'artists': ['Artist'],
                        'album': 'Album',
                        'release_date': '2020-05',
                        'platform': 'Deezer',
                        'source_url': 'https://www.deezer.com/track/1',
                    },
                    {
                        'title': 'Other song',
                        'artists': ['Artist'],
                        'source_url': 'https://www.deezer.com/track/2',
                    },
                ]
                for i, row in enumerate(pane.records):
                    pane.table.insert('', 'end', iid=str(i), values=(row['title'],))
                pane.table.selection_set('0')
                pane.selected()
                self.assertEqual(pane.platform_label.cget('text'), 'Deezer')
                self.assertEqual(str(pane.platform_label.cget('compound')), 'left')
                self.assertTrue(pane.platform_label.cget('image'))
                self.assertNotIn('Deezer', pane.track_info.get())
                self.assertEqual(pane.track_info.get(), 'Artist — Album')
                self.assertEqual(int(pane.info_label.grid_info()['row']), 1)
                self.assertEqual(int(pane.platform_label.grid_info()['row']), 3)
                self.assertEqual(
                    pane.release_label.cget('text'), 'Data de lançamento: 05/2020'
                )
                self.assertEqual(pane.release_label.winfo_manager(), 'grid')
                pane.table.selection_set('1')
                pane.selected()
                self.assertEqual(pane.release_label.winfo_manager(), '')
                pane.table.selection_set('0')
                pane.selected()
                pane.compare_results()

                def walk(parent):
                    for child in parent.winfo_children():
                        yield child
                        yield from walk(child)

                dialog = next(
                    w
                    for w in walk(app)
                    if isinstance(w, tk.Toplevel) and w.title() == 'Comparar resultados'
                )
                body = dialog.winfo_children()[0]
                combos = [
                    w for w in body.winfo_children() if isinstance(w, ttk.Combobox)
                ]
                text = next(w for w in body.winfo_children() if isinstance(w, tk.Text))
                combos[1].set(combos[0].get())
                app.update()
                self.assertIn('Essa música já foi selecionada', text.get('1.0', 'end'))
                combos[1].current(1)
                app.update()
                self.assertNotIn(
                    'Essa música já foi selecionada', text.get('1.0', 'end')
                )
                variable = tk.StringVar(value='Áudio · MP3 (320 kbps)')
                combo = TranslatedCombobox(
                    app, textvariable=variable, values=tuple(MODES)
                )
                self.assertEqual(ttk.Combobox.get(combo), 'Áudio · MP3')
                self.assertEqual(MODES[variable.get()], 'mp3')
                combo.destroy()
                dialog.destroy()
            finally:
                app.destroy()
