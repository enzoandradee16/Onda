"""Isolated FFmpeg effect render with progress and atomic output publication."""

import json
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from audio_tools import effects_filter, effect_name, executable, process_options
from engine import emit


def preserve_tags(source, output, effect):
    """Keep full native tags for same-format exports, changing only the title."""
    from mutagen import File
    from mutagen.id3 import ID3, TIT2
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.wave import WAVE

    original, rendered = File(source), File(output)
    if rendered is None:
        raise ValueError("Não foi possível gravar os metadados da exportação.")
    original_title = source.stem
    if original is not None and original.tags:
        if isinstance(original.tags, ID3):
            titles = original.tags.getall("TIT2")
            original_title = str(titles[0]) if titles else source.stem
        else:
            title_key = "\u00a9nam" if isinstance(original, MP4) else "title"
            original_title = (original.tags.get(title_key) or [source.stem])[0]
    native_tags = (
        original is not None
        and original.tags is not None
        and (
            type(original) is type(rendered)
            or isinstance(original.tags, ID3)
            and isinstance(rendered, (MP3, WAVE))
        )
    )
    if native_tags:
        if isinstance(original.tags, ID3):
            if rendered.tags is None:
                rendered.add_tags()
            rendered.tags.clear()
            rendered.tags.update(copy.deepcopy(original.tags))
            rendered.tags.unknown_frames = copy.deepcopy(original.tags.unknown_frames)
        else:
            rendered.tags = copy.deepcopy(original.tags)
        if hasattr(original, "pictures"):
            rendered.clear_pictures()
            for picture in original.pictures:
                rendered.add_picture(copy.deepcopy(picture))
    if effect:
        if rendered.tags is None:
            rendered.add_tags()
        if isinstance(rendered.tags, ID3):
            titles = rendered.tags.getall("TIT2")
            title = str(titles[0]) if titles else original_title
            rendered.tags.add(TIT2(encoding=3, text=[title + " - " + effect]))
        elif isinstance(rendered, MP4):
            title = (rendered.tags.get("\u00a9nam") or [original_title])[0]
            rendered.tags["\u00a9nam"] = [title + " - " + effect]
        else:
            title = (rendered.tags.get("title") or [original_title])[0]
            rendered.tags["title"] = [title + " - " + effect]
    if rendered.tags is not None:
        rendered.save()


def render(config):
    temporary = None
    try:
        source, output = (
            Path(config["source"]).resolve(),
            Path(config["output"]).resolve(),
        )
        if not source.is_file() or source == output:
            raise ValueError(
                "Escolha um áudio existente e um arquivo de saída diferente do original."
            )
        mode = output.suffix.lower()
        if mode not in (".mp3", ".m4a", ".flac", ".wav"):
            raise ValueError("Exporte em MP3, M4A, FLAC ou WAV.")
        filters = effects_filter(
            config.get("speed", 100),
            config.get("reverb", 0),
            config.get("keep_pitch", False),
        )
        ffmpeg, ffprobe = (
            executable(name, config.get("ffmpeg", "")) for name in ("ffmpeg", "ffprobe")
        )
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            **process_options(),
        )
        if probe.returncode:
            raise ValueError("Não foi possível ler este áudio.")
        duration = float(json.loads(probe.stdout)["format"]["duration"]) / (
            float(config.get("speed", 100)) / 100
        )
        duration += 2 if config.get("reverb") else 0
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            prefix=".onda-render-", suffix=mode, dir=output.parent
        )
        os.close(fd)
        temporary = Path(name)
        emit("temporary", path=str(temporary))
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-map_metadata",
            "0",
            "-af",
            filters,
        ]
        if mode != ".wav":
            command += [
                "-map",
                "0:v?",
                "-c:v",
                "copy",
                "-disposition:v",
                "attached_pic",
            ]
        command += [
            "-c:a",
            {".mp3": "libmp3lame", ".m4a": "aac", ".flac": "flac", ".wav": "pcm_s16le"}[
                mode
            ],
        ]
        if mode in (".mp3", ".m4a"):
            bitrate = int(config.get("bitrate", 320 if mode == ".mp3" else 256))
            if bitrate not in (96, 128, 192, 256, 320):
                raise ValueError("Bitrate inválido.")
            command += ["-b:a", str(bitrate) + "k"]
        from performance import thread_args, priority_flags

        command[1:1] = thread_args(config)
        command += thread_args(config)
        command += ["-progress", "pipe:1", "-nostats", str(temporary)]
        # Error output in a temporary file avoids stderr/stdout pipe deadlock.
        with tempfile.TemporaryFile() as errors:
            child_options = process_options()
            if os.name == "nt":
                child_options["creationflags"] = child_options.get(
                    "creationflags", 0
                ) | priority_flags(config)
            child_options.pop("start_new_session", None)
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                **child_options,
            ) as process:
                for line in process.stdout:
                    if line.startswith("out_time_us="):
                        try:
                            emit(
                                "progress",
                                percent=min(
                                    99,
                                    float(line.partition("=")[2])
                                    / 1e6
                                    / max(duration, 0.01)
                                    * 100,
                                ),
                            )
                        except ValueError:
                            pass
                if process.wait():
                    errors.seek(0)
                    raise ValueError(
                        "FFmpeg: " + errors.read(4000).decode("utf-8", errors="replace")
                    )
        preserve_tags(
            source,
            temporary,
            effect_name(config.get("speed", 100), config.get("reverb", 0)),
        )
        if config.get('record') or config.get('cover_data') or config.get('cover_url'):
            from effects_export import apply_export_metadata

            apply_export_metadata(temporary, config)
        # Never overwrite a new file created while rendering unless authorized.
        if output.exists() and not config.get("replace"):
            raise ValueError("O arquivo de saída já existe. Escolha outro nome.")
        if config.get("replace"):
            os.replace(temporary, output)
        else:
            # Windows rename fails if the destination was created meanwhile.
            if os.name == "nt":
                os.rename(temporary, output)
            else:
                os.link(temporary, output)
                temporary.unlink()
        emit("done", path=str(output))
        return 0
    except Exception as exc:
        emit("error", message=str(exc))
        return 1
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        config = json.loads(sys.stdin.readline())
    except (ValueError, OSError):
        sys.exit(1)
    sys.exit(render(config))
