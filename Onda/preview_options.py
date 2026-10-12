"""Shared choices for playback limits, measured in output seconds."""
PREVIEW_DURATIONS = tuple(f"{seconds} segundos" for seconds in (10, 15, 25, 30, 45, 60, 90, 120, 180))


def preview_seconds(value):
    if value not in PREVIEW_DURATIONS:
        raise ValueError("Escolha uma duração de prévia válida nas configurações.")
    return int(value.split()[0])
