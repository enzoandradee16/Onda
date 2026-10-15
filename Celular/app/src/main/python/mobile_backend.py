"""Android adapter for ONDA's shared engine. No desktop/UI imports required."""
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import zipfile

_local = threading.local()
_jobs = {}
_lock = threading.RLock()
_configured = False
_root = None
_native = None
_original_popen = subprocess.Popen


class Cancelled(ValueError):
    pass


def readable_error(message):
    message=str(message)
    if 'sign in to confirm' in message.lower() or "confirm you’re not a bot" in message.lower():
        return 'O YouTube exigiu uma verificação nesta conexão. Abra Menu → Sessão do YouTube, conclua a verificação e toque em Usar esta sessão. Também é possível importar cookies.txt em Configurações → Contas e redes. A liberação depende do YouTube.'
    return message


def emit(kind, **values):
    state = getattr(_local, 'state', None)
    if state:
        if state['cancel'].is_set():
            raise Cancelled('Operação cancelada.')
        if kind=='error' and 'message' in values:
            values['message']=readable_error(values['message'])
        if kind in ('file','done') and values.get('path') and state.get('duplicate_choice'):
            values['duplicate_choice'] = state.pop('duplicate_choice')
        state['callback'].onEvent(json.dumps({'type': kind, **values}, ensure_ascii=False))


def ask(kind, **values):
    state = _local.state
    emit(kind, **values)
    while not state['cancel'].is_set():
        try:
            result = state['replies'].get(timeout=.2)
            if result.get('cancel'):
                raise Cancelled('Seleção cancelada.')
            return result
        except queue.Empty:
            pass
    raise Cancelled('Operação cancelada.')


def ask_version(record, candidates, **_):
    selected = ask('choose_version', record=record, candidates=candidates).get('selected_id')
    for item in candidates:
        if item['id'] == selected:
            return dict(item, selection='user')
    raise ValueError('Escolha uma versão válida.')


def ask_catalog(anchor, candidates, **_):
    selected = ask('choose_catalog', record=anchor, candidates=candidates).get('selected_id')
    for item in candidates:
        if item['source_url'] == selected:
            return item
    raise ValueError('Escolha uma faixa válida.')


def ask_review(record, audio_source=None, **_):
    from review import apply_review
    return apply_review(record, ask('review_metadata', record=record, audio_source=audio_source)['changes'])


def ask_duplicate(path, **_):
    value = ask('choose_duplicate', path=str(path))['choice']
    if value not in ('keep', 'replace', 'skip'):
        raise ValueError('Escolha inválida.')
    _local.state['duplicate_choice'] = value
    return value


def ask_flac_browser(record, url, **_):
    from flac_browser import INSTRUCTIONS
    path = ask('choose_flac', record=record, url=url, message=INSTRUCTIONS)['path']
    imported = Path(path).resolve()
    if imported.parent == (_root / 'imports').resolve() and imported.name.startswith('flac-browser-'):
        _local.state.setdefault('flac_imports', []).append(imported)
    return path


def ask_media(candidates, **_):
    from media_selection import validate_selection
    value = ask('choose_media', candidates=candidates)
    selected, modes = validate_selection(value, candidates)
    return {'selected_ids': selected, 'media_modes': modes} if modes else selected


class ManagedProcess(_original_popen):
    """Track native processes so cancellation also stops FFmpeg conversion."""
    def __init__(self, *args, **kwargs):
        state = getattr(_local, 'state', None)
        if state and state['cancel'].is_set():
            raise Cancelled('Operação cancelada.')
        super().__init__(*args, **kwargs)
        if state:
            with _lock:
                state['processes'].append(self)


