"""Local U2NetP segmentation; weights are downloaded only when requested."""

from array import array
import hashlib
import math
import os
from pathlib import Path
import sys
import tempfile
import threading

from PIL import Image, ImageChops

MODEL_URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx'
MODEL_SHA256 = '309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8'
_lock = threading.Lock()
_native_predict = None


def model_path(emit):
    from cache_cleanup import root_path

    folder = root_path() / 'tools' / 'image-background'
    target = folder / 'u2netp.onnx'
    if (
        target.is_file()
        and hashlib.sha256(target.read_bytes()).hexdigest() == MODEL_SHA256
    ):
        return target
    import requests

    folder.mkdir(parents=True, exist_ok=True)
    emit('log', message='Baixando recurso de remoção de fundo…')
    descriptor, temporary = tempfile.mkstemp(prefix='model-', suffix='.tmp', dir=folder)
    try:
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(descriptor, 'wb') as output, requests.get(
            MODEL_URL, stream=True, timeout=(15, 30)
        ) as response:
            response.raise_for_status()
            for block in response.iter_content(65536):
                if not block:
                    continue
                size += len(block)
                if size > 6 * 1024 * 1024:
                    raise ValueError(
                        'O recurso de remoção de fundo não pôde ser verificado.'
                    )
                output.write(block)
                digest.update(block)
                emit('progress', percent=min(35, round(size / 4700000 * 35)))
        if digest.hexdigest() != MODEL_SHA256:
            raise ValueError('O recurso de remoção de fundo não pôde ser verificado.')
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def _desktop_predict(model, values):
    import subprocess
    from audio_tools import process_options

    base = Path(sys.executable).resolve().parent.parent
    runtime = Path(
        os.environ.get('ONDA_BACKGROUND_RUNTIME') or base / 'image-background-node'
    )
    node = base / 'node' / 'node.exe'
    if (
        not node.is_file()
        or not (runtime / 'node_modules/onnxruntime-node/package.json').is_file()
    ):
        raise ValueError(
            'O recurso de remoção de fundo não está instalado. Atualize o ONDA.'
        )
    result = subprocess.run(
        [
            str(node),
            str(Path(__file__).with_name('image_background_runner.cjs')),
            str(runtime),
            str(model),
        ],
        input=values,
        capture_output=True,
        timeout=60,
        **process_options()
    )
    if result.returncode or len(result.stdout) != 320 * 320 * 4:
        raise ValueError('Não foi possível remover o fundo desta imagem.')
    return result.stdout


def remove_background(image, emit=lambda *a, **kw: None):
    # One bounded inference at a time, independently from playback workers.
    with _lock:
        model = model_path(emit)
        emit('log', message='Removendo fundo…')
        emit('progress', percent=40)
        rgb = image.resize((320, 320), Image.Resampling.LANCZOS).convert('RGB')
        pixels = rgb.tobytes()
        maximum = max(pixels) or 1
        values = array('f')
        for channel, (mean, std) in enumerate(
            zip((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
        ):
            values.extend(
                (pixels[index] / maximum - mean) / std
                for index in range(channel, len(pixels), 3)
            )
        if sys.byteorder != 'little':
            values.byteswap()
        predict = _native_predict or _desktop_predict
        result = array('f')
        result.frombytes(predict(model, values.tobytes()))
        if sys.byteorder != 'little':
            result.byteswap()
        if len(result) != 320 * 320 or not all(
            math.isfinite(value) for value in result
        ):
            raise ValueError('Não foi possível remover o fundo desta imagem.')
        low, high = min(result), max(result)
        scale = 255 / (high - low) if high > low else 0
        mask = Image.frombytes(
            'L',
            (320, 320),
            bytes(max(0, min(255, round((value - low) * scale))) for value in result),
        )
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)
        output = image.convert('RGBA')
        output.putalpha(ImageChops.multiply(output.getchannel('A'), mask))
        emit('progress', percent=95)
        return output
