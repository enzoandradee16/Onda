"""Image export options shared by preview and downloads."""
import base64
import io
from pathlib import Path
from PIL import Image, ImageOps, ImageSequence

FORMATS = {'Original': None, 'JPG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP', 'SVG': 'SVG'}


IMAGE_SIZES = {'Original': (0, 0), 'Até 1920 × 1080': (1920, 1080), 'Até 1280 × 720': (1280, 720), 'Até 1080 × 1080': (1080, 1080), 'Personalizado': None}

def validate_options(options):
    if not isinstance(options, dict) or options.get('format') not in FORMATS:
        raise ValueError('Escolha um formato de imagem válido.')
    width, height = options.get('width', 0), options.get('height', 0)
    if any(type(n) is not int or n < 0 or n > 16384 for n in (width, height)):
        raise ValueError('Use dimensões entre 1 e 16384 pixels, ou tamanho original.')
    if bool(width) != bool(height):
        raise ValueError('Informe largura e altura.')
    if type(options.get('keep_ratio', True)) is not bool:
        raise ValueError('Opção de proporção inválida.')
    return {**options, 'width': width, 'height': height}


def output_size(size, options):
    width, height = options['width'], options['height']
    if not width:
        return size
    if not options.get('keep_ratio', True):
        return width, height
    # A bounding box preserves the entire image and never enlarges it.
    scale = min(width / size[0], height / size[1], 1)
    return max(1, round(size[0] * scale)), max(1, round(size[1] * scale))


def transform_image(source, options, emit=lambda *a, **kw: None):
    options = validate_options(options)
    if options['format'] == 'Original' and not options['width']:
        return Path(source)
    source = Path(source)
    if options['format'] == 'SVG':
        with Image.open(source) as image:
            animated = getattr(image, 'n_frames', 1) > 1
            frame = ImageOps.exif_transpose(image).convert('RGBA')
            frame = frame.resize(output_size(frame.size, options), Image.Resampling.LANCZOS)
            payload = io.BytesIO()
            frame.save(payload, format='PNG')
        encoded = base64.b64encode(payload.getvalue()).decode('ascii')
        width, height = frame.size
        target = source.with_name(source.stem + '.converted.svg')
        target.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            '<desc>Imagem raster incorporada; sem vetorização automática.</desc>'
            f'<image width="{width}" height="{height}" href="data:image/png;base64,{encoded}" xlink:href="data:image/png;base64,{encoded}"/></svg>', encoding='utf-8')
        final = source.with_suffix('.svg')
        target.replace(final)
        if source != final:
            source.unlink(missing_ok=True)
        emit('log', message=f'Imagem exportada: {width} × {height} · SVG com imagem incorporada, sem vetorização.')
        if animated:
            emit('log', message='SVG salva somente o primeiro quadro da imagem animada.')
        return final
    with Image.open(source) as image:
        fmt = FORMATS[options['format']] or image.format
        if fmt not in ('JPEG', 'PNG', 'WEBP', 'GIF', 'AVIF'):
            raise ValueError('Para redimensionar esta imagem, escolha JPG, PNG ou WebP.')
        ext = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp', 'GIF': '.gif', 'AVIF': '.avif'}[fmt]
        target = source.with_name(source.stem + '.converted' + ext)
        frames, durations = [], []
        animated = getattr(image, 'n_frames', 1) > 1
        for frame in ImageSequence.Iterator(image):
            value = ImageOps.exif_transpose(frame).convert('RGBA')
            value = value.resize(output_size(value.size, options), Image.Resampling.LANCZOS)
            if fmt == 'JPEG':
                background = Image.new('RGB', value.size, 'white')
                background.paste(value, mask=value.getchannel('A'))
                value = background
            frames.append(value)
            durations.append(frame.info.get('duration', 100))
            if not animated or fmt in ('JPEG', 'AVIF'):
                break
        args = {'format': fmt}
        if fmt in ('JPEG', 'WEBP'):
            args['quality'] = 95
        if image.info.get('icc_profile') and fmt != 'GIF':
            args['icc_profile'] = image.info['icc_profile']
        if len(frames) > 1:
            args.update(save_all=True, append_images=frames[1:], duration=durations, loop=image.info.get('loop', 0))
        if animated and len(frames) == 1:
            emit('log', message='Este formato salva somente o primeiro quadro da imagem animada.')
        frames[0].save(target, **args)
    final = source.with_suffix(ext)
    target.replace(final)
    if source != final:
        source.unlink(missing_ok=True)
    emit('log', message=f'Imagem exportada: {frames[0].width} × {frames[0].height} · {fmt}.')
    return final


def open_preview(path):
    """Open raster output or the embedded PNG of an SVG generated here."""
    path = Path(path)
    if path.suffix.lower() != '.svg':
        return Image.open(path)
    import xml.etree.ElementTree as ET
    image = ET.fromstring(path.read_bytes()).find('{http://www.w3.org/2000/svg}image')
    value = image.get('href', '') if image is not None else ''
    prefix = 'data:image/png;base64,'
    if not value.startswith(prefix):
        raise ValueError('Esta prévia SVG não contém uma imagem PNG incorporada.')
    return Image.open(io.BytesIO(base64.b64decode(value[len(prefix):], validate=True)))
