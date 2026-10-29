from pathlib import Path
import subprocess
import tempfile
import unittest
from video_converter import convert_video, probe_video, ConversionCancelled, FORMATS
from ffmpeg_runtime import existing_folder


class VideoConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = existing_folder()
        if not cls.folder:
            raise unittest.SkipTest('FFmpeg unavailable')

    def fixture(self, root, audio=True):
        source = Path(root) / 'original.mkv'
        command = [
            str(self.folder / 'ffmpeg.exe'),
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'testsrc2=size=322x242:rate=12:duration=1',
        ]
        if audio:
            command += ['-f', 'lavfi', '-i', 'sine=frequency=440:duration=1']
        command += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p']
        if audio:
            command += ['-c:a', 'aac', '-shortest']
        subprocess.run(command + [str(source)], check=True, capture_output=True)
        return source

    def test_real_conversion_formats_silent_inputs_and_no_upscaling(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root)
            before = source.read_bytes()
            for mode in FORMATS:
                output = Path(root) / ('result.' + mode.lower())
                events = []
                result = convert_video(
                    dict(
                        source=str(source),
                        output=str(output),
                        ffmpeg=str(self.folder),
                        video_format=mode,
                        video_resolution='720p',
                    ),
                    lambda kind, **v: events.append((kind, v)),
                )
                self.assertTrue(output.is_file())
                self.assertLessEqual(result['width'], 322)
                self.assertLessEqual(result['height'], 242)
                self.assertEqual(events[-1], ('progress', {'percent': 100}))
            self.assertEqual(source.read_bytes(), before)
        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root, False)
            result = convert_video(
                dict(
                    source=str(source),
                    output=str(Path(root) / 'silent.mp4'),
                    ffmpeg=str(self.folder),
                )
            )
            self.assertGreater(result['duration'], 0)

    def test_audio_exports_and_silent_video_rejection(self):
        import json

        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root)
            before = source.read_bytes()
            for mode in ('MP3', 'M4A', 'AAC'):
                target = Path(root) / ('audio.' + mode.lower())
                convert_video(
                    dict(
                        source=str(source),
                        output=str(target),
                        ffmpeg=str(self.folder),
                        video_format=mode,
                        audio_bitrate='128k',
                        video_audio='Sem áudio',
                    )
                )
                streams = json.loads(
                    subprocess.run(
                        [
                            str(self.folder / 'ffprobe.exe'),
                            '-v',
                            'error',
                            '-show_streams',
                            '-of',
                            'json',
                            str(target),
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout
                )['streams']
                self.assertEqual([v['codec_type'] for v in streams], ['audio'])
                self.assertGreater(int(streams[0]['bit_rate']), 0)
            self.assertEqual(source.read_bytes(), before)
        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root, False)
            target = Path(root) / 'silent.mp3'
            with self.assertRaisesRegex(ValueError, 'não contém áudio'):
                convert_video(
                    dict(
                        source=str(source),
                        output=str(target),
                        ffmpeg=str(self.folder),
                        video_format='MP3',
                    )
                )
            self.assertFalse(target.exists())

    def test_bitrate_fps_and_audio_removal_are_applied(self):
        import json

        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root)
            for audio in ('Manter áudio', 'Sem áudio'):
                output = Path(root) / (audio + '.mp4')
                config = dict(
                    source=str(source),
                    output=str(output),
                    ffmpeg=str(self.folder),
                    video_bitrate='1000k',
                    audio_bitrate='96k',
                    video_fps='24',
                    video_audio=audio,
                )
                convert_video(config)
                result = subprocess.run(
                    [
                        str(self.folder / 'ffprobe.exe'),
                        '-v',
                        'error',
                        '-show_streams',
                        '-of',
                        'json',
                        str(output),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                streams = json.loads(result.stdout)['streams']
                video = next(v for v in streams if v['codec_type'] == 'video')
                self.assertEqual(video['avg_frame_rate'], '24/1')
                self.assertEqual(
                    any(v['codec_type'] == 'audio' for v in streams),
                    audio == 'Manter áudio',
                )
                self.assertGreater(int(video['bit_rate']), 0)
            for key in ('video_bitrate', 'audio_bitrate', 'video_fps', 'video_audio'):
                with self.assertRaises(ValueError):
                    convert_video(dict(config, **{key: 'invalid'}))

    def test_original_existing_output_and_invalid_options_are_protected(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root)
            output = Path(root) / 'keep.mp4'
            output.write_bytes(b'keep')
            for config in [
                dict(output=str(source)),
                dict(output=str(output)),
                dict(output=str(Path(root) / 'new.mp4'), video_format='BAD'),
            ]:
                with self.assertRaises(ValueError):
                    convert_video(
                        dict(source=str(source), ffmpeg=str(self.folder), **config)
                    )
            self.assertEqual(output.read_bytes(), b'keep')

    def test_cancel_during_render_removes_partial_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as root:
            source = self.fixture(root)
            before = source.read_bytes()
            output = Path(root) / 'cancel.mp4'
            cancel = [False]

            def event(kind, **values):
                if kind == 'stage':
                    cancel[0] = True

            with self.assertRaises(ConversionCancelled):
                convert_video(
                    dict(
                        source=str(source), output=str(output), ffmpeg=str(self.folder)
                    ),
                    event,
                    lambda: cancel[0],
                )
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(list(Path(root).glob('.onda-convert-*')))

    def test_invalid_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'broken.mp4'
            source.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                probe_video(source, str(self.folder))
