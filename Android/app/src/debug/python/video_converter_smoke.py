import tempfile, subprocess, json
from pathlib import Path
from audio_tools import executable
from video_converter import convert_video


def verify(folder):
    with tempfile.TemporaryDirectory(dir=folder) as root:
        source = Path(root) / 'original.mkv'
        subprocess.run(
            [
                executable('ffmpeg'),
                '-v',
                'error',
                '-f',
                'lavfi',
                '-i',
                'testsrc2=size=160x90:rate=10:duration=1',
                '-f',
                'lavfi',
                '-i',
                'sine=duration=1',
                '-c:v',
                'libx264',
                '-pix_fmt',
                'yuv420p',
                '-c:a',
                'aac',
                '-shortest',
                str(source),
            ],
            check=True,
            capture_output=True,
        )
        original = source.read_bytes()
        modes = []
        for mode in ('MP4', 'MKV', 'MOV'):
            result = convert_video(
                dict(
                    source=str(source),
                    output=str(Path(root) / ('out.' + mode.lower())),
                    video_format=mode,
                    video_resolution='720p',
                    video_bitrate='1000k',
                    audio_bitrate='96k',
                    video_fps='24',
                    video_audio='Sem áudio',
                )
            )
            assert result['width'] == 160 and result['height'] == 90
            streams = json.loads(
                subprocess.run(
                    [
                        executable('ffprobe'),
                        '-v',
                        'error',
                        '-show_streams',
                        '-of',
                        'json',
                        result['path'],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            )['streams']
            assert not any(v['codec_type'] == 'audio' for v in streams)
            assert (
                next(v for v in streams if v['codec_type'] == 'video')['avg_frame_rate']
                == '24/1'
            )
            modes.append(mode)
        for mode in ('MP3', 'M4A', 'AAC'):
            result = convert_video(
                dict(
                    source=str(source),
                    output=str(Path(root) / ('audio.' + mode.lower())),
                    video_format=mode,
                    audio_bitrate='128k',
                )
            )
            streams = json.loads(
                subprocess.run(
                    [
                        executable('ffprobe'),
                        '-v',
                        'error',
                        '-show_streams',
                        '-of',
                        'json',
                        result['path'],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            )['streams']
            assert [s['codec_type'] for s in streams] == ['audio']
        assert source.read_bytes() == original
        return json.dumps(
            {'success': True, 'formats': modes, 'original_preserved': True}
        )
