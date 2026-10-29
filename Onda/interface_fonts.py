"""Font choices backed by local system fonts; no downloads required."""

import tkinter.font as tkfont

FONT_SIZES = ('85%', '100%', '115%', '130%')


def font_scale(value):
    return int(value[:-1]) / 100 if value in FONT_SIZES else 1.0


DEFAULT_FONT = 'ONDA Modern'
FONT_PREVIEW = 'Onda · Sua música, do seu jeito. Aa Bb 123'
FONT_ALIASES = {
    'ONDA Legacy': ('Segoe UI', 'Arial'),
    'Sem serifa': ('Arial', 'Segoe UI'),
    'Serifada': ('Georgia', 'Times New Roman'),
    'Monoespaçada': ('Consolas', 'Courier New'),
    'Condensada': ('Arial Narrow', 'Bahnschrift Condensed', 'Arial'),
    'Cursiva': ('Segoe Script', 'Comic Sans MS'),
    'Arredondada': ('Arial Rounded MT Bold', 'Trebuchet MS'),
}


def font_choices(root):
    installed = sorted(
        {name for name in tkfont.families(root) if not name.startswith('@')},
        key=str.casefold,
    )
    return (
        DEFAULT_FONT,
        *FONT_ALIASES,
        *(
            name
            for name in installed
            if name not in FONT_ALIASES and name != DEFAULT_FONT
        ),
    )


def font_family(root, selected, original='Segoe UI'):
    if selected == DEFAULT_FONT:
        return 'Inter' if 'Inter' in tkfont.families(root) else original
    installed = {name.casefold(): name for name in tkfont.families(root)}
    candidates = FONT_ALIASES.get(selected, (selected,))
    return next(
        (
            installed[name.casefold()]
            for name in candidates
            if name.casefold() in installed
        ),
        original,
    )


def qt_font_family(selected=DEFAULT_FONT):
    if selected in (DEFAULT_FONT, 'Padrão do sistema'):
        return 'Inter'
    if selected == 'ONDA Legacy':
        return 'Segoe UI'
    return FONT_ALIASES.get(selected, (selected,))[0]


def register_qt_fonts():
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase

    path = Path(__file__).parent / 'assets/fonts/Inter.ttf'
    if 'Inter' not in QFontDatabase.families():
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            raise ValueError('Não foi possível carregar a fonte Inter.')


def valid_font(value):
    return (
        isinstance(value, str)
        and 0 < len(value) <= 128
        and value == value.strip()
        and not any(ord(c) < 32 for c in value)
    )
