import unittest

from engine import build_options
from preferences import PreferenceStore
from size_estimate import estimate_size


class SizeAndFpsTests(unittest.TestCase):
    def test_audio_estimate_respects_quality_and_cover(self):
        for mode in ("mp3", "m4a"):
            low, _ = estimate_size(
                {"duration": 180}, {"mode": mode, "audio_quality": "128 kbps"}, 50000
            )
            high, _ = estimate_size(
                {"duration": 180}, {"mode": mode, "audio_quality": "192 kbps"}, 50000
            )
            self.assertEqual(low, int(180 * 128000 / 8 * 1.02 + 50000 + 8192))
            self.assertGreater(high, low)

    def test_video_sums_only_selected_video_and_audio(self):
        info = {
            "requested_formats": [{"filesize": 1000000}, {"filesize_approx": 100000}],
            "formats": [{"filesize": 99999999}],
        }
        size, _ = estimate_size(info, {"mode": "video"})
        self.assertEqual(size, 1111000)

    def test_original_bitrate_fallback(self):
        size, _ = estimate_size({"duration": 120, "abr": 128}, {"mode": "original"})
        self.assertEqual(size, int(120 * 128000 / 8 * 1.01))

    def test_missing_data_and_flac_are_unknown(self):
        for mode in ("mp3", "video", "original", "flac"):
            self.assertIsNone(estimate_size({}, {"mode": mode})[0])
        self.assertIsNone(
            estimate_size({"duration": 180, "filesize": 1000000}, {"mode": "flac"})[0]
        )

    def test_fps_applies_to_both_video_fallbacks(self):
        config = {"mode": "video", "folder": ".", "height": 720, "fps": 30}
        options = build_options(config)
        self.assertTrue(
            options["format"].startswith(
                "bestvideo[height<=?720][fps<=?30]+bestaudio/best[height<=?720][fps<=?30]"
            )
        )
        self.assertIn("best[width<=?720][fps<=?30]", options["format"])
        original = build_options({**config, "fps": None})
        self.assertNotIn("fps", original["format"])
        self.assertEqual(options["outtmpl"], original["outtmpl"])
        with self.assertRaises(ValueError):
            build_options({**config, "fps": 17})

    def test_fps_preferences_validate_labels(self):
        self.assertEqual(
            PreferenceStore.clean({"fps": "60 fps"}),
            {'confirm_version': False, "fps": "60 fps"},
        )
        self.assertNotIn("fps", PreferenceStore.clean({"fps": "999 fps"}))