def configure(root, native, libs):
    global _configured, _root, _native
    if _configured:
        return
    _root, _native = Path(root), Path(native)
    _root.mkdir(parents=True, exist_ok=True)
    # Extracted shared libraries are data; executable entry points remain in nativeLibraryDir.
    os.environ['LD_LIBRARY_PATH'] = str(libs) + ':' + str(_native) + ':' + os.environ.get('LD_LIBRARY_PATH', '')
    update = _root / 'tools/yt-dlp.zip'
    if update.is_file():
        sys.path.insert(0, str(update))
    import engine
    import audio_tools
    import effects_worker
    import yt_dlp
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
    engine.emit = effects_worker.emit = emit
    engine.ask_version, engine.ask_catalog = ask_version, ask_catalog
    engine.ask_review, engine.ask_duplicate, engine.ask_media = ask_review, ask_duplicate, ask_media
    engine.ask_flac_browser = ask_flac_browser
    paths = {name: str(_native / ('lib' + name + '.so')) for name in ('ffmpeg', 'ffprobe')}
    engine.binaries = lambda folder='': all(Path(v).is_file() for v in paths.values())
    def executable(name, folder=''):
        if name not in paths:
            raise ValueError('Ferramenta não disponível: ' + name)
        return paths[name]
    audio_tools.executable = effects_worker.executable = executable
    class AndroidOS:
        """Android SELinux disallows hard links; preserve exclusive publication."""
        def __getattr__(self, name):
            return getattr(os, name)

        @staticmethod
        def link(source, target):
            # Open outside the cleanup handler: never delete an existing target.
            output = Path(target).open('xb')
            try:
                with output, Path(source).open('rb') as original:
                    while chunk := original.read(1024*1024):
                        state = getattr(_local, 'state', None)
                        if state and state['cancel'].is_set():
                            raise Cancelled('Operação cancelada.')
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                Path(target).unlink(missing_ok=True)
                raise
    effects_worker.os = AndroidOS()
    FFmpegPostProcessor._determine_executables = lambda self: dict(paths)
    original = yt_dlp.YoutubeDL.__init__
    def initialize(self, params=None, *args, **kwargs):
        params = dict(params or {})
        state=getattr(_local,'state',None)
        config=(state or {}).get('config',{})
        cookies=config.get('cookies_file')
        from social_media import is_social
        if not is_social(config.get('url','')):
            cookies=config.get('youtube_cookies_file') or cookies
        if cookies:
            params['cookiefile']=cookies
        params['js_runtimes'] = {'quickjs': {'path': str(_native / 'libqjs.so')}}
        params['cachedir'] = str(_root / 'extractor-cache')
        original(self, params, *args, **kwargs)
    yt_dlp.YoutubeDL.__init__ = initialize
    subprocess.Popen = ManagedProcess
    # Chaquopy's Pillow wheel lacks libwebp; use the included Android FFmpeg codec.
    from PIL import Image
    import io
    Image.init()
    original_open=Image.open
    def open_image(fp, mode='r', formats=None):
        stream=fp if hasattr(fp,'read') else None
        close=False
        if stream is None:
            stream=open(fp,'rb')
            close=True
        try:
            stream.seek(0)
            header=stream.read(12)
            stream.seek(0)
            if header[:4]==b'RIFF' and header[8:12]==b'WEBP':
                data=stream.read(48*1024*1024+1)
                if len(data)>48*1024*1024:
                    raise ValueError('Imagem WebP acima do limite.')
                decoded=subprocess.run([paths['ffmpeg'],'-v','error','-i','pipe:0','-frames:v','1','-f','image2pipe','-c:v','png','pipe:1'],input=data,capture_output=True,timeout=40)
                if decoded.returncode:
                    raise ValueError('Não foi possível ler a imagem WebP.')
                return original_open(io.BytesIO(decoded.stdout))
        finally:
            if close:
                stream.close()
        return original_open(fp,mode,formats)
    def save_webp(image, fp, filename):
        image_bytes=io.BytesIO()
        image.save(image_bytes,format='PNG')
        encoded=subprocess.run([paths['ffmpeg'],'-v','error','-i','pipe:0','-frames:v','1','-c:v','libwebp','-quality',str(image.encoderinfo.get('quality',90)),'-f','webp','pipe:1'],input=image_bytes.getvalue(),capture_output=True,timeout=40)
        if encoded.returncode:
            raise ValueError('Não foi possível converter a imagem para WebP.')
        fp.write(encoded.stdout)
    Image.open=open_image
    Image.register_save('WEBP',save_webp)
    Image.register_extension('WEBP','.webp')
    _configured = True


def reply(identity, payload):
    with _lock:
        state = _jobs.get(identity)
    if state:
        state['replies'].put(json.loads(payload))


def cancel(identity):
    with _lock:
        state = _jobs.get(identity)
        if state:
            state['cancel'].set()
            for process in state['processes']:
                if process.poll() is None:
                    try:
                        process.terminate()
                    except OSError:
                        pass


