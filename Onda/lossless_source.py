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
    from record_identity import normalized_isrc
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
        left,right=normalized_isrc(record.get('isrc')),normalized_isrc(row.get('isrc'))
        if left and right and left!=right:continue
        exact = bool(left and left==right)
        candidate.update(match_score=min(1, score + (.05 if exact else 0)), exact_isrc=exact,
                         match_reasons=['Mesmo ISRC; título, artista, versão e duração compatíveis'] if exact else ['Título, artista, versão e duração compatíveis'])
        # Multiple album entries can point at the same recording.
        key = str(row.get("recordingId") or row.get("isrc") or identity)
        if key in seen:
            continue
        seen.add(key)
        ranked.append(candidate)
    return sorted(ranked, key=lambda c: (c["exact_isrc"], c["match_score"]), reverse=True)


def choose_match(record, candidates, choose, config):
    from search_choices import ChoiceStore
    store=ChoiceStore()
    remembered=store.get(record)
    candidates=[row for row in candidates if remembered.get(row['id']) is not False]
    if not candidates:
        raise ValueError("Nenhum FLAC compatível encontrado no Monochrome. Confira título, artista e versão, ou escolha MP3/M4A para usar o YouTube.")
    automatic = bool(config.get("auto_match"))
    previous=next((row for row in candidates if remembered.get(row['id']) is True),None)
    if previous is not None:return dict(previous,selection='remembered')
    ambiguous = len(candidates) > 1 and candidates[0]["exact_isrc"] == candidates[1]["exact_isrc"] and candidates[0]["match_score"] - candidates[1]["match_score"] < .025
    if not automatic and (ambiguous or config.get("confirm_version")):
        chosen = choose(dict(record, _audio_provider="Monochrome"), candidates)
        # The UI may return only its public fields. Use the validated source object.
        for candidate in candidates:
            if candidate["id"] == chosen.get("id"):
                if chosen.get('remember_choice'):store.set(record,candidate['id'],True)
                return dict(candidate, selection="user")
        raise ValueError("Nenhuma versão FLAC válida foi selecionada.")
    return dict(candidates[0], selection="automatic")


RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524}
TRANSFER_ATTEMPTS = 6
SEARCH_ATTEMPTS = 4
TIMEOUT = (10, 60)


def retry_delay(response, attempt):
    """Bounded Retry-After/backoff, including HTTP dates."""
    value = response.headers.get("Retry-After", "") if response is not None else ""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            from email.utils import parsedate_to_datetime
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError, AttributeError):
            seconds = min(12, 2 ** attempt)
    if seconds > 120:
        raise ValueError(f"O Monochrome solicitou aguardar {seconds/60:.0f} minutos antes de tentar novamente. Tente mais tarde.")
    return max(1, seconds)


def wait_retry(response, attempt, emit, message):
    delay = retry_delay(response, attempt)
    # Emitting also checks cancellation in the Android bridge.
    emit("stage", message=f"{message} Nova tentativa em {delay:.0f}s…")
    deadline = time.monotonic() + delay
    while time.monotonic() < deadline:
        time.sleep(min(.5, max(0, deadline-time.monotonic())))
        emit("stage", message=f"{message} Nova tentativa em {max(0, deadline-time.monotonic()):.0f}s…")


def validator(headers):
    etag = headers.get("ETag", "")
    return etag if etag and not etag.startswith("W/") else headers.get("Last-Modified", "")


