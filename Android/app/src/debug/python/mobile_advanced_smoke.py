"""Synthetic tests for library editing and non-secret configuration transfer."""

import io
import json
from pathlib import Path
import subprocess
import tempfile


def verify(folder):
    from mobile_backend import _native
    from PIL import Image
    from tagging import apply_tags
    from audio_library import edit_copy, read_audio, normalize_audio
    from advanced_options import export_settings, import_settings
    from mutagen.id3 import ID3

    with tempfile.TemporaryDirectory(prefix='advanced-test-', dir=folder) as directory:
        root = Path(directory)
        source = root / 'Música.mp3'
        result = subprocess.run(
            [
                str(_native / 'libffmpeg.so'),
                '-v',
                'error',
                '-y',
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=440:duration=3',
                '-af',
                'volume=0.1',
                '-c:a',
                'libmp3lame',
                str(source),
            ],
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        art = io.BytesIO()
        Image.new('RGB', (40, 30), 'blue').save(art, format='JPEG')
        apply_tags(
            source,
            {
                'title': 'Música',
                'artists': ['Artista'],
                'album': 'Álbum',
                'source_url': 'https://example.com/music',
            },
            {'source_url': 'https://example.com/audio'},
            (art.getvalue(), 'image/jpeg'),
        )
        original = source.read_bytes()
        lyric = root / 'letra.lrc'
        lyric.write_text('[00:01.00]Letra de teste', encoding='utf-8')
        preview = normalize_audio(source, {'ffmpeg': 'android-native'}, preview=True)
        assert Path(preview).is_file()
        target = edit_copy(
            {
                'source': str(source),
                'folder': directory,
                'ffmpeg': 'android-native',
                'normalize_volume': True,
                'edit_metadata': True,
                'changes': {'title': 'Título editado'},
                'lyrics_path': str(lyric),
            }
        )
        audio = read_audio(target['path'])
        assert audio['title'] == 'Título editado' and audio['album'] == 'Álbum'
        tags = ID3(target['path'])
        assert tags.getall('APIC')[0].data == art.getvalue()
        assert 'Letra de teste' in tags.getall('USLT')[0].text
        assert (
            source.read_bytes() == original
            and Path(target['path']).with_suffix('.lrc').is_file()
        )
        exported = export_settings(
            {
                'theme': 'Claro',
                'mode': 'mp3',
                'concurrent_downloads': '2',
                'spotify_client_secret': 'secret',
                'cookies_file': 'private',
            },
            'android',
        )
        assert 'secret' not in json.dumps(exported) and 'private' not in json.dumps(
            exported
        )
        assert import_settings(exported, 'windows')['theme_mode'] == 'Claro'
    return True


def verify_storage(folder):
    """Exercise shared fixes with real Android storage and Mutagen."""
    import wave
    from audio_library import edit_copy
    from playlist_sync import reconcile

    with tempfile.TemporaryDirectory(
        prefix='storage-regression-', dir=folder
    ) as directory:
        root = Path(directory)
        source = root / 'song.wav'
        lyrics = root / 'input.lrc'
        with wave.open(str(source), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b'\0\0' * 8000)
        lyrics.write_text('[00:00.00]New lyrics', encoding='utf-8')
        existing = root / 'song - Editada.lrc'
        existing.write_text('User lyrics', encoding='utf-8')
        result = edit_copy({'source': str(source), 'lyrics_path': str(lyrics)})
        final = Path(result['path'])
        assert existing.read_text(encoding='utf-8') == 'User lyrics'
        assert final.name == 'song - Editada (2).wav'
        assert final.with_suffix('.lrc').read_text(
            encoding='utf-8'
        ) == lyrics.read_text(encoding='utf-8')
        from mutagen import File

        assert 'New lyrics' in File(final).tags.getall('USLT')[0].text
        track = {
            'source_url': 'https://example.com/song',
            'title': 'Song',
            'artists': ['Artist'],
        }
        for state in ('Erro', 'Cancelado', 'Concluído'):
            assert (
                reconcile([track], [], [{'url': track['source_url'], 'state': state}])[
                    'items'
                ][0]['state']
                == 'missing'
            )
        for state in ('Pendente', 'Baixando', 'Aguardando escolha'):
            assert (
                reconcile([track], [], [{'url': track['source_url'], 'state': state}])[
                    'items'
                ][0]['state']
                == 'queued'
            )
    return True
