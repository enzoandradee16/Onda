import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from audio_tools import PreviewPlayer
from preferences import PreferenceStore
from preview_options import PREVIEW_DURATIONS, preview_seconds


class PreviewDurationTests(unittest.TestCase):
    def test_preferences_round_trip_and_reject_invalid_values(self):
        with tempfile.TemporaryDirectory() as folder:
            store = PreferenceStore(Path(folder) / "settings.json")
            for value in PREVIEW_DURATIONS:
                store.save({"effects_preview_duration": value, "search_preview_duration": "15 segundos"})
                self.assertEqual(store.load()["effects_preview_duration"], value)
                self.assertEqual(store.load()["search_preview_duration"], "15 segundos")
                self.assertGreaterEqual(preview_seconds(value), 10)
            for value in (None, True, 60, "0 segundos", "999 segundos", "30", []):
                self.assertNotIn("effects_preview_duration", PreferenceStore.clean({"effects_preview_duration": value}))
                with self.assertRaises(ValueError):
                    preview_seconds(value)

    def test_full_track_transport_keeps_long_duration_and_own_volume(self):
        player=PreviewPlayer();process=Mock(stderr=io.BytesIO(),returncode=0)
        with patch('audio_tools.executable',return_value='ffplay'),patch('audio_tools.subprocess.Popen',return_value=process) as launch:
            player.play('song.wav',duration=600,full_track=True,volume=35)
            player.events.get(timeout=5);player.events.get(timeout=5)
            command=launch.call_args.args[0]
            self.assertEqual(command[command.index('-volume')+1],'35')
            self.assertEqual(float(command[command.index('-t')+1]),600)
        player.close()
    def test_output_duration_is_independent_of_speed(self):
        for speed in (50, 100, 150):
            player = PreviewPlayer()
            process = Mock(stderr=io.BytesIO(), returncode=0)
            with patch("audio_tools.executable", return_value="ffplay"), patch("audio_tools.subprocess.Popen", return_value=process) as launch:
                player.play("song.wav", speed=speed, duration=60)
                self.assertIn("60 segundos", player.events.get(timeout=5)[1])
                self.assertEqual(player.events.get(timeout=5)[1], "Prévia encerrada.")
                command = launch.call_args.args[0]
                self.assertEqual(float(command[command.index("-t") + 1]), 60 * speed / 100)
                self.assertTrue(command[-1].endswith("atrim=duration=60"))
            player.close()
        for value in (0, 181, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                PreviewPlayer().play("song.wav", duration=value)


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Set ONDA_UI_TESTS for Tk integration")
class PreviewDurationUiTests(unittest.TestCase):
    def test_independent_settings_reach_effects_and_search_playback(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            app.withdraw()
            try:
                app.effects_preview_duration.set("90 segundos")
                app.search_preview_duration.set("15 segundos")
                source = Path(folder) / "song.wav"
                source.write_bytes(b"fixture")
                app.effects_page.source.set(str(source))
                with patch.object(app.effects_page.player, "play") as play:
                    app.effects_page.preview()
                    self.assertEqual(play.call_args.kwargs["duration"], 90)
                page = app.catalog_page
                with patch.object(page, "current", return_value={"preview_url": "https://example.com/preview.mp3"}), patch("catalog_ui.executable", return_value="ffplay"), patch("catalog_ui.subprocess.Popen") as launch:
                    page.preview()
                    command = launch.call_args.args[0]
                    self.assertEqual(command[command.index("-t") + 1], "15")
                    self.assertIn("15 segundos", page.status.get())
                    page.player = None
                app.remember_settings.set(True)
                app.preference_store.save({name: value.get() for name, value in app.preference_fields.items()})
                self.assertEqual(app.preference_store.load()["effects_preview_duration"], "90 segundos")
                self.assertEqual(app.preference_store.load()["search_preview_duration"], "15 segundos")
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