def client(config):
    from metadata import MetadataClient
    return MetadataClient(config.get('spotify_client_id', ''), config.get('spotify_client_secret', ''))


def account():
    from spotify_account import SpotifyAccount
    return SpotifyAccount(str(_root / 'spotify-account'))


def render_preview(config):
    from audio_tools import effects_filter, process_options
    preview_id = str(config.get('preview_id', 'default'))
    if not all(c in '0123456789abcdef-' for c in preview_id) and preview_id != 'default':
        raise ValueError('Identificador de prévia inválido')
    output = _root / ('preview-' + preview_id + '.mp3')
    start = max(0, float(config.get('start', 0)))
    seconds = min(180, max(10, float(config.get('duration', 25))))
    command = [str(_native / 'libffmpeg.so'), '-y', '-v', 'error', '-ss', str(start),
               '-i', config['source'], '-t', str(seconds), '-vn', '-af',
               effects_filter(config.get('speed', 100), config.get('reverb', 0), config.get('keep_pitch', False)),
               '-c:a', 'libmp3lame', '-b:a', '192k', str(output)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=120, **process_options())
        if result.returncode:
            raise ValueError('Não foi possível preparar a prévia: ' + result.stderr.decode(errors='replace')[-1200:])
        return {'path': str(output), 'source_start': start}
    except BaseException:
        output.unlink(missing_ok=True)
        raise


