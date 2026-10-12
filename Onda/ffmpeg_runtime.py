"""Download media tools directly from their publisher; never bundle them in ONDA."""
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import tempfile
import threading
import zipfile

VERSION = '9.0.2'
URL = 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip'
SHA256 = '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'
ARCHIVE_ROOT = 'ffmpeg-9.0.2-essentials_build'
EXECUTABLES = ('ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe')
MAX_DOWNLOAD = 180 * 1024 * 1024
MAX_EXTRACTED = 400 * 1024 * 1024


class DownloadCancelled(Exception):
    pass


def data_root():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.config'))) / 'Onda'


def cache_folder(root=None):
    return (Path(root) if root is not None else data_root()) / 'tools' / 'ffmpeg' / VERSION


def complete_folder(folder):
    return bool(folder) and all((Path(folder) / name).is_file() for name in EXECUTABLES)


def cached_folder(root=None):
    folder = cache_folder(root)
    try:
        marker = json.loads((folder / 'verified.json').read_text(encoding='utf-8'))
        if marker['archive_sha256'] == SHA256 and all(
                (folder / name).stat().st_size == marker['files'][name] for name in EXECUTABLES):
            return folder
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def existing_folder(root=None):
    root = Path(root) if root is not None else data_root()
    try:
        preferences = json.loads((root / 'settings.json').read_text(encoding='utf-8'))
        custom = preferences.get('ffmpeg')
        if isinstance(custom, str) and complete_folder(custom):
            return Path(custom)
    except (OSError, ValueError, AttributeError):
        pass
    cached = cached_folder(root)
    if cached:
        return cached
    paths = [shutil.which(name) for name in EXECUTABLES]
    if all(paths) and len({str(Path(path).parent) for path in paths}) == 1:
        return Path(paths[0]).parent
    return None


def download_tools(*, root=None, progress=lambda *args: None, cancel=None, session=None):
    """Bounded download, pinned SHA-256, allowlisted extraction and final marker."""
    existing = cached_folder(root)
    if existing:
        return existing
    import requests
    cancel = cancel or threading.Event()
    folder = cache_folder(root)
    folder.parent.mkdir(parents=True, exist_ok=True)

    def check_cancelled():
        if cancel.is_set():
            raise DownloadCancelled()

    client = session or requests
    with tempfile.TemporaryDirectory(prefix='.onda-download-', dir=folder.parent) as staging:
        staging = Path(staging)
        archive_path = staging / 'ffmpeg.zip'
        check_cancelled()
        progress(0, 0, 'Baixando FFmpeg diretamente de gyan.dev…')
        with client.get(URL, stream=True, timeout=(15, 30)) as response:
            response.raise_for_status()
            total = int(response.headers.get('Content-Length', 0))
            if total > MAX_DOWNLOAD:
                raise ValueError('O pacote excede o tamanho permitido.')
            digest, downloaded = hashlib.sha256(), 0
            with archive_path.open('wb') as output:
                for block in response.iter_content(256 * 1024):
                    check_cancelled()
                    downloaded += len(block)
                    if downloaded > MAX_DOWNLOAD:
                        raise ValueError('O pacote excede o tamanho permitido.')
                    output.write(block)
                    digest.update(block)
                    progress(downloaded, total, 'Baixando FFmpeg…')
        check_cancelled()
        progress(downloaded, total, 'Conferindo a integridade do download…')
        if digest.hexdigest() != SHA256:
            raise ValueError('A verificação do FFmpeg falhou. O arquivo foi descartado; tente novamente.')
        names = {f'{ARCHIVE_ROOT}/bin/{name}': name for name in EXECUTABLES}
        names.update({f'{ARCHIVE_ROOT}/LICENSE': 'LICENSE.txt', f'{ARCHIVE_ROOT}/README.txt': 'README.txt'})
        with zipfile.ZipFile(archive_path) as archive:
            matches = [info for info in archive.infolist() if info.filename in names]
            if len(matches) != len(names) or len({info.filename for info in matches}) != len(names):
                raise ValueError('O pacote do FFmpeg está incompleto ou é inválido.')
            if sum(info.file_size for info in matches) > MAX_EXTRACTED:
                raise ValueError('O pacote extraído excede o tamanho permitido.')
            for info in matches:
                check_cancelled()
                progress(downloaded, total, 'Preparando as ferramentas de áudio e vídeo…')
                # Never extract arbitrary ZIP paths, symlinks or directories.
                with archive.open(info) as source, (staging / names[info.filename]).open('wb') as output:
                    while True:
                        check_cancelled()
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
        check_cancelled()
        folder.mkdir(parents=True, exist_ok=True)
        for name in names.values():
            os.replace(staging / name, folder / name)
        marker = {'version': VERSION, 'origin': URL, 'archive_sha256': SHA256,
                  'files': {name: (folder / name).stat().st_size for name in EXECUTABLES}}
        temporary_marker = staging / 'verified.json'
        temporary_marker.write_text(json.dumps(marker, indent=2), encoding='utf-8')
        os.replace(temporary_marker, folder / 'verified.json')
    return folder


