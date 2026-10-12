import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audio_tools import effects_filter, effect_name, source_position


class SpedUpTests(unittest.TestCase):
    def test_effect_names_and_speed_limits(self):
        self.assertEqual(effect_name(125, 0), "Sped Up")
        self.assertEqual(effect_name(125, 30), "Sped Up + Reverb")
        self.assertEqual(effect_name(100, 0), "")
        self.assertEqual(effect_name(100, 30), "Reverb")
        for speed in (50, 100, 150):
            effects_filter(speed, 0)
        for speed in (49, 151, float("nan"), float("inf")):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                effects_filter(speed, 0)

    def test_sped_up_clock_stays_on_source_timeline(self):
        self.assertAlmostEqual(source_position("  4.00 M-A: 0.00", 150), 6)


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Set ONDA_UI_TESTS for Tk integration")
class SpedUpUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.environment.start()
        from app import App
        self.app = App()
        self.app.withdraw()
        self.pane = self.app.effects_page

    def tearDown(self):
        self.app.destroy()
        self.environment.stop()
        self.temp.cleanup()

    def test_fast_presets_and_original_are_visible_and_consistent(self):
        pane = self.pane
        self.assertEqual(float(pane.speed_slider["from"]), 50)
        self.assertEqual(float(pane.speed_slider["to"]), 150)
        for name, speed, reverb in (("Sped Up leve", 115, 0), ("Sped Up intenso", 130, 0),
                                    ("Sped Up + Reverb", 120, 25), ("Original", 100, 0)):
            pane.preset.set(name)
            pane.apply_preset()
            self.assertEqual(pane.speed.get(), speed)
            self.assertEqual(pane.reverb.get(), reverb)
            self.assertIn("Sped Up" if speed > 100 else "original", pane.speed_label.get())

    def test_preview_and_export_filename_use_fast_settings(self):
        pane = self.pane
        source = Path(self.temp.name) / "Artista - Música.wav"
        source.write_bytes(b"fixture")
        pane.source.set(str(source))
        pane.speed.set(125)
        pane.reverb.set(30)
        pane.changed()
        pane.duration = 10
        pane.set_position(2)
        with patch.object(pane.player, "play") as play:
            pane.preview()
        play.assert_called_once_with(str(source.resolve()), self.app.ffmpeg.get(), 125, 30, 2, duration=25)
        for reverb, expected in ((30, "Sped Up + Reverb"), (0, "Sped Up")):
            pane.reverb.set(reverb)
            with patch("effects_ui.filedialog.asksaveasfilename", return_value="") as dialog:
                pane.export()
            self.assertEqual(dialog.call_args.kwargs["initialfile"], f"Artista - Música - {expected}.mp3")


if __name__ == "__main__":
    unittest.main()
