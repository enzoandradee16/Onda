"""Honor video ceilings when a platform only exposes a larger/faster source."""

import json
import math
from pathlib import Path
import subprocess
import tempfile
from fractions import Fraction


def video_stream(path, config):
    from audio_tools import executable, process_options

    result = subprocess.run(
        [
            executable("ffprobe", config.get("ffmpeg", "")),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        timeout=40,
        **process_options(),
    )
    if result.returncode:
        raise ValueError("Não foi possível conferir a resolução e o FPS do vídeo.")
    streams = json.loads(result.stdout).get("streams") or []
    if not streams:
        raise ValueError("O arquivo baixado não contém uma faixa de vídeo válida.")
    stream = streams[0]
    try:
        rate = float(Fraction(stream.get("avg_frame_rate") or "0"))
        if rate <= 0:
            rate = float(Fraction(stream.get("r_frame_rate") or "0"))
    except (ValueError, ZeroDivisionError):
        rate = 0
    return int(stream.get("width") or 0), int(stream.get("height") or 0), rate


def limit_filters(width, height, rate, resolution=None, fps=None):
    filters = []
    if resolution and width > 0 and height > 0 and min(width, height) > resolution:
        ratio = resolution / min(width, height)
        target_width = max(2, math.floor(width * ratio / 2) * 2)
        target_height = max(2, math.floor(height * ratio / 2) * 2)
        filters.append(f"scale={target_width}:{target_height}")
    if fps and (not rate or rate > fps + 0.01):
        # Never duplicate frames to increase a source's frame rate.
        filters.append(f"fps=fps='min(source_fps,{fps})'")
    return filters


def enforce_video_limits(path, config, emit):
    if config.get("mode") not in ("mp4", "video") or not (
        config.get("height") or config.get("fps")
    ):
        return False
    from audio_tools import executable, process_options

    source = Path(path)
    width, height, rate = video_stream(source, config)
    filters = limit_filters(
        width, height, rate, config.get("height"), config.get("fps")
    )
    if not filters:
        return False
    emit(
        "stage",
        message="A fonte não oferece a qualidade pedida. Ajustando resolução/FPS do vídeo…",
    )
    emit(
        "log",
        message=f"Fonte: {width} × {height}, {rate:g} fps. Redução para os limites escolhidos; sem ampliar.",
    )
    with tempfile.TemporaryDirectory(
        prefix=".onda-video-", dir=source.parent
    ) as folder:
        target = Path(folder) / source.name
        command = [
            executable("ffmpeg", config.get("ffmpeg", "")),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-map_metadata",
            "0",
            "-vf",
            ",".join(filters),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
        ]
        from performance import thread_args

        command[1:1] = thread_args(config)
        command += thread_args(config)
        if source.suffix.lower() == ".mp4":
            command += ["-movflags", "+faststart"]
        result = subprocess.run(
            command + [str(target)], capture_output=True, **process_options()
        )
        if result.returncode or not target.is_file() or not target.stat().st_size:
            detail = result.stderr.decode("utf-8", errors="replace")[-1500:]
            raise ValueError(
                "Não foi possível ajustar a resolução/FPS. O arquivo não foi publicado. "
                + detail
            )
        out_width, out_height, out_rate = video_stream(target, config)
        if (config.get("height") and min(out_width, out_height) > config["height"]) or (
            config.get("fps") and out_rate > config["fps"] + 0.01
        ):
            raise ValueError(
                "O vídeo convertido excedeu os limites escolhidos; o arquivo não foi publicado."
            )
        target.replace(source)
    return True
