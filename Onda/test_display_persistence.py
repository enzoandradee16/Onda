import os, subprocess, sys, tempfile, unittest
from pathlib import Path


class DisplayPersistenceTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
    def test_both_windows_survive_new_process(self):
        for remember in (False, True):
            for view in ("Compacto", "Completa"):
                with (
                    self.subTest(remember=remember, view=view),
                    tempfile.TemporaryDirectory() as folder,
                ):
                    env = {**os.environ, "LOCALAPPDATA": folder}
                    setup = (
                        "from app import App; a=App(show_welcome=False); a.withdraw(); a.remember_settings.set(%r); a.toggle_remember_settings(); a.queue_view.set(%r); a.history_view.set(%r); a.queue_card_size.set('Pequeno'); a.history_card_size.set('Médio'); a.persist_preferences(); a.destroy()"
                        % (remember, view, view)
                    )
                    check = (
                        "from app import App; a=App(show_welcome=False); a.withdraw(); assert a.queue_view.get()==%r; assert a.history_view.get()==%r; assert a.queue_card_size.get()=='Pequeno'; assert a.history_card_size.get()=='Médio'; assert a.remember_settings.get()==%r; a.destroy()"
                        % (view, view, remember)
                    )
                    for code in (setup, check):
                        result = subprocess.run(
                            [sys.executable, "-X", "utf8", "-c", code],
                            cwd=Path(__file__).parent,
                            env=env,
                            capture_output=True,
                            text=True,
                            timeout=45,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
    def test_portable_default_saves_theme_and_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, "LOCALAPPDATA": folder}
            values = {
                "theme_mode": "Preto puro",
                "theme_accent": "Roxo",
                "interface_font_size": "130%",
                "mp3_quality": "192 kbps",
                "playlist": True,
                "auto_match": True,
                "effects_keep_pitch": True,
                "concurrent_downloads": "3",
                "image_format": "PNG",
                "image_width": "640",
                "image_height": "480",
                "image_keep_ratio": False,
            }
            setup = (
                "from app import App; a=App(show_welcome=False); a.withdraw(); assert a.remember_settings.get(); values="
                + repr(values)
                + "; [a.preference_fields[k].set(v) for k,v in values.items()]; a.persist_preferences(); a.destroy()"
            )
            check = (
                "from app import App; a=App(show_welcome=False); a.withdraw(); assert a.remember_settings.get(); values="
                + repr(values)
                + "; actual={k:a.preference_fields[k].get() for k in values}; assert actual==values,(actual,values); a.destroy()"
            )
            portable = Path(__file__).resolve().parents[1] / "Portatil/Onda"
            for code in (setup, check):
                result = subprocess.run(
                    [sys.executable, "-X", "utf8", "-c", code],
                    cwd=portable,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
