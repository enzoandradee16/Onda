"""Encode audio at the requested bitrate, even when source and target codecs match."""
import os
import tempfile
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
        with tempfile.TemporaryDirectory(prefix='.onda-encode-',dir=source.parent) as directory:
            temporary = Path(directory) / target.name
            codec = "libmp3lame" if self.mode == "mp3" else "aac"
            self.run_ffmpeg(str(source), str(temporary), ["-vn", "-c:a", codec, "-b:a", self.bitrate + "k"])
            if source == target:
                os.replace(temporary, target)
            else:
                from file_output import publish
                final, _ = publish(temporary, source.parent, 'keep')
                target = Path(final)
        info["filepath"], info["ext"] = str(target), self.mode
        return ([str(source)] if source != target else []), info


AACQualityPP = AudioQualityPP
