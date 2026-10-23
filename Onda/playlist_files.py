"""Portable playlist interchange: links only, never credentials or media."""
import csv
import io
import re

from metadata import MetadataError, is_streaming_link, parse_link
from engine import validate_url
from playlist_options import DEFAULT_PLAYLIST_LIMIT, playlist_limit


def track_url(value):
    value = value.strip()
    if is_streaming_link(value):
        return parse_link(value)[3]
    return validate_url(value)


def load_csv(text, limit=DEFAULT_PLAYLIST_LIMIT):
    limit = playlist_limit(limit)
    text = text.lstrip("\ufeff")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = {re.sub(r"[^a-z0-9]", "", name.lower()): name for name in (reader.fieldnames or []) if name}
    link = next((headers[key] for key in ("trackuri", "trackurl", "spotifyuri", "spotifyurl", "url", "uri") if key in headers), None)
    if not link:
        raise MetadataError("CSV sem coluna de links. Use o CSV do Exportify (Track URI) ou uma coluna Track URL/URL.")
    def field(row, *keys):
        return next((row.get(headers[key], "") or "" for key in keys if key in headers), "")
    rows, skipped, capped = [], 0, False
    try:
        for row in reader:
            if len(rows) == limit:
                capped = True
                break
            try:
                url = track_url(row.get(link) or "")
            except (ValueError, TypeError):
                skipped += 1
                continue
            duration = field(row, "durationms", "trackdurationms")
            rows.append({"source_url": url, "title": field(row, "trackname", "title", "name") or url,
                         "artists": [value.strip() for value in field(row, "artistnames", "artistname", "artists", "artist").split(";") if value.strip()],
                         "duration_ms": int(duration) if duration.isdigit() else None})
    except csv.Error:
        raise MetadataError("CSV inválido. Exporte o arquivo novamente em UTF-8.") from None
    if not rows:
        raise MetadataError("O CSV não contém links de músicas ou vídeos válidos.")
    note = f"CSV: {len(rows)} itens importados; {skipped} linhas inválidas/indisponíveis ignoradas."
    if capped:
        note += f" Limite de {limit} atingido; aumente-o em Configurações para importar mais."
    return {"title": "Playlist importada", "tracks": rows, "note": note}


def export_text(rows, m3u=False):
    lines = ["#EXTM3U"] if m3u else []
    for row in rows:
        url = track_url(row["source_url"])
        if any(char in url for char in "\r\n"):
            raise MetadataError("Link inválido na playlist.")
        if m3u:
            label = " - ".join(filter(None, [", ".join(row.get("artists", [])), row.get("title")]))
            label = label.replace("\r", " ").replace("\n", " ")
            duration = row.get("duration_ms")
            seconds = int(duration / 1000) if isinstance(duration, (int, float)) and duration >= 0 else -1
            lines.append(f"#EXTINF:{seconds},{label}")
        lines.append(url)
    return "\n".join(lines) + "\n"


def export_local_text(rows, m3u=False):
    """Export history paths for local players, independently of downloadable URLs."""
    from pathlib import Path
    lines = ["#EXTM3U"] if m3u else []
    for row in rows:
        path = str(Path(row['path']).resolve())
        if any(char in path for char in '\r\n'):
            raise ValueError('Caminho inválido na playlist.')
        if m3u:
            title = str(row.get('title') or row.get('name') or Path(path).stem)
            lines.append('#EXTINF:-1,' + title.replace('\r', ' ').replace('\n', ' '))
        lines.append(path)
    return '\n'.join(lines) + '\n'
