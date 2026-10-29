"""On-device resolution/FPS conversion with the shipped native binaries."""

import json
from pathlib import Path
import subprocess
import tempfile


def verify(folder):
    from mobile_backend import _native
    from video_limits import enforce_video_limits, video_stream

    with tempfile.TemporaryDirectory(prefix="video-limits-", dir=folder) as directory:
        results = []
        for mode, size in (("mp4", "720x1280"), ("video", "1280x720")):
            source = Path(directory) / (mode + (".mp4" if mode == "mp4" else ".mkv"))
            result = subprocess.run(
                [
                    str(_native / "libffmpeg.so"),
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=blue:s={size}:r=60:d=0.5",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=0.5",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                capture_output=True,
                timeout=60,
            )
            assert result.returncode == 0, result.stderr.decode(errors="replace")
            config = {"mode": mode, "height": 480, "fps": 24}
            assert enforce_video_limits(source, config, lambda *args, **kwargs: None)
            width, height, fps = video_stream(source, config)
            assert min(width, height) == 480 and fps <= 24.01, (width, height, fps)
            before = source.read_bytes()
            assert not enforce_video_limits(
                source, config, lambda *args, **kwargs: None
            )
            assert source.read_bytes() == before
            audio = subprocess.run(
                [
                    str(_native / "libffprobe.so"),
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
                timeout=20,
            )
            assert b"aac" in audio.stdout
            results.append(
                {
                    "mode": mode,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "audio": "aac",
                }
            )
        return json.dumps(results)
