"""Image export options shared by preview and downloads."""

import base64
import io
import os
import tempfile
from pathlib import Path
from PIL import Image, ImageOps, ImageSequence, ImageColor

FORMATS = {'Original': None, 'JPG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP', 'SVG': 'SVG'}


IMAGE_SIZES = {
    'Original': (0, 0),
    'Até 1920 × 1080': (1920, 1080),
    'Até 1280 × 720': (1280, 720),
    'Até 1080 × 1080': (1080, 1080),
    'Personalizado': None,
}


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
    if type(options.get('remove_background', False)) is not bool:
        raise ValueError('Opção de remoção de fundo inválida.')
    if options.get('remove_background') and options['format'] not in (
        'PNG',
        'WebP',
        'SVG',
    ):
        options = dict(options, format='PNG')
    if options.get('rotation', 0) not in (0, 90, 180, 270):
        raise ValueError('Rotação inválida.')
    if options.get('crop', 'Original') not in (
        'Original',
        '1:1',
        '4:3',
        '16:9',
        '9:16',
    ):
        raise ValueError('Proporção de recorte inválida.')
    if options.get('background', 'transparent') not in (
        'transparent',
        'color',
        'image',
    ):
        raise ValueError('Fundo inválido.')
    if options.get('background') == 'color':
        ImageColor.getrgb(options.get('background_color', '#ffffff'))
    if (
        options.get('background') == 'image'
        and not Path(options.get('background_image', '')).is_file()
    ):
        raise ValueError('Escolha uma imagem de fundo.')
    return {**options, 'width': width, 'height': height}


def has_image_edits(options):
    return bool(
        options.get('rotation')
        or options.get('crop', 'Original') != 'Original'
        or options.get('background', 'transparent') != 'transparent'
    )


def edit_frame(image, options):
    if options.get('rotation'):
        image = image.rotate(-options['rotation'], expand=True)
    crop = options.get('crop', 'Original')
    if crop != 'Original':
        a, b = map(int, crop.split(':'))
        width, height = image.size
        if width / height > a / b:
            width = max(1, round(height * a / b))
        else:
            height = max(1, round(width * b / a))
        left, top = (image.width - width) // 2, (image.height - height) // 2
        image = image.crop((left, top, left + width, top + height))
    background = options.get('background', 'transparent')
    if background == 'color':
        base = Image.new(
            'RGBA',
            image.size,
            ImageColor.getrgb(options.get('background_color', '#ffffff')),
        )
        base.alpha_composite(image)
        image = base
    elif background == 'image':
        with Image.open(options['background_image']) as source:
            base = ImageOps.fit(
                ImageOps.exif_transpose(source).convert('RGBA'),
                image.size,
                method=Image.Resampling.LANCZOS,
            )
        base.alpha_composite(image)
        image = base
    return image


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
    if (
        options['format'] == 'Original'
        and not options['width']
        and not options.get('remove_background')
        and not has_image_edits(options)
    ):
        return Path(source)
    source = Path(source)
    # Encode in an isolated directory; neither partial files nor format changes
    # may overwrite an unrelated neighbor of the source.
    with tempfile.TemporaryDirectory(
        prefix='.onda-image-', dir=source.parent
    ) as directory:
        output = _render_image(source, options, Path(directory), emit)
        if output.suffix.lower() == source.suffix.lower():
            os.replace(output, source)
            return source
        from file_output import publish

        final, _ = publish(output, source.parent, 'keep')
        source.unlink()
        return Path(final)


def _render_image(source, options, directory, emit):
    if options['format'] == 'SVG':
        with Image.open(source) as image:
            animated = getattr(image, 'n_frames', 1) > 1
            frame = ImageOps.exif_transpose(image).convert('RGBA')
            if options.get('remove_background'):
                from image_background import remove_background

                frame = remove_background(frame, emit)
            frame = edit_frame(frame, options)
            frame = frame.resize(
                output_size(frame.size, options), Image.Resampling.LANCZOS
            )
            payload = io.BytesIO()
            frame.save(payload, format='PNG')
        encoded = base64.b64encode(payload.getvalue()).decode('ascii')
        width, height = frame.size
        target = directory / (source.stem + '.svg')
        target.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            '<desc>Imagem raster incorporada; sem vetorização automática.</desc>'
            f'<image width="{width}" height="{height}" href="data:image/png;base64,{encoded}"/></svg>',
            encoding='utf-8',
        )
        emit(
            'log',
            message=f'Imagem exportada: {width} × {height} · SVG com imagem incorporada, sem vetorização.',
        )
        if animated:
            emit(
                'log', message='SVG salva somente o primeiro quadro da imagem animada.'
            )
        return target
    with Image.open(source) as image:
        fmt = FORMATS[options['format']] or image.format
        if fmt not in ('JPEG', 'PNG', 'WEBP', 'GIF', 'AVIF'):
            raise ValueError(
                'Para redimensionar esta imagem, escolha JPG, PNG ou WebP.'
            )
        ext = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'WEBP': '.webp',
            'GIF': '.gif',
            'AVIF': '.avif',
        }[fmt]
        target = directory / (source.stem + ext)
        frames, durations = [], []
        animated = getattr(image, 'n_frames', 1) > 1
        for frame in ImageSequence.Iterator(image):
            value = ImageOps.exif_transpose(frame).convert('RGBA')
            if options.get('remove_background'):
                from image_background import remove_background

                value = remove_background(value, emit)
            value = edit_frame(value, options)
            value = value.resize(
                output_size(value.size, options), Image.Resampling.LANCZOS
            )
            if fmt == 'JPEG':
                background = Image.new('RGB', value.size, 'white')
                background.paste(value, mask=value.getchannel('A'))
                value = background
            frames.append(value)
            durations.append(frame.info.get('duration', 100))
            if (
                not animated
                or fmt in ('JPEG', 'AVIF')
                or options.get('remove_background')
            ):
                break
        args = {'format': fmt}
        if fmt in ('JPEG', 'WEBP'):
            args['quality'] = 95
        if image.info.get('icc_profile') and fmt != 'GIF':
            args['icc_profile'] = image.info['icc_profile']
        if len(frames) > 1:
            args.update(
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=image.info.get('loop', 0),
            )
        if animated and len(frames) == 1:
            emit(
                'log',
                message='Este formato salva somente o primeiro quadro da imagem animada.',
            )
        frames[0].save(target, **args)
    emit(
        'log',
        message=f'Imagem exportada: {frames[0].width} × {frames[0].height} · {fmt}.',
    )
    return target


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
    return Image.open(io.BytesIO(base64.b64decode(value[len(prefix) :], validate=True)))
