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


def backdrop_opacity(rgb, dark):
    if not dark:
        return .38
    base = (16, 20, 25)
    low, high = 0.0, .56
    for _ in range(10):
        weight = (low + high) / 2
        composite = '#' + ''.join(
            f'{round(start * (1 - weight) + end * weight):02x}'
            for start, end in zip(base, rgb)
        )
        if luminance(composite) <= .17:
            low = weight
        else:
            high = weight
    return low


def readable_accent(value, dark, background=None):
    color = normalize_color(value)
    if not color:
        return ''
    surface = '#2b3744' if dark else '#e7edf4'
    target = 255 if dark else 0
    for _ in range(64):
        if contrast(color, surface) >= 4.5 and (
            not background or contrast(color, background) >= 4.5
        ):
            break
        channels = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
        rgb = [round(channel * .94 + target * .06) for channel in channels]
        if background and rgb == channels:
            rgb = [channel + (target > channel) - (target < channel) for channel in channels]
        color = '#' + ''.join(f'{v:02X}' for v in rgb)
    return color


def accent_ink(color):
    return (
        '#101419'
        if contrast(color, '#101419') >= contrast(color, '#ffffff')
        else '#ffffff'
    )
