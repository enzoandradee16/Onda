"""File and malformed-input regressions found during the cross-platform audit."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from image_output import transform_image
from silence import detect


class ProjectAuditTests(unittest.TestCase):
    def test_quality_encoder_preserves_existing_neighbors(self):
        from audio_quality import AudioQualityPP

        for mode in ('mp3', 'm4a'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'song.mp3'
                source.write_bytes(b'original')
                temporary = source.with_name('song.encoding.' + mode)
                temporary.write_bytes(b'unrelated temp')
                existing = source.with_suffix('.' + mode)
                if existing != source:
                    existing.write_bytes(b'unrelated audio')
                processor = AudioQualityPP(None, '128', mode)

                def render(source, target, args):
                    Path(target).write_bytes(b'encoded')

                with patch.object(processor, 'run_ffmpeg', side_effect=render):
                    deleted, result = processor.run({'filepath': str(source)})
                self.assertEqual(temporary.read_bytes(), b'unrelated temp')
                self.assertEqual(Path(result['filepath']).read_bytes(), b'encoded')
                if existing != source:
                    self.assertEqual(existing.read_bytes(), b'unrelated audio')
                    self.assertEqual(deleted, [str(source)])

    def test_photo_video_preserves_existing_neighbors(self):
        from photo_music import render_photo_video

        with tempfile.TemporaryDirectory() as directory:
            photo = Path(directory) / 'photo.jpg'
            Image.new('RGB', (20, 10), 'red').save(photo)
            neighbors = [
                photo.with_suffix('.mp4'),
                photo.with_suffix('.render.mp4'),
                photo.with_suffix('.jpg.soundtrack'),
            ]
            for path in neighbors:
                path.write_bytes(b'unrelated media')
            response = Mock(
                headers={'Content-Type': 'audio/mpeg', 'Content-Length': '5'}
            )
            response.iter_content.return_value = [b'audio']
            session = Mock()
            session.get.return_value.__enter__ = Mock(return_value=response)
            session.get.return_value.__exit__ = Mock(return_value=False)

            def render(command, **kwargs):
                Path(command[-1]).write_bytes(b'video')
                return Mock(returncode=0)

            with (
                patch('audio_tools.executable', return_value='ffmpeg'),
                patch('photo_music.subprocess.run', side_effect=render),
            ):
                output = render_photo_video(
                    photo,
                    {'url': 'https://example.com/music.mp3'},
                    session,
                    {},
                    {},
                    Mock(),
                )
            self.assertEqual(output.read_bytes(), b'video')
            self.assertFalse(photo.exists())
            for path in neighbors:
                self.assertEqual(path.read_bytes(), b'unrelated media')

    def test_image_conversion_preserves_neighboring_temporary_and_output_files(self):
        for fmt, ext in (('JPG', '.jpg'), ('PNG', '.png'), ('SVG', '.svg')):
            with self.subTest(format=fmt), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'photo.webp'
                Image.new('RGB', (20, 10), 'red').save(source)
                final = source.with_suffix(ext)
                temporary = source.with_name('photo.converted' + ext)
                final.write_bytes(b'existing image')
                temporary.write_bytes(b'unrelated file')
                output = transform_image(
                    source, {'format': fmt, 'width': 0, 'height': 0, 'keep_ratio': True}
                )
                self.assertEqual(final.read_bytes(), b'existing image')
                self.assertEqual(temporary.read_bytes(), b'unrelated file')
                self.assertNotEqual(output, final)
                self.assertTrue(output.is_file())

    def test_failed_image_encoding_removes_temporary_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'photo.png'
            Image.new('RGB', (20, 10), 'red').save(source)
            original = source.read_bytes()

            def broken(image, path, **kwargs):
                Path(path).write_bytes(b'partial')
                raise OSError('disk full')

            with patch.object(Image.Image, 'save', broken):
                with self.assertRaises(OSError):
                    transform_image(source, {'format': 'JPG'})
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [source])

    def test_silence_rejects_nonfinite_duration_before_spawning_ffmpeg(self):
        for duration in ('nan', 'inf', '-inf'):
            with (
                self.subTest(duration=duration),
                tempfile.TemporaryDirectory() as directory,
            ):
                source = Path(directory) / 'audio.wav'
                source.write_bytes(b'audio')
                result = Mock(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            'format': {'duration': duration},
                            'streams': [{'codec_type': 'audio'}],
                        }
                    ),
                )
                with (
                    patch('silence.executable', return_value='ffprobe'),
                    patch('silence.subprocess.run', return_value=result),
                    patch('silence.subprocess.Popen') as process,
                ):
                    with self.assertRaises(ValueError):
                        detect(source)
                    process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