def fetch_file(session, url, path, emit, title):
    # Resume only a byte-identical entity. Never follow arbitrary redirects or
    # substitute a different recording after an access denial.
    path = Path(path)
    downloaded, total, entity = 0, 0, ""
    denial_retried = False
    for attempt in range(TRANSFER_ATTEMPTS):
        response = None
        try:
            headers = {"Accept-Encoding": "identity"}
            offset = downloaded if entity else 0
            if offset:
                headers.update({"Range": f"bytes={offset}-", "If-Range": entity})
            with session.get(url, headers=headers, stream=True, timeout=TIMEOUT, allow_redirects=False) as response:
                status = response.status_code
                if status in (401, 403):
                    if denial_retried or attempt == TRANSFER_ATTEMPTS-1:
                        raise ValueError(f"O Monochrome recusou o acesso ao arquivo FLAC (HTTP {status}), mesmo após uma nova tentativa. Tente mais tarde ou escolha outro formato.")
                    denial_retried = True
                    wait_retry(response, attempt, emit, "O servidor recusou a solicitação. Reabrindo a conexão.")
                    session.close()  # Reset pooled connections; no credentials or bypass.
                    continue
                if status in RETRYABLE_STATUS:
                    response.raise_for_status()
                if status == 416 and offset:
                    downloaded, total, entity = 0, 0, ""
                    raise requests.ConnectionError("A fonte não aceitou o trecho restante; reiniciando com segurança.")
                response.raise_for_status()
                if status not in (200, 206):
                    raise ValueError("A fonte FLAC retornou uma resposta inesperada.")
                try:
                    length = int(response.headers.get("Content-Length") or 0)
                except (TypeError, ValueError):
                    raise ValueError("A fonte FLAC informou um tamanho inválido.") from None
                if length < 0:
                    raise ValueError("A fonte FLAC informou um tamanho inválido.")
                current_entity = validator(response.headers)
                if status == 206:
                    content_range = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                    if not offset or not content_range:
                        raise ValueError("A fonte FLAC retornou um trecho inválido. Nenhum arquivo foi publicado.")
                    first, last_byte, current_total = map(int, content_range.groups())
                    if first != offset or last_byte < first or last_byte >= current_total or (length and length != last_byte-first+1) or (total and total != current_total) or (current_entity and current_entity != entity):
                        downloaded, total, entity = 0, 0, ""
                        raise requests.ConnectionError("O arquivo mudou durante a retomada; reiniciando com segurança.")
                    total = current_total
                else:
                    # If Range is ignored, replace the partial file; never append.
                    downloaded, total, entity = 0, length, current_entity
                if total > MAX_FILE_SIZE:
                    raise ValueError("O FLAC ultrapassa o limite de 1 GB por faixa.")
                emit("estimate", size=total or None, reason="Tamanho informado pela fonte FLAC", title=title)
                if downloaded:
                    emit("stage", message=f"Retomando FLAC a partir de {downloaded/1048576:.1f} MB…")
                started, transferred, last_emit = time.monotonic(), 0, 0.0
                header = bytearray()
                with path.open("ab" if downloaded else "wb") as output:
                    for chunk in response.iter_content(65536):
                        if not chunk:
                            continue
                        if not offset or status == 200:
                            if len(header) < 4:
                                header.extend(chunk[:4-len(header)])
                                if len(header) == 4 and header != b"fLaC":
                                    raise ValueError("A fonte não entregou áudio FLAC. Nenhum arquivo foi publicado.")
                        if downloaded + len(chunk) > MAX_FILE_SIZE or (total and downloaded + len(chunk) > total):
                            raise ValueError("A fonte FLAC entregou um tamanho inválido. Nenhum arquivo foi publicado.")
                        output.write(chunk)
                        downloaded += len(chunk)
                        transferred += len(chunk)
                        now = time.monotonic()
                        if now-last_emit >= .15:
                            last_emit = now
                            speed = transferred/max(.001, now-started)
                            emit("progress", status="downloading", title=title, downloaded=downloaded,
                                 total=total or None, speed=speed, eta=max(0,total-downloaded)/speed if total else None)
                if downloaded < 4 or (total and downloaded != total):
                    raise requests.ConnectionError("O servidor encerrou o download antes de completar o FLAC.")
                emit("progress", status="finished", title=title, downloaded=downloaded, total=downloaded)
                return
        except requests.RequestException as exc:
            status = response.status_code if response is not None else None
            if isinstance(exc, requests.HTTPError) and status not in RETRYABLE_STATUS:
                raise ValueError(f"Não foi possível baixar o FLAC do Monochrome (HTTP {status}). Tente mais tarde.") from exc
            if attempt == TRANSFER_ATTEMPTS-1:
                raise ValueError("Não foi possível concluir o FLAC do Monochrome após 6 tentativas. A conexão ou o servidor continua instável; nenhum arquivo incompleto foi publicado.") from exc
            # No validator means a clean restart, avoiding mixed recordings.
            if not entity:
                downloaded = 0
            wait_retry(response, attempt, emit, "Conexão com a fonte FLAC interrompida. Recuperando o download.")
    raise ValueError("Fonte FLAC indisponível. Tente mais tarde.")


def search_matches(record, session=None, emit=lambda *args, **kwargs: None):
    from contextlib import nullcontext
    query = " ".join([*(record.get("artists") or []), record["title"]])
    with (requests.Session() if session is None else nullcontext(session)) as client:
        denial_retried = False
        for attempt in range(SEARCH_ATTEMPTS):
            response = None
            try:
                with client.get(BASE + "/search/tracks", params={"q": query, "limit": 20}, timeout=TIMEOUT, allow_redirects=False) as response:
                    status = response.status_code
                    if status in (401,403) and not denial_retried and attempt < SEARCH_ATTEMPTS-1:
                        denial_retried = True
                        wait_retry(response, attempt, emit, "Reabrindo a consulta à fonte FLAC.")
                        client.close()
                        continue
                    response.raise_for_status()
                    if status != 200:
                        raise ValueError("Resposta inesperada do servidor.")
                    payload = response.json()
                    break
            except (requests.RequestException, ValueError) as exc:
                status = response.status_code if response is not None else None
                permanent = isinstance(exc, requests.HTTPError) and status not in RETRYABLE_STATUS
                if permanent or attempt == SEARCH_ATTEMPTS-1:
                    raise ValueError("Não foi possível consultar a fonte FLAC Monochrome. Tente mais tarde.") from exc
                wait_retry(response, attempt, emit, "Consulta FLAC temporariamente indisponível.")
    tracks = payload.get("tracks") if isinstance(payload, dict) else None
    return rank_matches(record, tracks if isinstance(tracks, list) else [])


def download_flac(config, record, emit, choose, ask_duplicate):
    from file_output import destination
    from flac_browser import import_flac
    emit("stage", message="Procurando FLAC no Monochrome…")
    with requests.Session() as session:
        match = choose_match(record, search_matches(record, session, emit), choose, config)
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
