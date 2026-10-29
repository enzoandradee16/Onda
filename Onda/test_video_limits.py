"""Real yt-dlp selection and FFmpeg reduction for social and standard sources."""

import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from yt_dlp import YoutubeDL
from engine import build_options, HEIGHTS, FPS_OPTIONS
from video_limits import enforce_video_limits, limit_filters, video_stream


class VideoSelectionTests(unittest.TestCase):
    def select(self, formats, height, fps, mode="mp4", platform="test"):
        options = build_options(
            {"mode": mode, "folder": ".", "height": height, "fps": fps}
        )
        options.update(quiet=True, skip_download=True, logger=Mock())
        info = {
            "id": "fixture",
            "title": "Fixture",
            "extractor": platform,
            "formats": copy.deepcopy(formats),
        }
        with YoutubeDL(options) as downloader:
            return downloader.process_ie_result(info, download=False)

    def test_single_vertical_landscape_and_unknown_sources_never_disappear(self):
        scenarios = {
            "Kwai": [
                {
                    "url": "https://cdn.example/kwai.mp4",
                    "width": 720,
                    "height": 1280,
                    "fps": 30,
                }
            ],
            "Instagram": [
                {
                    "url": "https://cdn.example/ig.mp4",
                    "width": 1080,
                    "height": 1920,
                    "fps": 60,
                }
            ],
            "TikTok": [{"url": "https://cdn.example/tiktok.mp4"}],
            "Youtube": [
                {
                    "url": "https://cdn.example/yt.mp4",
                    "width": 1920,
                    "height": 1080,
                    "fps": 60,
                }
            ],
        }
        for platform, formats in scenarios.items():
            for fmt in formats:
                fmt.update(format_id="original", ext="mp4", vcodec="h264", acodec="aac")
            for height in HEIGHTS.values():
                for fps in FPS_OPTIONS.values():
                    for mode in ("mp4", "video"):
                        with self.subTest(
                            platform=platform, height=height, fps=fps, mode=mode
                        ):
                            result = self.select(formats, height, fps, mode, platform)
                            self.assertEqual(result["format_id"], "original")

    def test_silent_video_does_not_require_an_audio_stream(self):
        formats = [
            dict(
                url="https://cdn.example/silent.mp4",
                format_id="silent",
                ext="mp4",
                width=1080,
                height=1920,
                fps=60,
                vcodec="h264",
                acodec="none",
            )
        ]
        self.assertEqual(self.select(formats, 480, 24)["format_id"], "silent")

    def test_native_compatible_stream_is_preferred_to_larger_source(self):
        formats = [
            dict(
                url="https://cdn.example/a.mp4",
                format_id="720",
                ext="mp4",
                width=720,
                height=1280,
                fps=30,
                vcodec="h264",
                acodec="aac",
            ),
            dict(
                url="https://cdn.example/b.mp4",
                format_id="1080",
                ext="mp4",
                width=1080,
                height=1920,
                fps=60,
                vcodec="h264",
                acodec="aac",
            ),
        ]
        self.assertEqual(self.select(formats, 720, 30)["format_id"], "720")

    def test_short_side_and_lower_frame_rate_do_not_upscale(self):
        self.assertEqual(limit_filters(480, 854, 24, 720, 30), [])
        self.assertEqual(limit_filters(1280, 720, 30, 720, 30), [])
        self.assertEqual(
            limit_filters(1080, 1920, 60, 480, 24),
            ["scale=480:852", "fps=fps='min(source_fps,24)'"],
        )


@unittest.skipUnless(
    os.environ.get("ONDA_FFMPEG"), "Set ONDA_FFMPEG for real conversion tests"
)
class VideoConversionTests(unittest.TestCase):
    def test_real_conversion_limits_dimensions_fps_and_preserves_audio(self):
        folder = os.environ["ONDA_FFMPEG"]
        ffmpeg = str(Path(folder) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
        with tempfile.TemporaryDirectory() as temporary:
            for dimensions, mode, fps in (
                ("720x1280", "mp4", 24),
                ("1280x720", "video", 30),
            ):
                with self.subTest(dimensions=dimensions, mode=mode):
                    source = Path(temporary) / (
                        mode + (".mp4" if mode == "mp4" else ".mkv")
                    )
                    subprocess.run(
                        [
                            ffmpeg,
                            "-v",
                            "error",
                            "-f",
                            "lavfi",
                            "-i",
                            f"color=c=blue:s={dimensions}:r=60:d=0.7",
                            "-f",
                            "lavfi",
                            "-i",
                            "sine=frequency=440:duration=0.7",
                            "-c:v",
                            "libx264",
                            "-preset",
                            "ultrafast",
                            "-c:a",
                            "aac",
                            "-shortest",
                            str(source),
                        ],
                        check=True,
                        capture_output=True,
                    )
                    config = {"mode": mode, "height": 480, "fps": fps, "ffmpeg": folder}
                    self.assertTrue(enforce_video_limits(source, config, Mock()))
                    width, height, rate = video_stream(source, config)
                    self.assertEqual(min(width, height), 480)
                    self.assertLessEqual(rate, fps + 0.01)
                    from audio_tools import executable

                    audio = subprocess.run(
                        [
                            executable("ffprobe", folder),
                            "-v",
                            "error",
                            "-select_streams",
                            "a:0",
                            "-show_entries",
                            "stream=codec_name",
                            "-of",
                            "csv=p=0",
                            str(source),
                        ],
                        capture_output=True,
                        check=True,
                    )
                    self.assertIn(b"aac", audio.stdout)
                    before = source.read_bytes()
                    self.assertFalse(enforce_video_limits(source, config, Mock()))
                    self.assertEqual(before, source.read_bytes())

    def test_conversion_failure_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "video.mp4"
            source.write_bytes(b"original")
            with (
                patch("video_limits.video_stream", return_value=(1080, 1920, 60)),
                patch(
                    "subprocess.run",
                    return_value=Mock(returncode=1, stderr=b"conversion failed"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "não foi publicado"):
                    enforce_video_limits(
                        source,
                        {
                            "mode": "mp4",
                            "height": 480,
                            "ffmpeg": os.environ["ONDA_FFMPEG"],
                        },
                        Mock(),
                    )
            self.assertEqual(source.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