def perform(action, config):
    if action == 'audio_batch_edit':
        from batch_metadata import edit_batch
        return edit_batch(dict(config, _android_batch=True), emit)
    if action in ('audio_read','audio_edit','normalize_preview'):
        from audio_library import read_audio,edit_copy,normalize_audio
        if action=='audio_read':
            from audio_library import cover_preview
            return {'record':read_audio(config['source']), 'cover_preview':cover_preview(config['source'])}
        if action=='normalize_preview':return {'path':str(normalize_audio(config['source'],config,emit,preview=True))}
        # Android edits an imported staging file; the original is its content URI.
        result=edit_copy(dict(config,overwrite_original=False),emit)
        if config.get('overwrite_original'):
            return dict(result,message='Arquivo original atualizado.')
        emit('file',**result)
        sidecar=Path(result['path']).with_suffix('.lrc')
        if sidecar.is_file():emit('file',path=str(sidecar),mode='LRC',size=sidecar.stat().st_size)
        return {'message':'Cópia editada salva na pasta de destino.'}
    if action=='settings_export':
        from advanced_options import export_settings
        return {'payload':export_settings(config['settings'],'android')}
    if action=='settings_import':
        from advanced_options import import_settings
        path=Path(config['path'])
        if path.stat().st_size>131072:raise ValueError('Arquivo muito grande.')
        return {'settings':import_settings(json.loads(path.read_text(encoding='utf-8')),'android')}
    if action=='app_update':
        from advanced_options import release_update
        return release_update('android',config.get('version','1.1.0'))
    if action == 'describe':
        from metadata import is_streaming_link
        if is_streaming_link(config['url']):
            value=client(config)
            try:
                from queue_titles import describe_streaming, record_name
                record=describe_streaming(value, config['url'])
                from queue_details import queue_info
                return {'title':record_name(record) or config['url'], 'queue_info':queue_info(record)}
            finally:
                value.close()
        import yt_dlp
        from engine import validate_url
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'extract_flat':True,'skip_download':True,'noplaylist':True,'socket_timeout':15,'retries':1}) as downloader:
            info=downloader.extract_info(validate_url(config['url']),download=False)
        return {'title':' - '.join(filter(None,[info.get('artist') or info.get('uploader'),info.get('track') or info.get('title')])), 'queue_info':{'artists':[info.get('artist') or info.get('uploader')] if info.get('artist') or info.get('uploader') else [],'album':info.get('album') or '', 'cover_url':info.get('thumbnail') or '', 'duration_ms':int((info.get('duration') or 0)*1000)}}
    if action == 'download':
        import engine
        from social_media import is_social, download_post
        if is_social(config['url']) and config.get('mode') in ('mp3','m4a','flac','original'):
            if download_post(config, emit, ask_duplicate, choose=ask_media):
                return {'code':0}
        return {'code': engine.run_worker(config)}
    if action == 'search':
        from metadata import is_streaming_link
        value = client(config)
        try:
            records = [value.resolve(config['query'], choose=ask_catalog)] if is_streaming_link(config['query']) else value.search(config['query'], config.get('provider', 'Deezer'), account=account())
            return {'tracks': records}
        finally:
            value.close()
    if action == 'collection':
        from playlist_import import load_playlist
        value = client(config)
        try:
            return load_playlist(config['url'], value, limit=int(config.get('playlist_limit', 2000)), account=account(), cancelled=_local.state['cancel'].is_set)
        finally:
            value.close()
    if action == 'import':
        from playlist_import import load_text
        from playlist_files import load_csv
        text = Path(config['path']).read_text(encoding='utf-8-sig')
        if config.get('extension', '').lower() == 'csv':
            return load_csv(text, int(config.get('playlist_limit', 2000)))
        return load_text(text, int(config.get('playlist_limit', 2000)))
    if action == 'export_list':
        from playlist_files import export_text
        return {'text': export_text(config['tracks'], m3u=config.get('format') == 'm3u')}
    if action == 'matches':
        from matching import resolve_youtube
        from metadata import is_streaming_link
        import engine
        items = []
        value=client(config)
        try:
            for record in config['tracks']:
                if is_streaming_link(record['source_url']):
                    complete=value.resolve(record['source_url'],choose=ask_catalog)
                    if config.get('mode') == 'flac':
                        from lossless_source import search_matches, choose_match
                        match=choose_match(complete,search_matches(complete),ask_version,config)
                    else:
                        match=resolve_youtube(complete,engine.Logger(),ask_version,automatic=bool(config.get('auto_match')),confirm=bool(config.get('confirm_version')))
                else:
                    match={'title':'Vídeo original','source_url':record['source_url']}
                items.append(dict(record,youtube_match=match))
        finally:
            value.close()
        return {'tracks': items}
    if action == 'effects':
        from effects_worker import render
        target=Path(config['output'])
        if target.exists():
            policy=config.get('duplicate_policy','ask')
            if policy=='ask':
                policy=ask_duplicate(target)
            if policy=='skip':
                emit('file',path=str(target),mode=target.suffix.lstrip('.'),skipped=True)
                return {'code':0}
            if policy=='replace':
                config=dict(config,replace=True)
            else:
                index=2
                candidate=target.with_name(f'{target.stem} ({index}){target.suffix}')
                while candidate.exists():
                    index+=1
                    candidate=target.with_name(f'{target.stem} ({index}){target.suffix}')
                config=dict(config,output=str(candidate))
        return {'code': render(config)}
    if action == 'preview':
        return render_preview(config)
    if action in ('image_preview','image_convert'):
        import shutil
        import tempfile
        from image_output import transform_image, open_preview
        from media_links import prepare_link
        from file_output import publish
        folder = _root / 'image-preview'
        folder.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            files=[]
            def capture(kind, **values):
                if kind=='file':
                    files.append(values['path'])
                elif kind not in ('done', 'progress'):
                    emit(kind, **values)
            if config.get('source'):
                source=Path(temporary)/config.get('name',Path(config['source']).name)
                # Android may deny copying filesystem attributes; only image bytes are needed.
                shutil.copyfile(config['source'],source)
            else:
                work=dict(config,folder=temporary,mode='photos',duplicate_policy='keep')
                done,_=prepare_link(work,capture,None)
                if not done or not files:
                    raise ValueError('A prévia requer um link direto de imagem ou uma página com imagem principal.')
                source=Path(files[0])
            image=transform_image(source,config['image_options'])
            if action=='image_preview':
                with open_preview(image) as picture:
                    dimensions=picture.size
                    picture.thumbnail((1600,1600))
                    result=folder/'preview.png'
                    picture.convert('RGBA').save(result,format='PNG')
                return {'path':str(result),'width':dimensions[0],'height':dimensions[1]}
            final,skipped=publish(image,Path(config['folder']),config.get('duplicate_policy','keep'),ask_duplicate)
            emit('file',path=final,mode=Path(final).suffix.lstrip('.'),skipped=skipped)
            return {'path':final}
    if action == 'resolve_preview':
        import yt_dlp
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'noplaylist':True,'format':'bestaudio/best','socket_timeout':20}) as downloader:
            info = downloader.extract_info(config['url'], download=False)
        return {'url':info['url'],'headers':info.get('http_headers') or {}}
    if action == 'probe':
        result = subprocess.run([str(_native / 'libffprobe.so'), '-v', 'error', '-show_format', '-of', 'json', config['source']], capture_output=True, timeout=20)
        if result.returncode:
            raise ValueError('Não foi possível ler o áudio.')
        return json.loads(result.stdout)
    if action == 'spotify_connect':
        from spotify_account import authorize
        def opener(url):
            emit('open_browser', url=url)
            return True
        # Loopback + PKCE: authorization code is never logged or shared with another host.
        client_id, tokens = authorize(config['spotify_client_id'], _local.state['cancel'], opener=opener, return_url='onda://spotify-return', translate=lambda text: config.get('ui_messages', {}).get(text, text), language=config.get('language', 'pt-BR'))
        account().accept(client_id, tokens, remember=True)
        return {'connected': True}
    if action == 'spotify_disconnect':
        account().disconnect()
        return {'connected': False}
    if action == 'update':
        import requests
        response = requests.get('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest', timeout=30)
        response.raise_for_status()
        data = response.json()
        assets = {a['name']: a['browser_download_url'] for a in data.get('assets', [])}
        sums = requests.get(assets['SHA2-256SUMS'], timeout=30)
        sums.raise_for_status()
        expected = next(line.split()[0] for line in sums.text.splitlines() if line.split()[-1].lstrip('*') == 'yt-dlp')
        target = _root / 'tools/yt-dlp.zip'
        target.parent.mkdir(exist_ok=True)
        tmp = target.with_suffix('.tmp')
        digest = hashlib.sha256()
        try:
            with requests.get(assets['yt-dlp'], stream=True, timeout=(10, 30)) as download:
                download.raise_for_status()
                with tmp.open('wb') as stream:
                    size = 0
                    for chunk in download.iter_content(65536):
                        size += len(chunk)
                        if size > 40*1024*1024:
                            raise ValueError('Atualização acima do limite.')
                        digest.update(chunk)
                        stream.write(chunk)
                        emit('stage', message='Baixando atualização do yt-dlp…')
            if digest.hexdigest() != expected:
                raise ValueError('A verificação da atualização falhou.')
            with zipfile.ZipFile(tmp) as archive:
                if 'yt_dlp/__init__.py' not in archive.namelist() or archive.testzip():
                    raise ValueError('Pacote inválido.')
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
        return {'version': data['tag_name'], 'message': 'Atualização preparada. Use Forçar parada nas configurações Android e abra o ONDA novamente para aplicar.'}
    if action == 'self_test':
        import yt_dlp
        from audio_tools import effects_filter, effect_name
        native = {}
        for name in ('ffmpeg', 'ffprobe', 'qjs'):
            command = [str(_native / ('lib'+name+'.so')), *(['-e','console.log(2+2)'] if name=='qjs' else ['-version'])]
            result = subprocess.run(command, capture_output=True, timeout=20)
            native[name] = {'code': result.returncode, 'output': (result.stdout+result.stderr).decode(errors='replace')[:400]}
            if result.returncode:
                raise ValueError('Falha na ferramenta ' + name + ': ' + native[name]['output'])
        import PIL, gallery_dl, mutagen
        return {'yt_dlp': yt_dlp.version.__version__, 'native': native, 'filter': effects_filter(90,25,True), 'effect': effect_name(90,25), 'spotify_connected': account().connected}
    raise ValueError('Operação desconhecida: ' + action)


def run(identity, action, payload, callback):
    state = {'cancel': threading.Event(), 'replies': queue.Queue(), 'processes': [], 'callback': callback}
    with _lock:
        _jobs[identity] = state
    _local.state = state
    try:
        state['config']=json.loads(payload)
        result = perform(action, state['config'])
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        # Errors stay in the UI; credentials, cookie contents and OAuth codes are never dumped.
        return json.dumps({'error': readable_error(exc), 'cancelled': state['cancel'].is_set()}, ensure_ascii=False)
    finally:
        for imported in state.get('flac_imports', []):
            imported.unlink(missing_ok=True)
        with _lock:
            _jobs.pop(identity, None)
        _local.state = None
