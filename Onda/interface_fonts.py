"""Font choices backed by local system fonts; no downloads required."""
import tkinter.font as tkfont

DEFAULT_FONT = 'Padrão do sistema'
FONT_PREVIEW = 'Onda · Sua música, do seu jeito. Aa Bb 123'
FONT_ALIASES = {
    'Sem serifa': ('Arial', 'Segoe UI'),
    'Serifada': ('Georgia', 'Times New Roman'),
    'Monoespaçada': ('Consolas', 'Courier New'),
    'Condensada': ('Arial Narrow', 'Bahnschrift Condensed', 'Arial'),
    'Cursiva': ('Segoe Script', 'Comic Sans MS'),
    'Arredondada': ('Arial Rounded MT Bold', 'Trebuchet MS'),
}


def font_choices(root):
    installed = sorted({name for name in tkfont.families(root) if not name.startswith('@')}, key=str.casefold)
    return (DEFAULT_FONT, *FONT_ALIASES, *(name for name in installed if name not in FONT_ALIASES and name != DEFAULT_FONT))


def font_family(root, selected, original='Segoe UI'):
    if selected == DEFAULT_FONT:
        return original
    installed = {name.casefold(): name for name in tkfont.families(root)}
    candidates = FONT_ALIASES.get(selected, (selected,))
    return next((installed[name.casefold()] for name in candidates if name.casefold() in installed), original)


def valid_font(value):
    return isinstance(value, str) and 0 < len(value) <= 128 and value == value.strip() and not any(ord(c) < 32 for c in value)
