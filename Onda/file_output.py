"""Safe output directories and explicit collision choices."""
import os
import re
from pathlib import Path
import shutil

from output_rules import EXTRA_ORGANIZATIONS

ORGANIZATIONS = ("Catálogo", "Pasta de destino", "Artista", "Artista / Álbum") + EXTRA_ORGANIZATIONS
DUPLICATES = {"Perguntar": "ask", "Manter ambos": "keep", "Substituir": "replace", "Ignorar": "skip"}


def component(value):
    from yt_dlp.utils import sanitize_filename
    name = sanitize_filename(str(value or "Não informado"), restricted=False).replace("\\", "_").replace("/", "_")
    name = name.strip(" .")[:100].rstrip(" .")
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.I):
        name = "_" + name
    return name if name and name not in (".", "..") else "Não informado"


def destination(config, record=None, info=None):
    root = Path(config["folder"]).expanduser().resolve()
    title = config.get("playlist_title")
    if not title and config.get("playlist") and info:
        title = info.get("playlist_title") or info.get("playlist")
        if not title and (info.get("playlist_id") or info.get("playlist_index") is not None):
            title = "Playlist"
    if title:
        return root / component(title)
    if not record and not info:
        return root
    record = record or {}
    organization = config.get("organization", "Catálogo")
    if organization not in ORGANIZATIONS:
        raise ValueError("Organização de pastas inválida.")
    from output_rules import folder_parts
    parts = folder_parts(organization, config.get("mode"), record, info)
    if parts is not None:
        return root.joinpath(*parts)
    artist = (record.get("artists") or ["Artista desconhecido"])[0]
    if organization == "Artista / Álbum":
        return root / component(artist) / component(record.get("album"))
    if organization == "Artista":
        return root / component(artist)
    if organization == "Catálogo":
        if record.get("platform") not in ("Spotify", "Deezer", "Apple / iTunes"):
            return root
        provider = {"Spotify": "spotify", "Deezer": "deezer"}.get(record["platform"], "apple")
        return root / component(provider + "-" + record["id"])
    return root


def publish(source, folder, policy="keep", choose=None, *, config=None, record=None, info=None):
    source, folder = Path(source), Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    from output_rules import output_filename
    target = folder / (output_filename(source, config, record, info) if config is not None else source.name)
    if target.exists():
        if not target.is_file():
            raise ValueError("Já existe uma pasta com o nome do arquivo de saída.")
        if policy == "ask":
            if choose is None:
                raise ValueError("É necessário escolher como tratar o arquivo duplicado.")
            policy = choose(target)
        if policy == "skip":
            if target.is_file():
                return str(target), True
            policy = "keep"
        if policy not in ("replace", "keep"):
            raise ValueError("Escolha inválida para arquivo duplicado.")
        if policy == "replace":
            os.replace(source, target)
            return str(target), False
    # Exclusive creation also protects against another app creating the file.
    index = 1
    while True:
        candidate = target if index == 1 else target.with_name(f"{target.stem} ({index}){target.suffix}")
        try:
            output = candidate.open("xb")
        except FileExistsError:
            index += 1
            continue
        try:
            with output, source.open("rb") as original:
                shutil.copyfileobj(original, output)
                output.flush()
                os.fsync(output.fileno())
        except BaseException:
            candidate.unlink(missing_ok=True)
            raise
        source.unlink()
        return str(candidate), False
