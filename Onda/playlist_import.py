"""Public playlist enumeration only; each track goes through the normal worker."""
import json
import re
from urllib.parse import parse_qs, urlsplit

from metadata import MetadataError, deezer_record
from spotify_public import EmbedParser

from playlist_options import DEFAULT_PLAYLIST_LIMIT, playlist_limit

LIMIT = DEFAULT_PLAYLIST_LIMIT


def spotify_playlist(html, playlist_id, limit=LIMIT):
    limit = playlist_limit(limit)
    parser = EmbedParser()
    parser.feed(html)
    try:
        entity = json.loads("".join(parser.parts))["props"]["pageProps"]["state"]["data"]["entity"]
        if entity.get("id") != playlist_id or entity.get("type") != "playlist":
            raise ValueError()
        rows, seen = [], set()
        for row in (entity.get("trackList") or [])[:limit]:
            uri = row.get("uri", "") if isinstance(row, dict) else ""
            match = re.fullmatch(r"spotify:track:([A-Za-z0-9]{22})", uri)
            if not match or uri in seen:
                continue
            seen.add(uri)
            rows.append({"title": row.get("title") or "Faixa Spotify", "artists": [row.get("subtitle") or ""],
                         "source_url": "https://open.spotify.com/track/" + match[1], "duration_ms": row.get("duration")})
        if not rows:
            raise ValueError()
        return {"title": entity.get("title") or "Playlist Spotify", "tracks": rows,
                "note": f"Lista pública Spotify: pode mostrar apenas parte da playlist, mesmo com um limite maior. Máximo configurado: {limit}."}
    except (ValueError, TypeError, KeyError, AttributeError):
        raise MetadataError("A playlist não está disponível no embed público Spotify. Tente uma playlist pública diferente ou importe um TXT/M3U com os links das faixas.") from None


def load_playlist(url, client, limit=LIMIT):
    limit = playlist_limit(limit)
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise MetadataError("Use o link HTTPS de uma playlist pública.")
    parts = parsed.path.strip("/").split("/")
    if host in ("deezer.com", "www.deezer.com"):
        if parts and re.fullmatch(r"[a-z]{2}", parts[0]):
            parts = parts[1:]
        if len(parts) != 2 or parts[0] != "playlist" or not parts[1].isdigit():
            raise MetadataError("Use um link Deezer /playlist/ID.")
        data = client.get_json("https://api.deezer.com/playlist/" + parts[1])
        if data.get("error"):
            raise MetadataError("Playlist Deezer indisponível ou privada.")
        records, offset = [], 0
        while offset < limit:
            tracks = client.get_json("https://api.deezer.com/playlist/" + parts[1] + "/tracks",
                                     params={"limit": min(100, limit - offset), "index": offset})
            if tracks.get("error"):
                raise MetadataError("Não foi possível carregar todas as páginas da playlist Deezer. Tente novamente.")
            page = tracks.get("data") or []
            if not page:
                break
            for row in page[:limit - offset]:
                if isinstance(row, dict) and str(row.get("id", "")).isdigit() and row.get("title"):
                    records.append(deezer_record(row, str(row["id"]), "https://www.deezer.com/track/" + str(row["id"])))
            offset += len(page)
            if not tracks.get("next"):
                break
        return {"title": data.get("title") or "Playlist Deezer", "tracks": records,
                "note": f"Até {limit} faixas por importação. Itens indisponíveis são omitidos."}
    if host == "open.spotify.com":
        if parts and parts[0].startswith("intl-"):
            parts = parts[1:]
        if len(parts) != 2 or parts[0] != "playlist" or not re.fullmatch(r"[A-Za-z0-9]{22}", parts[1]):
            raise MetadataError("Use um link Spotify /playlist/ID.")
        with client.request("https://open.spotify.com/embed/playlist/" + parts[1]) as response:
            return spotify_playlist(response.text, parts[1], limit=limit)
    if host in ("www.youtube.com", "youtube.com", "music.youtube.com") and parse_qs(parsed.query).get("list"):
        from yt_dlp import YoutubeDL
        with YoutubeDL({"quiet": True, "extract_flat": "in_playlist", "skip_download": True,
                       "playlistend": limit, "socket_timeout": 20, "retries": 1,
                       "js_runtimes": {"deno": {}, "node": {}}}) as downloader:
            result = downloader.extract_info("https://www.youtube.com/playlist?list=" + parse_qs(parsed.query)["list"][0], download=False)
        tracks = [{"title": row.get("title") or "Vídeo", "artists": [row.get("uploader") or row.get("channel") or ""],
                   "source_url": "https://www.youtube.com/watch?v=" + row["id"], "duration_ms": (row.get("duration") or 0) * 1000}
                  for row in (result or {}).get("entries", []) if row and re.fullmatch(r"[A-Za-z0-9_-]{11}", row.get("id", ""))]
        return {"title": result.get("title") or "Playlist YouTube", "tracks": tracks[:limit], "note": f"YouTube: os próprios vídeos da playlist serão usados; até {limit} itens."}
    raise MetadataError("Importe uma playlist pública Deezer, Spotify ou YouTube, ou um TXT/M3U com links individuais.")


def load_text(text, limit=LIMIT):
    limit = playlist_limit(limit)
    from metadata import is_streaming_link
    from engine import validate_url
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not is_streaming_link(line):
            validate_url(line)
        records.append({"source_url": line, "title": line, "artists": []})
        if len(records) == limit:
            break
    return {"title": "Lista de links", "tracks": records, "note": f"Até {limit} links individuais. Os metadados são consultados ao baixar."}
