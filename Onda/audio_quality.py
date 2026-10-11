"""Encode audio at the requested bitrate, even when source and target codecs match."""
import os
from pathlib import Path
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor


class AudioQualityPP(FFmpegPostProcessor):
    def __init__(self, downloader, bitrate, mode="m4a"):
        super().__init__(downloader)
        self.bitrate = bitrate
        self.mode = mode

    def run(self, info):
        source = Path(info["filepath"])
        target = source.with_suffix("." + self.mode)
        temporary = target.with_name(target.stem + ".encoding." + self.mode)
        try:
            codec = "libmp3lame" if self.mode == "mp3" else "aac"
            self.run_ffmpeg(str(source), str(temporary), ["-vn", "-c:a", codec, "-b:a", self.bitrate + "k"])
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        info["filepath"], info["ext"] = str(target), self.mode
        return ([str(source)] if source != target else []), info


AACQualityPP = AudioQualityPP
