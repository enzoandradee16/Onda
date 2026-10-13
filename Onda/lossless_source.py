"""Direct public FLAC source. No browser session, secrets or lossy fallback."""
from pathlib import Path
import re
import tempfile
import time
import requests

BASE = "https://tracks.monochrome.st"
MAX_FILE_SIZE = 1024 * 1024 * 1024


def rank_matches(record, tracks):
    from matching import score_candidate
    ranked = []
    seen = set()
    for row in tracks:
        if not isinstance(row, dict) or row.get("playable") is not True:
            continue
        identity = str(row.get("id") or row.get("trackId") or "")
        if not re.fullmatch(r"[0-9]{1,30}", identity):
            continue
        artists = row.get("artistNames")
        duration = row.get("duration")
        if not isinstance(artists, list) or not all(isinstance(a, str) for a in artists):
            continue
        if not isinstance(row.get("title"), str) or not isinstance(duration, (int, float)) or duration <= 0:
            continue
        candidate = {"id": identity, "title": row["title"], "channel": ", ".join(artists),
                     "artists": artists, "duration": duration / 1000, "isrc": row.get("isrc"),
                     "source_url": BASE + "/track/" + identity}
        score = score_candidate(record, candidate)
        if score is None or score < .84:
            continue
        exact = bool(record.get("isrc") and str(record["isrc"]).upper() == str(row.get("isrc") or "").upper())
        candidate.update(match_score=min(1, score + (.05 if exact else 0)), exact_isrc=exact)
        # Multiple album entries can point at the same recording.
        key = str(row.get("recordingId") or row.get("isrc") or identity)
        if key in seen:
            continue
        seen.add(key)
        ranked.append(candidate)
    return sorted(ranked, key=lambda c: (c["exact_isrc"], c["match_score"]), reverse=True)


def choose_match(record, candidates, choose, config):
    if not candidates:
        raise ValueError("Nenhum FLAC compatível encontrado no Monochrome. Confira título, artista e versão, ou escolha MP3/M4A para usar o YouTube.")
    automatic = bool(config.get("auto_match"))
    ambiguous = len(candidates) > 1 and candidates[0]["exact_isrc"] == candidates[1]["exact_isrc"] and candidates[0]["match_score"] - candidates[1]["match_score"] < .025
    if not automatic and (ambiguous or config.get("confirm_version")):
        chosen = choose(dict(record, _audio_provider="Monochrome"), candidates)
        # The UI may return only its public fields. Use the validated source object.
        for candidate in candidates:
            if candidate["id"] == chosen.get("id"):
                return dict(candidate, selection="user")
        raise ValueError("Nenhuma versão FLAC válida foi selecionada.")
    return dict(candidates[0], selection="automatic")


def fetch_file(session, url, path, emit, title):
    # No cross-domain redirects or browser impersonation. Access denials stay denials.
    for attempt in range(3):
        try:
            with session.get(url, stream=True, timeout=(8, 20), allow_redirects=False) as response:
                if response.status_code in (429, 500, 502, 503, 504, 521) and attempt < 2:
                    emit("stage", message="Fonte FLAC temporariamente ocupada. Tentando novamente…")
                    time.sleep(attempt + 1)
                    continue
                if response.status_code in (401, 403):
                    raise ValueError("O Monochrome recusou o acesso ao arquivo FLAC. Tente mais tarde ou escolha outro formato.")
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError("A fonte FLAC retornou uma resposta inesperada.")
                total = int(response.headers.get("Content-Length") or 0)
                if total > MAX_FILE_SIZE:
                    raise ValueError("O FLAC ultrapassa o limite de 1 GB por faixa.")
                emit("estimate", size=total or None, reason="Tamanho informado pela fonte FLAC", title=title)
                downloaded, last = 0, 0.0
                start = time.monotonic()
                header = bytearray()
                with Path(path).open("wb") as output:
                    for chunk in response.iter_content(65536):
                        if not chunk:
                            continue
                        if len(header) < 4:
                            header.extend(chunk[:4-len(header)])
                            if len(header) == 4 and header != b"fLaC":
                                raise ValueError("A fonte não entregou áudio FLAC. Nenhum arquivo foi publicado.")
                        downloaded += len(chunk)
                        if downloaded > MAX_FILE_SIZE:
                            raise ValueError("O FLAC ultrapassa o limite de 1 GB por faixa.")
                        output.write(chunk)
                        now = time.monotonic()
                        if now - last >= .15:
                            last = now
                            speed = downloaded / max(.001, now-start)
                            emit("progress", status="downloading", title=title, downloaded=downloaded,
                                 total=total or None, speed=speed, eta=(total-downloaded)/speed if total else None)
                if downloaded < 4 or total and downloaded != total:
                    raise ValueError("O download FLAC ficou incompleto. Tente novamente.")
                emit("progress", status="finished", title=title, downloaded=downloaded, total=downloaded)
                return
        except requests.RequestException as exc:
            if attempt == 2 or isinstance(exc, requests.HTTPError):
                raise ValueError("Não foi possível baixar o FLAC do Monochrome. Tente mais tarde.") from exc
            emit("stage", message="Conexão com a fonte FLAC interrompida. Tentando novamente…")
    raise ValueError("Fonte FLAC indisponível. Tente mais tarde.")


def search_matches(record, session=None):
    from contextlib import nullcontext
    query = " ".join([*(record.get("artists") or []), record["title"]])
    with (requests.Session() if session is None else nullcontext(session)) as client:
        try:
            with client.get(BASE + "/search/tracks", params={"q": query, "limit": 20}, timeout=(8, 20)) as response:
                response.raise_for_status()
                payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ValueError("Não foi possível consultar a fonte FLAC Monochrome. Tente mais tarde.") from exc
    tracks = payload.get("tracks") if isinstance(payload, dict) else None
    return rank_matches(record, tracks if isinstance(tracks, list) else [])


def download_flac(config, record, emit, choose, ask_duplicate):
    from file_output import destination
    from flac_browser import import_flac
    emit("stage", message="Procurando FLAC no Monochrome…")
    with requests.Session() as session:
        match = choose_match(record, search_matches(record, session), choose, config)
        emit("log", message=f"Fonte FLAC: Monochrome • {match['title']} • {match['channel']}")
        work = destination(config, record) / ".onda-work"
        work.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="lossless-", dir=work) as temporary:
                source = Path(temporary) / "download.flac"
                emit("stage", message="Baixando FLAC do Monochrome…")
                fetch_file(session, match["source_url"], source, emit, record["title"])
                provenance = dict(match, provider="Monochrome", note="Arquivo FLAC obtido diretamente do servidor Monochrome. A origem anterior e a masterização sem perdas não são comprovadas pelo codec.")
                return import_flac(config, record, None, emit, ask_duplicate, source=source, match=provenance, consume=True)
        finally:
            try:
                work.rmdir()
            except OSError:
                pass
