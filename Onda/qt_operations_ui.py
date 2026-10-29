"""Headless operations reused by Qt. No widgets or GUI event loops."""

from pathlib import Path
import json, shutil, subprocess, tempfile


def client(config, cancel):
    from metadata import MetadataClient

    value = MetadataClient(
        config.get('spotify_client_id', ''), config.get('spotify_client_secret', '')
    )
    value.cancelled = cancel.is_set
    account = config.get('_account')
    if account and account.connected:
        value.spotify_get = account.get
    return value


def image_details(source):
    from PIL import Image

    try:
        with Image.open(source) as image:
            width, height = image.size
            if image.getexif().get(274) in (5, 6, 7, 8):
                width, height = height, width
            return {
                'width': width,
                'height': height,
                'format': image.format or Path(source).suffix.lstrip('.').upper(),
            }
    except (OSError, ValueError):
        return {}


def perform(action, config, cancel, emit):
    if action == 'tools_status':
        from tool_status import read, present, display

        report = read(config['_root'])
        return dict(report=report, display=display(report), message=present(report))
    if action == 'compare_collection_file':
        from collection_coverage import compare_file

        return compare_file(config['tracks'], config['source'])
    if action == 'image_gallery_manifest':
        from online_image_preview import discover

        return discover(config, cancel.is_set)
    if action == 'image_gallery_thumbnail':
        from online_image_preview import thumbnail

        try:
            return thumbnail(config['token'], int(config['index']), cancel.is_set)
        except Exception as error:
            if cancel.is_set():
                raise
            return {'error': str(error)}
    if action == 'effects_queue_info':
        rows = []
        for source in config['sources']:
            if cancel.is_set():
                break
            try:
                rows.append(
                    dict(
                        perform(
                            'effects_info', dict(config, source=source), cancel, emit
                        ),
                        source=source,
                    )
                )
            except Exception as error:
                rows.append({'source': source, 'error': str(error)})
        return rows
    if action in ('effects_search', 'playback_input'):
        value = client(config, cancel)
        try:
            from playback_input import resolve_input

            return resolve_input(
                config['query'], value, config, config.get('_account'), cancel.is_set
            )
        finally:
            value.close()
    if action == 'card_details':
        value = client(config, cancel)
        try:
            from catalog_details import complete_record

            return [
                dict(row, record=complete_record(row['record'], value, cancel.is_set))
                for row in config['requests']
                if not cancel.is_set()
            ]
        finally:
            value.close()
    if action == 'effects_collection':
        rows = []
        for record in config['tracks']:
            if cancel.is_set():
                raise InterruptedError('Cancelado')
            try:
                result = perform(
                    'effects_load', dict(config, record=record), cancel, emit
                )
                source = result['source']
                info = perform(
                    'effects_info',
                    dict(config, source=source, record=result.get('record') or record),
                    cancel,
                    emit,
                )
                rows.append(
                    dict(info, source=source, cover_url=record.get('cover_url', ''))
                )
            except Exception as error:
                if cancel.is_set():
                    raise
                rows.append(
                    {
                        'error': str(error),
                        'source': record.get('source_url', ''),
                        'record': dict(record),
                        'remote': True,
                        'duration': float(record.get('duration_ms') or 0) / 1000,
                        'cover_url': record.get('cover_url', ''),
                    }
                )
        return rows
    if action == 'effects_load':
        from jukebox import fetch_audio

        return fetch_audio(
            config,
            config['record'],
            cancel.is_set,
            lambda value: emit('stage', message=str(value) + '%'),
            analyze=False,
        )

    if action == "lyrics_online":
        from lyrics_service import fetch_lyrics

        try:
            return fetch_lyrics(
                config["source"],
                config.get("record"),
                cancel,
                alternatives=config.get('alternatives', False),
            )
        except Exception:
            if config.get('automatic'):
                return {}
            raise
    if action == 'history_details':
        from platform_info import platform_info
        from history_details import history_platform
        from audio_library import read_audio, cover_preview, AUDIO_TYPES

        rows = []
        for row in config['rows']:
            if cancel.is_set():
                break
            path = Path(row['path'])
            if path.suffix.lower() not in AUDIO_TYPES:
                continue
            try:
                cover = cover_preview(path)
                try:
                    record = read_audio(path)
                except (OSError, ValueError):
                    record = {'title': path.stem, 'artists': [], 'album': ''}
                cover_url = 'data:image/png;base64,' + cover if cover else ''
                if not cover_url:
                    for candidate in (
                        path.with_suffix('.jpg'),
                        path.with_suffix('.png'),
                        path.parent / 'cover.jpg',
                        path.parent / 'folder.jpg',
                    ):
                        if candidate.is_file():
                            from PySide6.QtCore import QUrl

                            cover_url = QUrl.fromLocalFile(str(candidate)).toString()
                            break
                rows.append(
                    dict(
                        id=row['id'],
                        title=record['title'],
                        artist=', '.join(record['artists']),
                        album=record['album'],
                        cover_url=cover_url,
                        **platform_info(row.get('source', ''), history_platform(path)),
                    )
                )
            except (OSError, ValueError):
                continue
        return rows

    if cancel.is_set():
        raise ValueError('Operação cancelada.')
    if action in ('search', 'collection', 'check_matches', 'release_date'):
        value = client(config, cancel)
        try:
            if action == 'search':
                from music_search import search_music

                return search_music(
                    value,
                    config['query'],
                    config.get('provider', 'Deezer'),
                    account=config.get('_account'),
                    automatic=config.get('auto_metadata', False),
                    refresh=config.get('refresh', False),
                    cancelled=cancel.is_set,
                )
            if action == 'collection':
                from playlist_import import load_interactive_playlist as load_playlist
                from catalog_details import collection_artwork

                return dict(
                    collection_artwork(
                        load_playlist(
                            config['url'],
                            value,
                            limit=int(config.get('playlist_limit', 1000)),
                            account=config.get('_account'),
                            cancelled=cancel.is_set,
                        )
                    ),
                    _collection_url=config['url'],
                )
            if action == 'release_date':
                from metadata import deezer_release_date

                return deezer_release_date(config['record'], value)
            from matching import find_youtube
            from engine import Logger

            result = {}
            for row in config['tracks']:
                if cancel.is_set():
                    break
                try:
                    match = find_youtube(
                        row, Logger(), prefer_best=config.get('auto_match', False)
                    )
                    result[row['source_url']] = match['title']
                except Exception as error:
                    result[row['source_url']] = str(error)
            return result
        finally:
            value.close()
    if action == 'compare_collection':
        from playlist_sync import scan_folder, compare_collection

        inventory = scan_folder(
            config['folder'], config.get('history', []), cancel.is_set
        )
        return compare_collection(
            config['tracks'],
            inventory,
            config.get('queued', []),
            config.get('url', ''),
            config['database'],
        )
    if action == 'detect_silence':
        from silence import detect

        rows = []
        for index, source in enumerate(config['sources']):
            if cancel.is_set():
                raise InterruptedError('Detecção cancelada.')
            emit(
                'stage',
                message=f"{index+1}/{len(config['sources'])} · {Path(source).name}",
            )
            try:
                rows.append(detect(source, config.get('ffmpeg', ''), cancel.is_set))
            except InterruptedError:
                raise
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                rows.append({'source': source, 'error': str(error)})
        return rows
    if action == 'convert':
        from video_converter import convert_video, convert_batch

        return (convert_batch if len(config.get('sources', [])) > 1 else convert_video)(
            config, emit, cancel.is_set
        )
    if action == 'probe':
        from audio_tools import executable, process_options

        output = subprocess.run(
            [
                executable('ffprobe', config.get('ffmpeg', '')),
                '-v',
                'error',
                '-show_entries',
                'format=duration',
                '-of',
                'json',
                config['source'],
            ],
            capture_output=True,
            text=True,
            timeout=20,
            **process_options(),
        )
        if output.returncode:
            raise ValueError(output.stderr[-1000:])
        return float(json.loads(output.stdout).get('format', {}).get('duration', 0))
    if action == 'normalize_preview':
        from audio_library import normalize_audio

        return {
            'path': str(normalize_audio(config['source'], config, emit, preview=True))
        }
    if action == 'cover_crop':
        from PIL import Image, ImageOps
        from cover_crop import crop_box
        import uuid

        target = Path(config['_root']) / 'image-preview'
        target.mkdir(parents=True, exist_ok=True)
        target = target / (uuid.uuid4().hex + '.png')
        with Image.open(config['source']) as opened:
            if opened.width * opened.height > 40_000_000:
                raise ValueError('Escolha uma imagem de até 40 megapixels.')
            image = ImageOps.exif_transpose(opened).convert('RGBA')
            image.thumbnail((2048, 2048))
            zoom = max(1, min(4, float(config.get('zoom', 1))))
            side = min(image.size) / zoom
            box = crop_box(
                *image.size,
                zoom,
                float(config.get('x', 0)) * side,
                float(config.get('y', 0)) * side,
            )
            image.resize((1000, 1000), Image.Resampling.LANCZOS, box=box).save(target)
        return {'path': str(target)}
    if action == 'effects_info':
        from audio_library import read_audio, cover_preview

        try:
            record = read_audio(config['source'])
        except (OSError, ValueError):
            record = {'title': Path(config['source']).stem}
        supplied = (
            config.get('record')
            or config.get('records', {}).get(config['source'])
            or {}
        )
        for field in ('title', 'artists', 'album', 'cover_url'):
            if supplied.get(field):
                record[field] = supplied[field]
        duration = record.get('duration') or perform('probe', config, cancel, emit)
        return {
            'record': record,
            'cover': cover_preview(config['source']) or '',
            'duration': duration,
        }
    if action == 'audio_read':
        from audio_library import read_audio, cover_preview

        return {
            'record': read_audio(config['source']),
            'cover': cover_preview(config['source']) or '',
        }
    if action == 'audio_edit':
        from audio_library import edit_copy
        from batch_metadata import edit_batch

        return (
            edit_batch(config, emit, cancelled=cancel.is_set)
            if len(config.get('sources', [])) > 1
            else edit_copy(config, emit, cancelled=cancel.is_set)
        )
    if action == 'image_info':
        return {'source': image_details(config['source'])}
    if action in ('image_preview', 'image_export'):
        from image_output import transform_image, open_preview
        from file_output import publish

        root = Path(config['_root']) / 'image-preview'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='onda-image-') as temp:
            if str(config['source']).startswith(('http://', 'https://')):
                from media_links import prepare_link

                files = []

                def capture(event, **data):
                    if cancel.is_set():
                        raise ValueError('Operação cancelada.')
                    if event == 'file':
                        files.append(data['path'])
                    emit(event, **data)

                done, _ = prepare_link(
                    {
                        'url': config['source'],
                        'mode': 'photos',
                        'folder': temp,
                        'cookies_file': config.get('social_cookies', ''),
                        'duplicate_policy': 'keep',
                    },
                    capture,
                    None,
                )
                if not done or not files:
                    raise ValueError(
                        'Use um link direto de imagem ou uma página com imagem principal. Publicações podem ser baixadas pela fila.'
                    )
                source = Path(files[0])
            else:
                source = Path(temp) / Path(config['source']).name
                shutil.copyfile(config['source'], source)
            if cancel.is_set():
                raise ValueError('Operação cancelada.')
            original = image_details(source)
            output = transform_image(source, config['image_options'], emit)
            output_info = image_details(output)
            if action == 'image_preview':
                target = root / 'preview.png'
                with open_preview(output) as image:
                    image.thumbnail((1400, 1400))
                    image.convert('RGBA').save(target)
                return {
                    'path': str(target),
                    'preview': True,
                    'image_info': {'source': original, 'output': output_info},
                }
            final, skipped = publish(output, config['folder'], 'keep', None)
            return {
                'path': str(final),
                'skipped': skipped,
                'image_info': {'source': original, 'output': output_info},
            }
    if action == 'cache_auto':
        from cache_cleanup import automatic_cleanup

        return automatic_cleanup(config['_root'])
    if action in ('cache_info', 'cache_clear'):
        from cache_cleanup import cache_info, clear_cache

        return (clear_cache if action == 'cache_clear' else cache_info)(config['_root'])
    if action == 'prepare_tools':
        from ffmpeg_runtime import download_tools

        return str(
            download_tools(
                cancel=cancel,
                progress=lambda done, total, message: emit(
                    'stage', message=message, done=done, total=total
                ),
            )
        )
    if action == 'verify_tools':
        from audio_tools import executable
        from tool_status import check, present, display

        commands = {}
        for name in ('ffmpeg', 'ffprobe', 'ffplay'):
            try:
                commands[name] = [
                    executable(name, config.get('ffmpeg', '')),
                    '-version',
                ]
            except (OSError, ValueError):
                commands[name] = ['onda-missing-' + name, '-version']
        commands['Node.js'] = [
            shutil.which('node')
            or str(Path(__import__('sys').executable).parents[1] / 'node/node.exe'),
            '--version',
        ]
        report = check(config['_root'], commands)
        return dict(report=report, display=display(report), message=present(report))
    if action == 'app_update':
        from advanced_options import release_update
        from app_version import VERSION

        return release_update('windows', VERSION)
    if action == 'update_tools':
        emit('stage', message='Atualizando ferramentas…', done=0, total=0)
        from audio_tools import process_options
        import sys

        python = Path(sys.executable).with_name('python.exe')
        result = subprocess.run(
            [
                str(python),
                '-m',
                'pip',
                'install',
                '--upgrade',
                'yt-dlp[default,curl-cffi]',
                'gallery-dl<2',
                'Pillow>=10',
            ],
            capture_output=True,
            text=True,
            timeout=240,
            **process_options(),
        )
        from tool_status import updated, present, display

        report = updated(config['_root'], not result.returncode)
        if result.returncode:
            raise ValueError(
                'Falha na atualização das ferramentas. Verifique a conexão e tente novamente.'
            )
        return dict(report=report, display=display(report), message=present(report))
    if action == 'spotify_connect':
        from spotify_account import authorize

        identity, tokens = authorize(
            config['spotify_client_id'],
            cancel,
            language=config.get('language', 'pt-BR'),
        )
        config['_account'].accept(identity, tokens, remember=True)
        return {'message': 'Spotify conectado.'}
    raise ValueError('Operação desconhecida: ' + action)
