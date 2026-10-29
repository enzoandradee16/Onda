import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from engine import ask_version, build_options, audio_bitrate
from preferences import PreferenceStore


class ChoiceTests(unittest.TestCase):
    def test_choice_uses_selected_candidate_and_rejects_unknown(self):
        candidates = [
            {"id": "aaaaaaaaaaa", "title": "A"},
            {"id": "bbbbbbbbbbb", "title": "B"},
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            selected = ask_version(
                {"title": "Song"},
                candidates,
                io.StringIO('{"selected_id":"bbbbbbbbbbb"}\n'),
            )
        self.assertEqual(selected["title"], "B")
        self.assertEqual(selected["selection"], "user")
        self.assertEqual(json.loads(output.getvalue())["type"], "choose_version")
        for reply in ('{"selected_id":"unknown"}', '', 'null'):
            with (
                self.subTest(reply=reply),
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(ValueError),
            ):
                ask_version({"title": "Song"}, candidates, io.StringIO(reply))

    def test_quality_options_and_clean_output_names(self):
        config = {"mode": "mp3", "folder": ".", "audio_quality": "128 kbps"}
        low = build_options(config)
        high = build_options({**config, "audio_quality": "320 kbps"})
        self.assertEqual(audio_bitrate(config), "128")
        self.assertEqual(low["outtmpl"], high["outtmpl"])
        self.assertNotIn("kbps", low["outtmpl"]["default"])
        self.assertNotIn("%(id)", low["outtmpl"]["default"])
        named = build_options(
            {**config, "output_artist": "Room 5", "output_title": "Make Luv"}
        )
        self.assertEqual(named["outtmpl"]["default"], "Room 5 - Make Luv.%(ext)s")
        with self.assertRaises(ValueError):
            build_options({**config, "audio_quality": "999 kbps"})

    def test_preferences_include_only_valid_audio_qualities(self):
        cleaned = PreferenceStore.clean(
            {
                "mp3_quality": "192 kbps",
                "m4a_quality": "96 kbps",
                "client_secret": "private",
            }
        )
        self.assertEqual(
            cleaned,
            {
                'confirm_version': False,
                "mp3_quality": "192 kbps",
                "m4a_quality": "96 kbps",
            },
        )

    @unittest.skipUnless(os.environ.get("ONDA_FFMPEG"), "Requires FFmpeg")
    def test_aac_source_is_reencoded_at_requested_quality(self):
        from yt_dlp import YoutubeDL
        from audio_quality import AACQualityPP

        root = Path(os.environ["ONDA_FFMPEG"])
        ffmpeg = str(root / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
        ffprobe = str(root / ("ffprobe.exe" if os.name == "nt" else "ffprobe"))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "noise.m4a"
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "anoisesrc=color=pink:r=44100:d=4",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "256k",
                    str(source),
                ],
                check=True,
            )
            with YoutubeDL({"quiet": True, "ffmpeg_location": str(root)}) as ydl:
                _, info = AACQualityPP(ydl, "96").run(
                    {"filepath": str(source), "ext": "m4a"}
                )
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=bit_rate",
                    "-of",
                    "json",
                    info["filepath"],
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            bitrate = int(json.loads(result.stdout)["streams"][0]["bit_rate"])
            self.assertTrue(75000 < bitrate < 125000, bitrate)
            from audio_quality import AudioQualityPP

            source_mp3 = Path(directory) / "noise.mp3"
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-i",
                    str(source),
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "320k",
                    str(source_mp3),
                ],
                check=True,
            )
            with YoutubeDL({"quiet": True, "ffmpeg_location": str(root)}) as ydl:
                AudioQualityPP(ydl, "128", "mp3").run(
                    {"filepath": str(source_mp3), "ext": "mp3"}
                )
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=bit_rate",
                    "-of",
                    "json",
                    str(source_mp3),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(
                int(json.loads(result.stdout)["streams"][0]["bit_rate"]), 128000
            )


if __name__ == "__main__":
    unittest.main()
