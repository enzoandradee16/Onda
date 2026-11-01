"""Verify photo soundtrack conversion on-device with local synthetic media."""

import functools
import http.server
import json
from pathlib import Path
import subprocess
import tempfile
import threading


def verify(folder):
    from PIL import Image
    from mobile_backend import _native
    from photo_music import direct_audio
    from social_media import download_post, session_for
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(prefix='photo-music-test-', dir=folder) as tmp:
        root = Path(tmp)
        photo = root / 'photo.png'
        Image.new('RGB', (161, 123), 'blue').save(photo)
        original = photo.read_bytes()
        song = root / 'song.wav'
        subprocess.run(
            [
                str(_native / 'libffmpeg.so'),
                '-y',
                '-v',
                'error',
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=440:duration=2',
                str(song),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(Handler, directory=tmp)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}'
            audio = direct_audio(url + '/song.wav', start=0.5, duration=1)
            items = [
                (url + '/photo.png', dict(extension='png', num=i, _photo_audio=audio))
                for i in (1, 2)
            ]
            config = dict(
                url='https://www.instagram.com/p/onda-test/',
                mode='social',
                social_best_quality=True,
                folder=str(root / 'out'),
                ffmpeg=str(_native),
            )
            seen = []

            def choose(candidates):
                assert all(
                    row['photo_choice'] and row['has_audio'] for row in candidates
                )
                assert all(row['automatic_quality'] for row in candidates)
                seen.extend(candidates)
                return dict(selected_ids=['1', '2'], media_modes={'1': 'photo_video'})

            with session_for() as session:
                from social_media import download_selected

                def download(config, emit, duplicate, picker):
                    return download_selected(
                        items, session, config, emit, duplicate, picker
                    )

                with patch('social_media._download_post', side_effect=download):
                    outputs = download_post(config, lambda *a, **k: None, None, choose)
            assert len(seen) == 2
            assert sorted(Path(p).suffix for p in outputs) == ['.mp4', '.png']
            video = next(p for p in outputs if p.endswith('.mp4'))
            info = json.loads(
                subprocess.check_output(
                    [
                        str(_native / 'libffprobe.so'),
                        '-v',
                        'error',
                        '-show_streams',
                        '-show_format',
                        '-of',
                        'json',
                        video,
                    ],
                    timeout=30,
                )
            )
            assert {s['codec_type'] for s in info['streams']} == {'video', 'audio'}
            duration = float(info['format']['duration'])
            assert abs(duration - 1) < 0.3, duration
            assert photo.read_bytes() == original
            assert not (root / 'out' / '.onda-work').exists()
            return json.dumps(
                dict(
                    ok=True,
                    photos=2,
                    videos=1,
                    separate_photos=1,
                    audio=True,
                    duration=duration,
                    original_preserved=True,
                )
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
