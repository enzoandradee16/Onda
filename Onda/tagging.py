"""Write available catalog fields and provenance to audio, using an atomic replacement."""
import json
import os
from pathlib import Path
import shutil


def fetch_cover(url, *, _attempt=0):
    if not url:
        return None
    import requests
    if not url.startswith("https://"):
        raise ValueError("A URL da capa precisa usar HTTPS.")
    try:
        with requests.get(url, timeout=(5, 20), stream=True) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > 10 * 1024 * 1024:
                    raise ValueError("A capa excede o limite de 10 MB.")
    except requests.RequestException as error:
        status = getattr(getattr(error, 'response', None), 'status_code', None)
        if _attempt < 2 and (status is None or status == 429 or status >= 500):
            import time
            time.sleep(.5 * (_attempt + 1))
            return fetch_cover(url, _attempt=_attempt + 1)
        raise ValueError("Não foi possível obter a capa. Tente novamente.") from None
    if data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    else:
        raise ValueError("A capa retornada não é JPEG nem PNG.")
    return bytes(data), mime


def apply_tags(filename, record, match, cover=None):
    path = Path(filename)
    suffix = path.suffix.lower()
    if suffix not in (".mp3", ".m4a", ".flac"):
        raise ValueError("Metadados automáticos exigem MP3, M4A ou FLAC.")
    provenance = {"catalog": record, "audio_source": match["source_url"],
                  "selection": match.get("selection", "automatic"),
                  "youtube_title": match.get("title"), "match_score": match.get("match_score"),
                  "note": match.get("note") or "Áudio obtido do YouTube; a correspondência é heurística, não comprova a mesma masterização do catálogo."}
    if match.get("artist_alias"):
        provenance["artist_alias"] = match["artist_alias"]
    if match.get("title_alias"):
        provenance["title_alias"] = match["title_alias"]
    if match.get("provider"):
        provenance["provider"] = match["provider"]
        provenance.pop("youtube_title", None)
        provenance["imported_filename"] = match.get("title")
    raw = json.dumps(provenance, ensure_ascii=False, indent=2)
    temporary = path.with_name(path.stem + ".tagging" + suffix)
    sidecar = path.with_suffix(path.suffix + ".metadata.json")
    sidecar_temp = sidecar.with_suffix(".tmp")
    shutil.copyfile(path, temporary)
    try:
        if suffix == ".mp3":
            from mutagen.id3 import (ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TPE2, TDRC,
                                     TRCK, TPOS, TCON, TSRC, TXXX, APIC, WOAS)
            try:
                tags = ID3(temporary)
            except ID3NoHeaderError:
                tags = ID3()
            mapping = {"title": TIT2, "artists": TPE1, "album": TALB, "album_artists": TPE2,
                       "release_date": TDRC, "track_number": TRCK, "disc_number": TPOS, "genre": TCON, "isrc": TSRC}
            for field, frame in mapping.items():
                value = record.get(field)
                if value is not None and value != [] and value != "":
                    tags.add(frame(encoding=3, text=value if isinstance(value, list) else [str(value)]))
            tags.add(WOAS(url=record["source_url"]))
            tags.add(TXXX(encoding=3, desc="ONDA_METADATA", text=[raw]))
            if record.get("explicit") is not None:
                tags.add(TXXX(encoding=3, desc="EXPLICIT", text=[str(record["explicit"]).lower()]))
            if cover:
                tags.delall("APIC")
                tags.add(APIC(encoding=3, mime=cover[1], type=3, desc="Cover", data=cover[0]))
            tags.save(temporary)
        elif suffix == ".m4a":
            from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
            tags = MP4(temporary)
            mapping = {"title": "\u00a9nam", "artists": "\u00a9ART", "album": "\u00a9alb", "album_artists": "aART",
                       "release_date": "\u00a9day", "genre": "\u00a9gen"}
            for field, tag in mapping.items():
                value = record.get(field)
                if value is not None and value != [] and value != "":
                    tags[tag] = value if isinstance(value, list) else [str(value)]
            for field, tag in (("track_number", "trkn"), ("disc_number", "disk")):
                if record.get(field):
                    tags[tag] = [(int(record[field]), 0)]
            if record.get("explicit") is not None:
                tags["rtng"] = [1 if record["explicit"] else 2]
            for field, name in (("isrc", "ISRC"), ("source_url", "CATALOG_URL")):
                if record.get(field):
                    tags["----:com.apple.iTunes:" + name] = [MP4FreeForm(record[field].encode("utf-8"))]
            tags["----:com.apple.iTunes:ONDA_METADATA"] = [MP4FreeForm(raw.encode("utf-8"))]
            if cover:
                tags["covr"] = [MP4Cover(cover[0], imageformat=MP4Cover.FORMAT_JPEG if cover[1] == "image/jpeg" else MP4Cover.FORMAT_PNG)]
            tags.save()
        else:
            from mutagen.flac import FLAC, Picture
            tags = FLAC(temporary)
            mapping = {"title": "title", "artists": "artist", "album": "album", "album_artists": "albumartist",
                       "release_date": "date", "track_number": "tracknumber", "disc_number": "discnumber",
                       "genre": "genre", "isrc": "isrc", "source_url": "catalog_url", "explicit": "explicit"}
            for field, tag in mapping.items():
                value = record.get(field)
                if value is not None and value != [] and value != "":
                    tags[tag] = [str(v) for v in value] if isinstance(value, list) else [str(value)]
            tags["onda_metadata"] = [raw]
            if cover:
                picture = Picture()
                picture.type, picture.mime, picture.desc, picture.data = 3, cover[1], "Cover", cover[0]
                tags.clear_pictures()
                tags.add_picture(picture)
            tags.save()
        sidecar_temp.write_text(raw, encoding="utf-8")
        os.replace(temporary, path)
        os.replace(sidecar_temp, sidecar)
    finally:
        temporary.unlink(missing_ok=True)
        sidecar_temp.unlink(missing_ok=True)
    return str(sidecar)


def optional_cover(url, emit):
    """A remote artwork outage must not discard an otherwise valid recording."""
    try:
        return fetch_cover(url)
    except ValueError as error:
        emit('log', message=str(error) + ' Continuando sem capa.')
        return None
