"""Render a still image with the soundtrack actually supplied by its post."""
import math
import subprocess
from urllib.parse import urlsplit


def direct_audio(url, start=0, duration=None):
    if not isinstance(url, str) or urlsplit(url).scheme not in ('https', 'http'):
        return None
    try:
        start = float(start or 0)
        duration = float(duration) if duration is not None else None
    except (ValueError, TypeError):
        return None
    if not math.isfinite(start) or start < 0 or (duration is not None and (not math.isfinite(duration) or duration <= 0)):
        return None
    return {'url': url, 'start': start, 'duration': duration}


def instagram_audio(product):
    metadata = product.get('music_metadata') or {}
    for info in (metadata.get('music_info'), product.get('clips_metadata')):
        if not isinstance(info, dict):
            continue
        asset = info.get('music_asset_info') or info.get('original_sound_info') or {}
        consumption = info.get('music_consumption_info') or {}
        start = consumption.get('audio_asset_start_time_in_ms') or 0
        end = consumption.get('audio_asset_end_time_in_ms')
        try:
            audio = direct_audio(asset.get('progressive_download_url'), float(start) / 1000,
                                 (float(end) - float(start)) / 1000 if end is not None else None)
        except (TypeError, ValueError):
            audio = direct_audio(asset.get('progressive_download_url'))
        if audio:
            return audio
    return None


def render_photo_video(photo, audio, session, headers, config, emit):
    from audio_tools import executable, process_options
    if not isinstance(audio, dict) or not direct_audio(audio.get('url'), audio.get('start'), audio.get('duration')):
        raise ValueError('A plataforma não disponibilizou a música desta foto. Escolha Só foto.')
    # Use the authenticated platform session; never pass credentials to FFmpeg.
    soundtrack = photo.with_suffix(photo.suffix + '.soundtrack')
    target = photo.with_suffix('.mp4')
    partial = target.with_suffix('.render.mp4')
    emit('stage', message='Baixando a música da foto…')
    try:
        with session.get(audio['url'], headers=headers, stream=True, timeout=(20, 30)) as response:
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/' in content_type or 'json' in content_type or 'image/' in content_type:
                raise ValueError('A plataforma não forneceu um arquivo de áudio válido para esta foto.')
            size = 0
            with soundtrack.open('wb') as output:
                for chunk in response.iter_content(128 * 1024):
                    if chunk:
                        output.write(chunk)
                        size += len(chunk)
            expected = int(response.headers.get('Content-Length') or 0)
            if not size or (expected and size != expected):
                raise ValueError('Transferência da música incompleta. Tente novamente.')
        emit('stage', message='Criando MP4 com a foto inteira e a música…')
        command = [executable('ffmpeg', config.get('ffmpeg', '')), '-y', '-v', 'error',
                   '-loop', '1', '-framerate', '30', '-i', str(photo)]
        if audio.get('start'):
            command += ['-ss', str(audio['start'])]
        command += ['-i', str(soundtrack), '-map', '0:v:0', '-map', '1:a:0',
                    '-vf', 'scale=ceil(iw/2)*2:ceil(ih/2)*2',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart']
        if audio.get('duration'):
            command += ['-t', str(audio['duration'])]
        command.append(str(partial))
        result = subprocess.run(command, capture_output=True, timeout=600, **process_options())
        if result.returncode or not partial.is_file() or not partial.stat().st_size:
            raise ValueError('Não foi possível criar o MP4 com esta música. Tente baixar só a foto.')
        partial.replace(target)
        photo.unlink()
        return target
    finally:
        soundtrack.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
