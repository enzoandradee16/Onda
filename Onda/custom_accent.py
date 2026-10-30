"""Validate opaque RGB accents and keep their hue readable on interface surfaces."""

import re


def normalize_color(value):
    if not isinstance(value, str):
        return ''
    value = value.strip()
    return (
        '#' + value.lstrip('#').upper()
        if re.fullmatch(r'#?[0-9a-fA-F]{6}', value)
        else ''
    )


def luminance(color):
    rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return sum(v * weight for v, weight in zip(rgb, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def readable_accent(value, dark):
    color = normalize_color(value)
    if not color:
        return ''
    surface = '#2b3744' if dark else '#e7edf4'
    target = 255 if dark else 0
    for _ in range(64):
        if contrast(color, surface) >= 4.5:
            break
        rgb = [
            round(int(color[i : i + 2], 16) * 0.94 + target * 0.06) for i in (1, 3, 5)
        ]
        color = '#' + ''.join(f'{v:02X}' for v in rgb)
    return color


def accent_ink(color):
    return (
        '#101419'
        if contrast(color, '#101419') >= contrast(color, '#ffffff')
        else '#ffffff'
    )
