"""On-device integration tests using synthetic media, never user files."""

import functools
import http.server
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import shutil

_fixture = None


def start_fixture(folder):
    global _fixture
    from mobile_backend import _native

    root = Path(tempfile.mkdtemp(prefix='service-test-', dir=folder))
    result = subprocess.run(
        [
            str(_native / 'libffmpeg.so'),
            '-y',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'color=c=blue:s=160x120:d=2',
            '-f',
            'lavfi',
            '-i',
            'sine=frequency=440:duration=2',
            '-c:v',
            'libx264',
            '-c:a',
            'aac',
            '-shortest',
            str(root / 'fixture.mp4'),
        ],
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode(errors='replace')

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(Handler, directory=str(root))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _fixture = (root, server)
    return json.dumps(
        {
            'url': f'http://127.0.0.1:{server.server_port}/fixture.mp4',
            'folder': str(root / 'output'),
        }
    )


def stop_fixture():
    global _fixture
    if _fixture:
        root, server = _fixture
        server.shutdown()
        server.server_close()
        shutil.rmtree(root, ignore_errors=True)
        _fixture = None


from mobile_backend import _native, run


def verify(folder, callback):
    events = []
    original_callback = callback

    class Recorder:
        def onEvent(self, value):
            events.append(json.loads(value))
            original_callback.onEvent(value)

    callback = Recorder()
    from PIL import Image
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
    from audio_tools import effects_filter, effect_name
    from image_output import transform_image
    from playlist_files import load_csv, export_text
    from playlist_import import load_text
    from media_selection import validate_selection

    root = Path(tempfile.mkdtemp(prefix='mobile-test-', dir=folder))
    native = json.loads(run('test-native', 'self_test', '{}', callback))
    assert 'error' not in native, native
    source = root / 'Artista - Música.mp3'
    video = root / 'video.mp4'

    def command(args):
        result = subprocess.run(
            [str(_native / 'libffmpeg.so'), '-y', '-v', 'error', *args],
            capture_output=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr.decode(errors='replace')

    command(
        [
            '-f',
            'lavfi',
            '-i',
            'sine=frequency=440:duration=3',
            '-c:a',
            'libmp3lame',
            str(source),
        ]
    )
    cover = io.BytesIO()
    Image.new('RGB', (200, 100), (10, 90, 150)).save(cover, format='JPEG')
    tags = ID3(source)
    tags.add(TIT2(encoding=3, text=['Música']))
    tags.add(TPE1(encoding=3, text=['Artista']))
    tags.add(TALB(encoding=3, text=['Álbum']))
    tags.add(
        APIC(encoding=3, mime='image/jpeg', type=3, desc='Capa', data=cover.getvalue())
    )
    tags.save(source)
    output = root / 'Artista - Música - Slowed + Reverb.mp3'
    config = {
        'source': str(source),
        'output': str(output),
        'speed': 90,
        'reverb': 20,
        'keep_pitch': True,
        'ffmpeg': 'android-native',
    }
    effects = json.loads(run('test-effects', 'effects', json.dumps(config), callback))
    assert effects.get('code') == 0, (effects, events[-5:])
    rendered = ID3(output)
    assert str(rendered['TIT2']) == 'Música - Slowed + Reverb'
    assert str(rendered['TPE1']) == 'Artista' and str(rendered['TALB']) == 'Álbum'
    assert rendered.getall('APIC')[0].data == cover.getvalue()
    preview = json.loads(
        run(
            'test-preview',
            'preview',
            json.dumps(dict(config, start=1, duration=10)),
            callback,
        )
    )
    assert (
        'error' not in preview and Path(preview['path']).stat().st_size > 100
    ), preview
    assert effect_name(120, 0) == 'Sped Up' and effect_name(100, 10) == 'Reverb'
    assert effects_filter(120, 0, True) == 'atempo=1.2'
    photo = root / 'image.jpg'
    photo.write_bytes(cover.getvalue())
    for fmt in ('PNG', 'WebP', 'SVG'):
        photo.write_bytes(cover.getvalue())
        converted = transform_image(
            photo, {'format': fmt, 'width': 100, 'height': 100, 'keep_ratio': True}
        )
        assert Path(converted).is_file()
    photo.write_bytes(cover.getvalue())
    rows = load_text('https://www.youtube.com/watch?v=BaW_jenozKc\n')['tracks']
    csv = load_csv(
        'Track URI,Track Name,Artist Name(s)\nspotify:track:6xXEw4y39shgIp6pacKQFH,Música,Artista\n'
    )
    assert len(rows) == 1 and len(csv['tracks']) == 1
    assert export_text(rows, m3u=True).startswith('#EXTM3U\n')
    assert validate_selection(
        {'selected_ids': ['1'], 'media_modes': {'1': 'mp3'}},
        [{'id': '1', 'kind': 'Vídeo'}],
    ) == (['1'], {'1': 'mp3'})
    command(
        [
            '-f',
            'lavfi',
            '-i',
            'color=c=blue:s=160x120:d=2',
            '-f',
            'lavfi',
            '-i',
            'sine=frequency=440:duration=2',
            '-c:v',
            'libx264',
            '-c:a',
            'aac',
            '-shortest',
            str(video),
        ]
    )

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(Handler, directory=str(root))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for index, (name, mode) in enumerate(
            [('image.jpg', 'photos'), ('video.mp4', 'mp4'), ('video.mp4', 'mp3')]
        ):
            config = {
                'url': f'http://127.0.0.1:{server.server_port}/{name}',
                'mode': mode,
                'folder': str(root / 'downloads' / mode),
                'ffmpeg': 'android-native',
                'height': 1080,
                'fps': None,
                'audio_quality': '192 kbps',
                'organization': 'Pasta de destino',
                'duplicate_policy': 'keep',
            }
            result = json.loads(
                run(
                    'test-download-' + str(index),
                    'download',
                    json.dumps(config),
                    callback,
                )
            )
            assert result.get('code') == 0, (result, events[-5:])
            assert any(
                (root / 'downloads' / mode).glob(
                    '*.' + ('jpg' if mode == 'photos' else mode)
                )
            )
        # Keep platform requests out of this reproducible fixture while exercising
        # the real mixed-post selector, image publishing and audio conversion.
        import instagram_media
        from mobile_backend import reply

        original_items = instagram_media.instagram_items
        base = f'http://127.0.0.1:{server.server_port}'
        instagram_media.instagram_items = lambda *args, **kwargs: [
            (
                base + '/image.jpg',
                {'extension': 'jpg', 'title': 'Foto teste', 'user': 'ONDA'},
            ),
            (
                base + '/video.mp4',
                {'extension': 'mp4', 'title': 'Vídeo teste', 'user': 'ONDA'},
            ),
        ]

        class MixedCallback:
            def onEvent(self, value):
                callback.onEvent(value)
                if json.loads(value).get('type') == 'choose_media':
                    reply(
                        'test-mixed',
                        json.dumps(
                            {'selected_ids': ['1', '2'], 'media_modes': {'2': 'mp3'}}
                        ),
                    )

        try:
            config = {
                'url': 'https://www.instagram.com/p/onda_test_fixture/',
                'mode': 'mp3',
                'folder': str(root / 'mixed'),
                'ffmpeg': 'android-native',
                'height': 1080,
                'fps': None,
                'audio_quality': '192 kbps',
                'organization': 'Pasta de destino',
                'duplicate_policy': 'keep',
            }
            result = json.loads(
                run('test-mixed', 'download', json.dumps(config), MixedCallback())
            )
            assert result.get('code') == 0, (result, events[-5:])
            assert list((root / 'mixed').glob('*.jpg')) and list(
                (root / 'mixed').glob('*.mp3')
            )
            from photo_music import direct_audio

            for mode in ('photos', 'photo_video'):
                identity = 'test-single-photo-' + mode
                instagram_media.instagram_items = lambda *args, **kwargs: [
                    (
                        base + '/image.jpg',
                        {
                            'extension': 'jpg',
                            'title': 'Foto com música',
                            'user': 'ONDA',
                            '_photo_audio': direct_audio(
                                base + '/Artista%20-%20M%C3%BAsica.mp3'
                            ),
                        },
                    )
                ]

                class PhotoCallback:
                    def onEvent(self, value):
                        callback.onEvent(value)
                        if json.loads(value).get('type') == 'choose_media':
                            reply(
                                identity,
                                json.dumps(
                                    {'selected_ids': ['1'], 'media_modes': {'1': mode}}
                                ),
                            )

                config = dict(
                    config, mode='mp3', folder=str(root / 'single-photo' / mode)
                )
                result = json.loads(
                    run(identity, 'download', json.dumps(config), PhotoCallback())
                )
                assert result.get('code') == 0, (result, events[-5:])
                output = list(
                    (root / 'single-photo' / mode).glob(
                        '*.mp4' if mode == 'photo_video' else '*.jpg'
                    )
                )
                assert len(output) == 1, output
                if mode == 'photo_video':
                    probe = subprocess.run(
                        [
                            str(_native / 'libffprobe.so'),
                            '-v',
                            'error',
                            '-show_streams',
                            '-of',
                            'json',
                            str(output[0]),
                        ],
                        capture_output=True,
                        timeout=30,
                    )
                    streams = json.loads(probe.stdout)['streams']
                    assert {s['codec_type'] for s in streams} == {
                        'video',
                        'audio',
                    }, streams
        finally:
            instagram_media.instagram_items = original_items
    finally:
        server.shutdown()
        server.server_close()
    return json.dumps(
        {
            'native': native,
            'effects_tags_and_cover': True,
            'preview_seek': True,
            'images_png_webp_svg': True,
            'playlist_csv_m3u_txt': True,
            'mixed_media_selection': True,
            'mixed_post_photo_and_audio': True,
            'single_photo_image_or_mp4_with_audio': True,
            'direct_download_photo_video_audio': True,
            'folder': str(root),
        },
        ensure_ascii=False,
    )


def create_history_audio(folder):
    source = Path(folder) / 'Histórico teste.mp3'
    result = subprocess.run(
        [
            str(_native / 'libffmpeg.so'),
            '-v',
            'error',
            '-y',
            '-i',
            str(Path(folder) / 'fixture.mp4'),
            '-vn',
            '-c:a',
            'libmp3lame',
            str(source),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    return str(source)


def verify_spotify_return(callback):
    from unittest.mock import patch
    import mobile_backend
    import spotify_account

    accepted = []

    class Account:
        def accept(self, client_id, tokens, remember=False):
            assert isinstance(tokens, dict)
            accepted.append((client_id, tokens, remember))

    tokens = {'access_token': 'fixture-access', 'refresh_token': 'fixture-refresh'}
    with (
        patch.object(
            spotify_account, 'authorize', return_value=('a' * 32, tokens)
        ) as authorize,
        patch.object(mobile_backend, 'account', return_value=Account()),
    ):
        result = json.loads(
            run(
                'test-spotify-return',
                'spotify_connect',
                json.dumps({'spotify_client_id': 'a' * 32}),
                callback,
            )
        )
    assert result.get('connected'), result
    assert accepted == [('a' * 32, tokens, True)]
    assert authorize.call_args.kwargs['return_url'] == 'onda://spotify-return'
    page = spotify_account.callback_page(True, True, 'onda://spotify-return').decode()
    assert (
        '}, 3000)' in page
        and 'window.close()' in page
        and 'onda://spotify-return' in page
    )
    assert 'setTimeout' not in spotify_account.callback_page(False, False).decode()
    return True


def create_live_audio(folder):
    source = Path(folder) / 'Histórico teste.mp3'
    result = subprocess.run(
        [
            str(_native / 'libffmpeg.so'),
            '-v',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            'sine=frequency=440:duration=40',
            '-c:a',
            'libmp3lame',
            str(source),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    return str(source)


_enter_search_patch = None
_enter_search_queries = []


def start_enter_search_fixture():
    global _enter_search_patch
    from unittest.mock import patch

    _enter_search_queries.clear()

    def search(query, *args, **kwargs):
        _enter_search_queries.append(query)
        return [
            {
                'title': 'Resultado: ' + query,
                'artists': ['Teste'],
                'source_url': 'https://example.com/test.mp3',
            }
        ]

    _enter_search_patch = patch('metadata.MetadataClient.search', side_effect=search)
    _enter_search_patch.start()


def enter_search_count():
    return len(_enter_search_queries)


def stop_enter_search_fixture():
    global _enter_search_patch
    if _enter_search_patch:
        _enter_search_patch.stop()
        _enter_search_patch = None
