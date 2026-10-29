"""Configurable bounds shared by playlist import and downloads."""

DEFAULT_PLAYLIST_LIMIT = 1000
PLAYLIST_LIMITS = tuple(str(value) for value in (100, 250, 500, 1000, 2000, 5000))


def playlist_limit(value=DEFAULT_PLAYLIST_LIMIT):
    if type(value) is int and 1 <= value <= 5000:
        return value
    if (
        isinstance(value, str)
        and len(value) <= 4
        and value.isascii()
        and value.isdigit()
        and 1 <= int(value) <= 5000
    ):
        return int(value)
    raise ValueError("Escolha um limite de playlist entre 1 e 5.000 itens.")
