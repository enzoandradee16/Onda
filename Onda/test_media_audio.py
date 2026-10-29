import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from engine import ask_media
from social_media import download_selected, extract_video_audio


class MediaAudioTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'FFmpeg integration')
    def test_direct_and_resolved_video_publish_audio_files(self):
        import functools
        import http.server
        import threading
        import requests
        from social_media import save_media, save_video

        ffmpeg = Path(os.environ['ONDA_FFMPEG'])
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'clip.mp4'
            subprocess.run(
                [
                    str(ffmpeg / 'ffmpeg.exe'),
                    '-v',
                    'error',
                    '-f',
                    'lavfi',
                    '-i',
                    'color=c=black:s=64x64:d=0.3',
                    '-f',
                    'lavfi',
                    '-i',
                    'sine=frequency=440:duration=0.3',
                    '-c:v',
                    'libx264',
                    '-c:a',
                    'aac',
                    '-shortest',
                    str(source),
                ],
                check=True,
                capture_output=True,
            )

            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *_):
                    pass

            server = http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0), functools.partial(Handler, directory=folder)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/clip.mp4'
                config = {
                    'url': url,
                    'folder': str(Path(folder) / 'output'),
                    'mode': 'mp3',
                    'height': None,
                    'fps': None,
                    'ffmpeg': str(ffmpeg),
                }
                metadata = {
                    'extension': 'mp4',
                    'title': 'Clip',
                    'user': 'Artist',
                    '_video_info': {
                        'id': 'clip',
                        'title': 'Clip',
                        'formats': [
                            {
                                'url': url,
                                'ext': 'mp4',
                                'vcodec': 'h264',
                                'acodec': 'aac',
                            }
                        ],
                    },
                }
                with requests.Session() as session:
                    resolved = save_video(session, metadata, config, Mock(), Mock(), 1)
                    direct = save_media(
                        session,
                        url,
                        metadata,
                        dict(config, mode='m4a'),
                        Mock(),
                        Mock(),
                        2,
                    )
                for name, suffix in ((resolved, '.mp3'), (direct, '.m4a')):
                    self.assertEqual(Path(name).suffix, suffix)
                    info = json.loads(
                        subprocess.check_output(
                            [
                                str(ffmpeg / 'ffprobe.exe'),
                                '-v',
                                'error',
                                '-show_streams',
                                '-of',
                                'json',
                                name,
                            ]
                        )
                    )
                    self.assertEqual(
                        [stream['codec_type'] for stream in info['streams']], ['audio']
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_mixed_post_in_photo_mode_offers_video_and_applies_choice(self):
        items = [
            ('https://example.com/1.jpg', {'extension': 'jpg'}),
            (
                'https://example.com/2.mp4',
                {'extension': 'mp4', '_video_info': {'id': 'clip'}},
            ),
        ]
        choose = Mock(return_value={'selected_ids': ['2'], 'media_modes': {'2': 'mp3'}})
        with (
            patch('social_media.save_media') as photo,
            patch('social_media.save_video', return_value='clip.mp3') as video,
        ):
            result = download_selected(
                items, Mock(), {'mode': 'photos'}, Mock(), Mock(), choose
            )
        self.assertEqual(result, ['clip.mp3'])
        self.assertEqual(len(choose.call_args.args[0]), 2)
        self.assertEqual(video.call_args.args[2]['mode'], 'mp3')
        photo.assert_not_called()

    def test_direct_video_audio_choice_and_photo_preserved(self):
        items = [
            ('https://example.com/1.jpg', {'extension': 'jpg'}),
            ('https://example.com/2.mp4', {'extension': 'mp4'}),
        ]
        choose = Mock(
            return_value={'selected_ids': ['1', '2'], 'media_modes': {'2': 'm4a'}}
        )
        with patch('social_media.save_media', return_value='saved') as save:
            download_selected(items, Mock(), {'mode': 'mp4'}, Mock(), Mock(), choose)
        self.assertEqual(save.call_args_list[0].args[3]['mode'], 'photos')
        self.assertEqual(save.call_args_list[1].args[3]['mode'], 'm4a')

    def test_ipc_accepts_only_video_formats_for_selected_videos(self):
        candidates = [{'id': '1', 'kind': 'Foto'}, {'id': '2', 'kind': 'Vídeo'}]
        valid = {'selected_ids': ['2'], 'media_modes': {'2': 'mp3'}}
        with patch('engine.emit'):
            self.assertEqual(
                ask_media(candidates, io.StringIO(json.dumps(valid))), valid
            )
            for value in (
                {'selected_ids': ['1'], 'media_modes': {'1': 'mp3'}},
                {'selected_ids': ['2'], 'media_modes': {'2': 'exe'}},
                {'selected_ids': ['1'], 'media_modes': {'2': 'mp3'}},
            ):
                with self.assertRaises(ValueError):
                    ask_media(candidates, io.StringIO(json.dumps(value)))

    @unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'FFmpeg integration')
    def test_real_video_becomes_audio_only_in_all_audio_formats(self):
        ffmpeg = Path(os.environ['ONDA_FFMPEG'])
        with tempfile.TemporaryDirectory() as folder:
            for mode in ('mp3', 'm4a', 'flac', 'original'):
                source = Path(folder) / (mode + '.mp4')
                subprocess.run(
                    [
                        str(ffmpeg / 'ffmpeg.exe'),
                        '-v',
                        'error',
                        '-f',
                        'lavfi',
                        '-i',
                        'color=c=black:s=64x64:d=0.3',
                        '-f',
                        'lavfi',
                        '-i',
                        'sine=frequency=440:duration=0.3',
                        '-c:v',
                        'libx264',
                        '-c:a',
                        'aac',
                        '-shortest',
                        str(source),
                    ],
                    check=True,
                    capture_output=True,
                )
                target = extract_video_audio(
                    source, {'mode': mode, 'ffmpeg': str(ffmpeg)}, Mock()
                )
                self.assertTrue(target.is_file())
                self.assertFalse(source.exists())
                info = json.loads(
                    subprocess.check_output(
                        [
                            str(ffmpeg / 'ffprobe.exe'),
                            '-v',
                            'error',
                            '-show_streams',
                            '-of',
                            'json',
                            str(target),
                        ]
                    )
                )
                self.assertEqual(
                    [stream['codec_type'] for stream in info['streams']], ['audio']
                )
                self.assertEqual(
                    target.suffix, '.' + ('m4a' if mode == 'original' else mode)
                )


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class MediaAudioUiTests(unittest.TestCase):
    def test_picker_confirms_per_video_output(self):
        import tkinter as tk
        from media_picker import MediaPicker

        root = tk.Tk()
        root.social_cookies = tk.StringVar()
        confirm = Mock()
        picker = MediaPicker(
            root,
            {
                'candidates': [
                    {'id': '1', 'number': 1, 'kind': 'Foto', 'title': 'Photo'},
                    {
                        'id': '2',
                        'number': 2,
                        'kind': 'Vídeo',
                        'title': 'Clip',
                        'default_mode': 'mp3',
                    },
                ]
            },
            confirm,
            Mock(),
        )
        try:
            root.update()
            self.assertEqual(picker.video_modes['2'].get(), 'Só áudio · MP3')
            picker.variables['1'].set(False)
            picker.video_modes['2'].set('Só áudio · M4A')
            picker.accept()
            confirm.assert_called_once_with(
                {'selected_ids': ['2'], 'media_modes': {'2': 'm4a'}}
            )
        finally:
            picker.destroy()
            root.destroy()
