import os
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from keyboard_shortcuts import SHORTCUTS
from i18n import catalog


class ShortcutReferenceTests(unittest.TestCase):
    def test_all_reference_descriptions_are_translated(self):
        self.assertEqual(len(SHORTCUTS), len({key for key, _ in SHORTCUTS}))
        for language in ('en', 'es'):
            for _, label in SHORTCUTS:
                self.assertIn(label, catalog(language))


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class KeyboardShortcutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        from app import App

        self.app = App(show_welcome=False)
        self.app.folder.set(self.temp.name)
        self.app.update()

    def tearDown(self):
        self.app.running = False
        self.app.parallel.workers.clear()
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def send(self, sequence, widget=None):
        widget = widget or self.app
        widget.focus_force()
        self.app.update()
        widget.event_generate(sequence)
        self.app.update()

    def test_control_a_selects_queue_playlist_and_history_but_keeps_text_selection(
        self,
    ):
        app = self.app
        for page, table in (
            (app.queue_page, app.tree),
            (app.playlist_page, app.playlist_page.table),
            (app.history_page, app.history_page.table),
        ):
            app.pages.select(page)
            ids = [
                table.insert('', 'end', values=('one',)),
                table.insert('', 'end', values=('two',)),
            ]
            self.send('<Control-a>', table)
            self.assertEqual(set(table.selection()), set(ids))
            table.delete(*ids)
        self.send('<Control-l>')
        app.urls.insert('1.0', 'text stays intact')
        self.send('<Control-a>', app.urls)
        self.assertEqual(app.urls.get('1.0', 'end-1c'), 'text stays intact')
        self.assertTrue(app.urls.tag_ranges('sel'))

    def test_control_arrows_scroll_only_current_page(self):
        app = self.app
        self.send('<Control-l>')
        with (
            patch.object(app.download_page.canvas, 'yview_scroll') as scroll,
            patch.object(app.queue_page.canvas, 'yview_scroll') as other,
        ):
            self.send('<Control-Down>', app.urls)
            self.send('<Control-Up>', app.urls)
        self.assertEqual(
            scroll.call_args_list,
            [unittest.mock.call(1, 'pages'), unittest.mock.call(-1, 'pages')],
        )
        other.assert_not_called()

    def test_numeric_shortcuts_follow_reordered_tabs_and_cycle_once(self):
        app = self.app
        app.tab_reorder.apply(
            [
                'images',
                'queue',
                'downloads',
                'catalog',
                'history',
                'playlists',
                'metadata',
                'effects',
                'converter',
            ]
        )
        self.send('<Control-Key-1>')
        self.assertEqual(app.pages.select(), str(app.images_page))
        self.send('<Control-Tab>', app.pages)
        self.assertEqual(app.pages.select(), str(app.queue_page))
        self.send('<Control-Shift-Tab>', app.pages)
        self.assertEqual(app.pages.select(), str(app.images_page))
        self.send('<Control-Key-8>')
        self.assertEqual(app.pages.select(), str(app.effects_page))

    def test_links_focus_and_text_remain_intact_for_global_shortcuts(self):
        app = self.app
        app.urls.insert('1.0', 'https://example.com/a')
        self.send('<Control-l>')
        self.assertEqual(app.pages.select(), str(app.download_page))
        self.assertEqual(app.focus_get(), app.urls)
        before = app.urls.get('1.0', 'end')
        with patch.object(app, 'open_metadata') as metadata:
            self.send('<Control-m>', app.urls)
        metadata.assert_called_once_with()
        self.assertEqual(app.urls.get('1.0', 'end'), before)
        with patch.object(app, 'open_folder') as folder:
            self.send('<Control-o>', app.urls)
        folder.assert_called_once_with()
        self.assertEqual(app.urls.get('1.0', 'end'), before)

    def test_download_and_add_require_links_and_do_not_insert_newlines(self):
        app = self.app
        with patch.object(app, 'download_now') as now, patch.object(app, 'add') as add:
            self.send('<Control-Return>')
            now.assert_not_called()
            self.send('<Control-l>')
            app.urls.insert('1.0', 'https://example.com/a')
            text = app.urls.get('1.0', 'end')
            self.send('<Control-Return>', app.urls)
            now.assert_called_once_with()
            self.send('<Control-Shift-Return>', app.urls)
            add.assert_called_once_with()
            self.assertEqual(app.urls.get('1.0', 'end'), text)
            self.assertEqual(app.urls.bind('<Return>'), '')

    def test_queue_commands_are_scoped_and_stop_requires_running_work(self):
        app = self.app
        with patch.object(app, 'start') as start, patch.object(app, 'cancel') as stop:
            self.send('<F5>')
            start.assert_not_called()
            self.send('<Shift-F5>')
            stop.assert_not_called()
            self.send('<Control-j>')
            self.send('<F5>')
            start.assert_called_once_with()
            app.running = True
            self.send('<Shift-F5>')
            stop.assert_called_once_with()

    def test_queue_reordering_retry_and_view_toggle_keep_model(self):
        app = self.app
        ids = app.add(lines=['https://example.com/a', 'https://example.com/b'])
        self.send('<Control-j>')
        app.tree.selection_set(ids[1])
        self.send('<Alt-Up>')
        self.assertEqual(app.tree.get_children()[0], ids[1])
        app.set_state(ids[1], 'Falhou')
        self.send('<Control-r>')
        self.assertEqual(app.jobs[ids[1]]['state'], 'Na fila')
        old = app.queue_view.get()
        self.send('<Alt-v>')
        self.assertNotEqual(app.queue_view.get(), old)
        self.assertEqual(set(app.jobs), set(ids))

    def test_clear_chord_does_not_first_trigger_plain_delete(self):
        app = self.app
        ids = app.add(lines=['https://example.com/a', 'https://example.com/b'])
        self.send('<Control-j>')
        app.queue_view.set('Compacto')
        app.update()
        app.tree.selection_set(ids[0])
        with patch.object(app, 'clear_queue') as clear:
            self.send('<Control-Shift-Delete>', app.tree)
        clear.assert_called_once_with()
        self.assertEqual(set(app.jobs), set(ids))

    def test_editable_fields_keep_native_keys_in_queue(self):
        app = self.app
        self.send('<Control-j>')
        text = tk.Text(app.queue_page.content, height=1)
        text.grid(row=7, column=0)
        text.insert('1.0', 'editable')
        app.update()
        with (
            patch.object(app, 'clear_queue') as clear,
            patch('advanced_ui.move_queue') as move,
        ):
            self.send('<Control-Shift-Delete>', text)
            self.send('<Alt-Up>', text)
        clear.assert_not_called()
        move.assert_not_called()

    def test_dialog_and_modal_grab_block_background_actions(self):
        app = self.app
        app.running = True
        dialog = tk.Toplevel(app)
        field = tk.Entry(dialog)
        field.pack()
        app.update()
        try:
            with patch.object(app, 'cancel') as cancel:
                self.assertIsNone(
                    app.shortcuts.dispatch('stop', SimpleNamespace(widget=field))
                )
                dialog.grab_set()
                self.assertIsNone(
                    app.shortcuts.dispatch('stop', SimpleNamespace(widget=app))
                )
                cancel.assert_not_called()
        finally:
            dialog.grab_release()
            dialog.destroy()

    def test_search_focus_uses_the_active_page(self):
        app = self.app
        self.send('<Control-f>')
        self.assertEqual(app.focus_get(), app.catalog_page.entry)
        app.pages.select(app.playlist_page)
        app.update()
        self.send('<Control-f>')
        self.assertEqual(app.focus_get(), app.playlist_page.search_entry)
        self.send('<Control-h>')
        self.send('<Control-f>')
        self.assertEqual(app.focus_get(), app.history_page.search_entry)

    def test_shift_shortcut_does_not_trigger_unshifted_action(self):
        app = self.app
        app.pages.select(app.queue_page)
        app.update()
        with patch.object(app, 'show_log') as show:
            self.send('<Control-Shift-L>')
        show.assert_called_once_with()
        self.assertEqual(app.pages.select(), str(app.queue_page))

    def test_help_opens_once_and_does_not_capture_dialog_shortcuts(self):
        app = self.app
        self.send('<F1>')
        first = app.shortcuts.window
        self.assertTrue(first.winfo_exists())
        app.shortcuts.show_help()
        self.assertIs(app.shortcuts.window, first)
        self.assertNotIn(app.shortcuts.tag, first.bindtags())
        self.assertIn(app.shortcuts.tag, app.urls.bindtags())


if __name__ == '__main__':
    unittest.main()
