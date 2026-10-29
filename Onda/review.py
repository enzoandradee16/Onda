"""Validate only user-editable tag fields, leaving source identity intact."""

from pathlib import Path
from urllib.parse import urlsplit

TEXT_FIELDS = ("title", "album", "release_date", "genre")


def apply_review(record, changes):
    if not isinstance(changes, dict):
        raise ValueError("Revisão de metadados inválida.")
    result = dict(record)
    for field in TEXT_FIELDS:
        value = changes.get(field, result.get(field))
        if value is not None and (
            not isinstance(value, str) or len(value) > 1000 or "\x00" in value
        ):
            raise ValueError("Campo de metadados inválido: " + field)
        result[field] = value.strip() if value else None
    artists = changes.get("artists", record.get("artists"))
    if (
        not isinstance(artists, list)
        or not artists
        or any(not isinstance(a, str) or not a.strip() or len(a) > 200 for a in artists)
    ):
        raise ValueError("Informe pelo menos um artista.")
    if not result.get("title"):
        raise ValueError("Informe o título da música.")
    result["artists"] = [a.strip() for a in artists]
    for field in ("track_number", "disc_number"):
        value = changes.get(field, result.get(field))
        if value is not None and (type(value) is not int or not 1 <= value <= 9999):
            raise ValueError("Número de faixa/disco inválido.")
        result[field] = value
    if "cover_url" in changes:
        url = changes["cover_url"]
        if url and (
            not isinstance(url, str)
            or urlsplit(url).scheme != "https"
            or len(url) > 4096
        ):
            raise ValueError("Use uma URL HTTPS para a capa.")
        result["cover_url"] = url or None
    if changes.get("cover_path"):
        path = Path(changes["cover_path"])
        if (
            not path.is_file()
            or path.suffix.lower() not in (".jpg", ".jpeg", ".png")
            or path.stat().st_size > 10 * 1024 * 1024
        ):
            raise ValueError("Escolha uma capa JPEG/PNG de até 10 MB.")
        result["cover_path"] = str(path.resolve())
    result["user_edited"] = True
    return result


def local_cover(path):
    data = Path(path).read_bytes()
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("Capa muito grande.")
    if data.startswith(b"\xff\xd8\xff"):
        return data, "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return data, "image/png"
    raise ValueError("A capa precisa ser JPEG ou PNG.")