def download_with_window(parent=None):
    """All widget access stays on the UI thread; download runs in a worker."""
    import tkinter as tk
    from tkinter import ttk
    from window_position import center_window
    window = tk.Toplevel(parent) if parent is not None else tk.Tk()
    window.title('ONDA · Preparar áudio e vídeo')
    window.geometry('560x255')
    window.resizable(False, False)
    try:
        window.iconbitmap(str(Path(__file__).resolve().parent.parent / 'onda.ico'))
    except tk.TclError:
        pass
    body = ttk.Frame(window, padding=24)
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='Preparando o ONDA', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
    ttk.Label(body, text='O FFmpeg é baixado uma vez para converter e reproduzir mídias.\n'
              'Origem: gyan.dev · aproximadamente 109 MB', wraplength=505).pack(anchor='w', pady=(8, 12))
    status = tk.StringVar(value='Conectando…')
    ttk.Label(body, textvariable=status, wraplength=505).pack(anchor='w')
    bar = ttk.Progressbar(body, maximum=100)
    bar.pack(fill='x', pady=12)
    actions = ttk.Frame(body)
    actions.pack(fill='x')
    events, stopped, result = queue.Queue(), threading.Event(), [None]
    after_id = [None]
    def close():
        stopped.set()
        if after_id[0] is not None:
            window.after_cancel(after_id[0])
        window.destroy()
    def worker():
        try:
            # Coalesce progress: large downloads must not flood the UI event queue.
            last = [-1]
            def progress(done, total, message):
                percent = min(100, int(done * 100 / total)) if total else 0
                key = (percent, message)
                if key != last[0]:
                    last[0] = key
                    events.put(('progress', percent, message))
            path = download_tools(progress=progress, cancel=stopped)
            events.put(('done', path))
        except DownloadCancelled:
            pass
        except Exception as exc:
            events.put(('error', str(exc)))
    def start():
        retry.pack_forget()
        status.set('Conectando…')
        bar['value'] = 0
        threading.Thread(target=worker, daemon=True).start()
    retry = ttk.Button(actions, text='Tentar novamente', command=start)
    ttk.Button(actions, text='Agora não', command=close).pack(side='right')
    def poll():
        after_id[0] = None
        while not events.empty():
            event = events.get_nowait()
            if event[0] == 'progress':
                bar['value'] = event[1]
                status.set(event[2] + (f' {event[1]}%' if event[1] else ''))
            elif event[0] == 'error':
                status.set('Não foi possível preparar o FFmpeg. Confira a conexão e tente novamente.')
                retry.pack(side='left')
            elif event[0] == 'done':
                result[0] = event[1]
                close()
                return
        after_id[0] = window.after(80, poll)
    window.protocol('WM_DELETE_WINDOW', close)
    window.update_idletasks()
    center_window(window)
    if parent is not None:
        window.transient(parent)
        window.grab_set()
    start()
    after_id[0] = window.after(80, poll)
    if parent is None:
        window.mainloop()
    else:
        parent.wait_window(window)
    return result[0]
