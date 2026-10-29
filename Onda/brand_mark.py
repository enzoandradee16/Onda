"""ONDA's continuous wave, shared by native icons and generated vector resources."""

WIDTH, HEIGHT = 100, 64
STROKE = 4.5
START = (4, 32)
CURVES = (
    (8, 24, 10, 25, 13, 32),
    (16, 39, 19, 41, 22, 31),
    (25, 12, 29, 11, 30, 32),
    (32, 57, 37, 57, 40, 21),
    (43, -5, 48, -3, 48, 30),
    (48, 73, 54, 73, 58, 28),
    (62, 3, 66, 12, 67, 31),
    (68, 52, 73, 50, 76, 31),
    (79, 17, 82, 20, 85, 31),
    (88, 39, 91, 38, 96, 32),
)
SVG_PATH = 'M 4 32 ' + ' '.join('C ' + ' '.join(map(str, curve)) for curve in CURVES)


def points(steps=48):
    """Sample the cubic path for raster renderers without an SVG dependency."""
    x0, y0 = START
    result = [START]
    for x1, y1, x2, y2, x3, y3 in CURVES:
        for index in range(1, steps + 1):
            t = index / steps
            s = 1 - t
            result.append(
                (
                    s**3 * x0 + 3 * s * s * t * x1 + 3 * s * t * t * x2 + t**3 * x3,
                    s**3 * y0 + 3 * s * s * t * y1 + 3 * s * t * t * y2 + t**3 * y3,
                )
            )
        x0, y0 = x3, y3
    return result


def icon(size, accent='#79e2c4', background='#10151e'):
    """Antialiased application icon, also used by the Windows tray and taskbar."""
    from PIL import Image, ImageDraw

    scale = max(4, size / 96 * 4)
    side = round(96 * scale)
    image = Image.new('RGBA', (side, side))
    draw = ImageDraw.Draw(image)
    if background is not None:
        draw.rounded_rectangle(
            (2 * scale, 2 * scale, 94 * scale, 94 * scale),
            radius=22 * scale,
            fill=background,
        )
    path = [((6 + x * 0.84) * scale, (16 + y) * scale) for x, y in points()]
    width = max(1, round(STROKE * 0.84 * scale))
    draw.line(path, fill=accent, width=width, joint='curve')
    radius = width / 2
    for x, y in (path[0], path[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=accent)
    return image.resize((size, size), Image.Resampling.LANCZOS)
