import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from window_icons import draw_icon, icon_kind


class WindowIconTests(unittest.TestCase):
    def test_function_icons_are_distinct_and_support_window_sizes(self):
        titles = (
            "Onda • Configurações",
            "Onda • Detalhes dos downloads",
            "Sobre o Onda",
            "Onda • Metadados de músicas",
            "Onda • Escolha a versão",
            "Onda • Escolha o formato",
            "Escolher fotos e vídeos",
            "Onda • Arquivo já existe",
        )
        images = []
        for title in titles:
            kind = icon_kind(title)
            self.assertIsNotNone(kind)
            for size in (16, 32, 48):
                image = draw_icon(kind, size)
                self.assertEqual(image.size, (size, size))
                self.assertIsNotNone(image.getbbox())
            images.append(draw_icon(kind, 32).tobytes())
        self.assertEqual(len(set(images)), len(titles))
        self.assertIsNone(icon_kind("Onda • Vídeo, áudio & fotos"))


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class SettingsScrollUiTests(unittest.TestCase):
    def test_root_brand_and_spinbox_theme_colors(self):
        from app import App
        from tkinter import ttk

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"LOCALAPPDATA": folder}),
        ):
            app = App(show_welcome=False)
            app.clipboard_watch.shutdown()
            try:
                self.assertEqual(app._function_icon_key[0], "onda")
                for mode in ("Escuro", "Preto puro", "Claro"):
                    app.theme_mode.set(mode)
                    app.update()
                    colors = app.theme_manager.colors
                    self.assertEqual(
                        app._function_icon_key,
                        ("onda", colors["accent"], colors["text"], colors["bg"]),
                    )
                    self.assertEqual(
                        ttk.Style(app).lookup("TSpinbox", "foreground"), colors["text"]
                    )
                    self.assertEqual(
                        ttk.Style(app).lookup("TSpinbox", "fieldbackground"),
                        colors["input"],
                    )
            finally:
                app.destroy()

    def test_categories_scroll_to_last_control_and_footer_stays_visible(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"LOCALAPPDATA": folder}),
        ):
            from app import App
            from tkinter import ttk

            app = App()
            app.withdraw()
            try:
                ttk.Style(app).configure(".", font=("Segoe UI", 14))
                app.settings_window.geometry("600x620")
                app.show_settings()
                app.update()
                self.assertEqual(app.settings_window._function_icon_kind, "settings")
                self.assertEqual(len(app.settings_window._function_icons), 3)
                for tab in app.settings_pages.tabs():
                    app.settings_pages.select(tab)
                    app.update()
                    page = app.settings_categories[tab]
                    last = page.content.winfo_children()[-1]
                    page.canvas.yview_moveto(1)
                    app.update()
                    self.assertLessEqual(
                        last.winfo_rooty() + last.winfo_height(),
                        page.canvas.winfo_rooty() + page.canvas.winfo_height() + 1,
                    )
                # Force overflow to verify mouse-wheel behavior independent of display DPI.
                page = app.settings_categories[app.settings_pages.select()]
                spacer = ttk.Frame(page.content, height=1000)
                spacer.pack(fill="x")
                app.update()
                page.canvas.yview_moveto(0)
                page.wheel(SimpleNamespace(widget=page.canvas, delta=-120))
                self.assertGreater(page.canvas.yview()[0], 0)
                buttons = [
                    w
                    for w in app.settings_window.winfo_children()[0].winfo_children()
                    if isinstance(w, ttk.Frame)
                ]
                footer = buttons[0]
                self.assertTrue(footer.winfo_ismapped())
                self.assertLessEqual(
                    footer.winfo_y() + footer.winfo_height(),
                    footer.master.winfo_height(),
                )
                app.show_log()
                app.update()
                self.assertEqual(app.log_window._function_icon_kind, "log")
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
