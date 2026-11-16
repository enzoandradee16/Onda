"""Bounded PCM decoding and the official Chromaprint C API on Android."""
import ctypes as c
import os
from pathlib import Path
import subprocess
import tempfile
import time


def fingerprint(source, cancel):
    from audio_library import read_audio
    from audio_tools import executable, process_options

    duration = round(read_audio(source)['duration'])
    if duration <= 0:
        raise ValueError('Não foi possível determinar a duração do áudio.')
    library = c.CDLL(os.environ['ONDA_CHROMAPRINT'])
    library.chromaprint_new.argtypes = [c.c_int]
    library.chromaprint_new.restype = c.c_void_p
    library.chromaprint_start.argtypes = [c.c_void_p, c.c_int, c.c_int]
    library.chromaprint_feed.argtypes = [c.c_void_p, c.POINTER(c.c_int16), c.c_int]
    library.chromaprint_finish.argtypes = [c.c_void_p]
    library.chromaprint_get_fingerprint.argtypes = [c.c_void_p, c.POINTER(c.c_void_p)]
    library.chromaprint_dealloc.argtypes = [c.c_void_p]
    library.chromaprint_free.argtypes = [c.c_void_p]
    library.chromaprint_dealloc.restype = None
    library.chromaprint_free.restype = None
    context = library.chromaprint_new(1)
    if not context:
        raise RuntimeError('Não foi possível iniciar o Chromaprint.')
    encoded = c.c_void_p()
    try:
        command = [executable('ffmpeg'), '-nostdin', '-v', 'error', '-i', str(Path(source).resolve()),
                   '-t', '120', '-vn', '-ac', '1', '-ar', '11025', '-f', 's16le', 'pipe:1']
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, **process_options())
            started = time.monotonic()
            try:
                while True:
                    if cancel.is_set():
                        raise InterruptedError('Operação cancelada.')
                    if time.monotonic() - started > 45:
                        raise TimeoutError('A preparação do áudio excedeu o tempo limite.')
                    try:
                        pcm, _ = process.communicate(timeout=.1)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if process.returncode or len(pcm) < 22050 or len(pcm) > 11025 * 2 * 121:
                    raise ValueError('Não foi possível gerar a impressão digital do áudio.')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        samples = (c.c_int16 * (len(pcm) // 2)).from_buffer_copy(pcm)
        if not (library.chromaprint_start(context, 11025, 1)
                and library.chromaprint_feed(context, samples, len(samples))
                and library.chromaprint_finish(context)
                and library.chromaprint_get_fingerprint(context, c.byref(encoded))):
            raise RuntimeError('Não foi possível gerar a impressão digital do áudio.')
        return {'duration': duration, 'fingerprint': c.string_at(encoded).decode('ascii')}
    finally:
        if encoded.value:
            library.chromaprint_dealloc(encoded)
        library.chromaprint_free(context)
