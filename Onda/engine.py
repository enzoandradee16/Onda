"""Download engine: isolated worker, structured events, no UI dependencies."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

MODES = {
    "Vídeo · melhor qualidade (MKV)": "video",
    "Vídeo · MP4": "mp4",
    "Áudio · original, sem recodificar": "original",
    "Áudio · MP3 (320 kbps)": "mp3",
    "Áudio · M4A (AAC)": "m4a",
    "Áudio · FLAC": "flac",
    "Fotos · todas do carrossel": "photos",
    "Publicação · fotos e vídeos originais": "social",
}
HEIGHTS = {"Melhor disponível": None, "2160p / 4K": 2160, "1440p": 1440,
           "1080p": 1080, "720p": 720, "480p": 480}
MP3_QUALITIES = ("320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps")
M4A_QUALITIES = ("256 kbps", "192 kbps", "128 kbps", "96 kbps")
FPS_OPTIONS = {"Original": None, "24 fps": 24, "30 fps": 30, "60 fps": 60, "120 fps": 120}


def audio_bitrate(config):
    mode = config["mode"]
    choices = MP3_QUALITIES if mode == "mp3" else M4A_QUALITIES
    quality = config.get("audio_quality") or choices[0]
    if quality not in choices:
        raise ValueError("Qualidade de áudio inválida para o formato escolhido.")
    return quality.split()[0]


def validate_url(value: str) -> str:
    from media_links import unwrap_google
    value = unwrap_google(value.strip())
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in ("http", "https") or not host or any(c.isspace() for c in value):
            raise ValueError("Informe um link HTTP ou HTTPS completo.")
        if parsed.username or parsed.password:
            raise ValueError("Não coloque senhas no link.")
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"Link inválido: {exc}") from exc
    for domain in ("spotify.com", "spotify.link", "music.apple.com", "itunes.apple.com"):
        if host == domain or host.endswith("." + domain):
            raise ValueError("Spotify e Apple Music: use o aplicativo oficial para ouvir offline. "
                             "O Onda não exporta o catálogo protegido desses serviços.")
    return value


def binaries(folder: str = "") -> bool:
    if folder:
        suffix = ".exe" if os.name == "nt" else ""
        return all((Path(folder) / (name + suffix)).is_file() for name in ("ffmpeg", "ffprobe"))
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def build_options(config: dict) -> dict:
    from playlist_options import playlist_limit
    max_items = playlist_limit(config.get("playlist_limit", 1000))
    mode = config["mode"]
    if mode not in MODES.values():
        raise ValueError("Formato inválido.")
    height = config.get("height")
    if height not in HEIGHTS.values():
        raise ValueError("Resolução inválida.")
    options = {
        "paths": {"home": str(Path(config["folder"]).resolve())},
        "outtmpl": {"default": "%(artist,uploader|Artista desconhecido).80B - %(track,title).140B.%(ext)s"},
        "windowsfilenames": True,
        "noplaylist": not config.get("playlist", False),
        "playlistend": max_items if config.get("playlist", False) else 1,
        "continuedl": True, "overwrites": False,
        "retries": 3, "fragment_retries": 3, "socket_timeout": 20,
        "ignoreerrors": False, "quiet": True, "no_warnings": False,
        "noprogress": True, "concurrent_fragment_downloads": 2,
        "js_runtimes": {"deno": {}, "node": {}},
        "match_filter": reject_live,
    }
    if config.get("ffmpeg"):
        options["ffmpeg_location"] = config["ffmpeg"]
    if config.get("cookies_file"):
        options["cookiefile"] = config["cookies_file"]
    if mode in ("mp3", "m4a"):
        bitrate = audio_bitrate(config)
    if config.get("output_artist") and config.get("output_title"):
        from yt_dlp.utils import sanitize_filename
        name = sanitize_filename(config["output_artist"][:80] + " - " + config["output_title"][:140], restricted=False)
        options["outtmpl"] = {"default": name.replace("%", "%%") + ".%(ext)s"}
    if mode == "social":
        options["outtmpl"] = {"default": "%(uploader|Publicação).60B - %(title).120B - %(playlist_index|1)s.%(ext)s"}
        options["format"] = "bestvideo+bestaudio/best"
        options["noplaylist"] = False
        options["playlistend"] = 100
        options["postprocessors"] = []
    elif mode == "photos":
        raise ValueError("Fotos devem ser baixadas pelo extrator de publicações.")
    elif mode in ("video", "mp4"):
        limit = f"[height<=?{height}]" if height else ""
        fps = config.get("fps")
        if fps not in FPS_OPTIONS.values():
            raise ValueError("FPS inválido.")
        fps_limit = f"[fps<=?{fps}]" if fps else ""
        options["format"] = f"bestvideo{limit}{fps_limit}+bestaudio/best{limit}{fps_limit}"
        options["merge_output_format"] = "mkv"
        options["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mkv"}]
        if mode == "mp4":
            # Prefer MP4/M4A streams to avoid unnecessary transcoding. Every
            # fallback must retain the requested resolution and FPS ceilings.
            constraints = limit + fps_limit
            options["format"] = (f"bestvideo[ext=mp4]{constraints}+bestaudio[ext=m4a]/"
                                 f"best[ext=mp4]{constraints}/"
                                 f"bestvideo{constraints}+bestaudio/best{constraints}")
            options["merge_output_format"] = "mp4/mkv"
            options["postprocessors"] = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
    else:
        options["format"] = "bestaudio" if mode == "original" else "bestaudio/best"
        if mode == "original":
            # Download an audio-only stream unchanged. Never allow best->MP3 fallback.
            options["postprocessors"] = []
            return options
        processor = {"key": "FFmpegExtractAudio", "preferredcodec": "best" if mode == "original" else mode}
        if mode == "mp3":
            processor["preferredquality"] = bitrate
        # Honor bitrate even when source and target codecs already match.
        options["postprocessors"] = [] if mode in ("mp3", "m4a") else [processor]
    return options


def reject_live(info, *, incomplete=False):
    if info.get("is_live") or info.get("live_status") == "is_upcoming":
        return "Transmissões ao vivo e estreias futuras não são suportadas."


def download_with_recovery(url, options, configure, saved):
    """Refresh expired YouTube media URLs once and test candidate formats."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    youtube = any(host == domain or host.endswith("." + domain)
                  for domain in ("youtube.com", "youtu.be"))
    for attempt in range(2):
        current = dict(options)
        if attempt:
            # The selector keeps the requested codec/resolution/FPS constraints.
            # Testing is lazy: reject inaccessible candidates before choosing one.
            current["check_formats"] = "selected"
        try:
            with YoutubeDL(current) as downloader:
                from kwai import OndaKwaiIE
                if OndaKwaiIE.suitable(url):
                    downloader.add_info_extractor(OndaKwaiIE(downloader))
                    configure(downloader)
                    info = downloader.extract_info(url, download=False, process=False, ie_key=OndaKwaiIE.ie_key())
                    formats = [f for f in info.get("formats", []) if f.get("width") and f.get("height")]
                    if formats and all(f["width"] < f["height"] for f in formats):
                        selector = current.get("format", "best").replace("[height<=?", "[width<=?")
                        downloader.params["format"] = selector
                        downloader.format_selector = downloader.build_format_selector(selector)
                    downloader.process_ie_result(info, download=True)
                    return 0
                configure(downloader)
                return downloader.download([url])
        except DownloadError as exc:
            forbidden = "HTTP Error 403" in str(exc)
            if not (youtube and forbidden):
                raise
            if attempt or saved:
                raise RuntimeError(
                    "O YouTube recusou o acesso ao arquivo (HTTP 403). "
                    "Tente novamente mais tarde. Se persistir, atualize o yt-dlp. "
                    "Detalhes: " + str(exc)) from exc
            emit("stage", message="YouTube recusou o áudio/vídeo. Atualizando links e testando formatos…")
            emit("log", message="Recuperação HTTP 403: nova consulta ao mesmo vídeo; "
                 "formatos indisponíveis serão descartados.")


def emit(kind: str, **values):
    print(json.dumps({"type": kind, **values}, ensure_ascii=True), flush=True)


class Logger:
    def debug(self, message):
        if not message.startswith("[debug]"):
            emit("log", message=message)

    def warning(self, message):
        emit("log", message="Aviso: " + message)

    def error(self, message):
        emit("log", message="Erro: " + message)


def ask_version(record, candidates, input_stream=None):
    fields = ("id", "title", "channel", "uploader", "duration", "match_score", "source_url", "manual_review")
    emit("choose_version", title=record["title"], artists=record.get("artists", []),
         duration_ms=record.get("duration_ms"),
         candidates=[{k: c.get(k) for k in fields} for c in candidates])
    try:
        reply = json.loads((input_stream or sys.stdin).readline())
        selected = reply.get("selected_id")
    except (ValueError, AttributeError):
        raise ValueError("A escolha da versão foi interrompida.") from None
    for candidate in candidates:
        if candidate["id"] == selected:
            return {**candidate, "selection": "user"}
    raise ValueError("Nenhuma versão válida foi selecionada.")


def ask_catalog(anchor, candidates, input_stream=None):
    from catalog_match import picker_event
    event = picker_event(anchor, candidates)
    fields = ("id", "title", "artists", "platform", "album", "duration", "duration_ms", "match_score", "source_url")
    emit("choose_catalog", title=event["title"], artists=event["artists"], duration_ms=event["duration_ms"],
         candidates=[{k: row.get(k) for k in fields} for row in event["candidates"]])
    try:
        selected_id = json.loads((input_stream or sys.stdin).readline()).get("selected_id")
    except (ValueError, AttributeError):
        raise ValueError("A escolha de metadados foi interrompida.") from None
    for row in candidates:
        if row["source_url"] == selected_id:
            return row
    raise ValueError("Nenhuma faixa válida do catálogo foi selecionada.")


def ask_review(record, input_stream=None, audio_source=None):
    from review import apply_review
    emit("review_metadata", record=record, audio_source=audio_source)
    try:
        changes = json.loads((input_stream or sys.stdin).readline())["changes"]
    except (ValueError, KeyError, TypeError):
        raise ValueError("A revisão foi interrompida.") from None
    return apply_review(record, changes)


def ask_duplicate(path, input_stream=None):
    emit("choose_duplicate", path=str(path), size=path.stat().st_size)
    try:
        choice = json.loads((input_stream or sys.stdin).readline())["choice"]
    except (ValueError, KeyError, TypeError):
        raise ValueError("A escolha do arquivo duplicado foi interrompida.") from None
    if choice not in ("keep", "replace", "skip"):
        raise ValueError("Escolha inválida para arquivo duplicado.")
    return choice


def ask_media(candidates, input_stream=None):
    emit("choose_media", candidates=candidates)
    try:
        value = json.loads((input_stream or sys.stdin).readline())
        from media_selection import validate_selection
        selected, modes = validate_selection(value, candidates)
    except (ValueError, KeyError, TypeError):
        raise ValueError("A seleção de fotos e vídeos foi interrompida.") from None
    return {"selected_ids": selected, "media_modes": modes} if modes else selected


def run_worker(config: dict) -> int:
    try:
        from yt_dlp.postprocessor.common import PostProcessor

        from metadata import MetadataClient, is_streaming_link
        record = match = cover = None
        streaming = is_streaming_link(config["url"])
        url = config["url"] if streaming else validate_url(config["url"])
        from social_media import is_social
        if not streaming and not is_social(url):
            from media_links import prepare_link
            config['url'] = url
            finished, url = prepare_link(config, emit, ask_duplicate)
            if finished:
                return 0
            config['url'] = url
        if config["mode"] in ("photos", "social") or is_social(url):
            if streaming:
                raise ValueError("Escolha um formato de áudio para links de música.")
            from social_media import download_post, access_error
            try:
                if download_post(config, emit, ask_duplicate, choose=ask_media):
                    return 0
            except Exception as exc:
                raise ValueError(access_error(exc)) from exc
        if not binaries(config.get("ffmpeg", "")):
            raise ValueError("FFmpeg e ffprobe não encontrados. Instale-os ou selecione a pasta bin na interface.")
        Path(config["folder"]).mkdir(parents=True, exist_ok=True)
        if streaming:
            from matching import resolve_youtube
            from tagging import fetch_cover
            emit("stage", message="Consultando metadados da música…")
            client = MetadataClient(config.get("spotify_client_id", ""), config.get("spotify_client_secret", ""))
            try:
                if config.get('catalog_record'):
                    from spotify_search import cached_record
                    record = cached_record(config['catalog_record'], url)
                else:
                    record = client.resolve(url, choose=ask_catalog, selected_catalog_url=config.get("selected_catalog_url"))
            finally:
                client.close()
            emit("log", message="Metadados e capa: " + record["platform"] + " • " + record["source_url"])
            emit("stage", message="Procurando uma versão correspondente no YouTube…")
            match = resolve_youtube(record, Logger(), ask_version,
                                    automatic=bool(config.get("auto_match")), confirm=bool(config.get("confirm_version")))
            url = match["source_url"]
            emit("log", message=f"Selecionado: {match['title']} • {url} • similaridade {match['match_score']:.0%}")
            if config.get("review_metadata"):
                emit("stage", message="Aguardando revisão dos metadados…")
                record = ask_review(record, audio_source=url)
            emit("stage", message="Obtendo a capa…")
            if record.get("cover_path"):
                from review import local_cover
                cover = local_cover(record["cover_path"])
            else:
                cover = fetch_cover(record.get("cover_url"))
            config = dict(config, playlist=False, output_artist=record["artists"][0], output_title=record["title"])
            if config["mode"] in ("video", "mp4", "original"):
                config["mode"] = "mp3" if config["mode"] in ("video", "mp4") else "m4a"
        from file_output import destination, publish
        output_folder = destination(config, record)
        destination_config = dict(config)
        # Keep resumable intermediates separate from complete user files.
        identity = json.dumps({k: config.get(k) for k in ("url", "mode", "audio_quality", "height", "fps", "output_artist", "output_title")}, sort_keys=True)
        staging = output_folder / ".onda-work" / hashlib.sha256(identity.encode()).hexdigest()[:20]
        staging.mkdir(parents=True, exist_ok=True)
        config = dict(config, folder=str(staging))
        last_update = 0.0
        saved = []

        def progress(data):
            nonlocal last_update
            now = time.monotonic()
            if data["status"] == "downloading" and now - last_update < 0.15:
                return
            last_update = now
            info = data.get("info_dict", {})
            emit("progress", status=data["status"], title=info.get("title", ""),
                 downloaded=data.get("downloaded_bytes", 0),
                 total=data.get("total_bytes") or data.get("total_bytes_estimate"),
                 speed=data.get("speed"), eta=data.get("eta"),
                 index=info.get("playlist_index"), count=info.get("playlist_count"))

        def postprocess(data):
            emit("processing", title=data.get("info_dict", {}).get("title", ""))

        class CaptureFile(PostProcessor):
            def run(self, info):
                path = info.get("filepath") or info.get("_filename")
                if path and Path(path).is_file():
                    sidecar = None
                    if record:
                        from tagging import apply_tags
                        emit("stage", message="Gravando metadados e capa no arquivo…")
                        sidecar = apply_tags(path, record, match, cover)
                        emit("log", message="Metadados e origem registrados: " + sidecar)
                    target_folder = destination(destination_config, record, info=info)
                    final, skipped = publish(path, target_folder, config.get("duplicate_policy", "keep"), ask_duplicate)
                    if sidecar:
                        if skipped:
                            Path(sidecar).unlink(missing_ok=True)
                        else:
                            os.replace(sidecar, final + ".metadata.json")
                    if skipped:
                        Path(path).unlink(missing_ok=True)
                        emit("log", message="Arquivo existente mantido: " + final)
                    saved.append(final)
                    emit("file", path=final, size=Path(final).stat().st_size, skipped=skipped,
                         mode=Path(final).suffix.lstrip(".").upper() if config["mode"] == "social" else config["mode"].upper())
                return [], info

        class EstimateSize(PostProcessor):
            def run(self, info):
                from size_estimate import estimate_size
                size, reason = estimate_size(info, config, len(cover[0]) if cover else 0)
                emit("estimate", size=size, reason=reason, title=info.get("title"),
                     playlist=bool(config.get("playlist")), fps=info.get("fps"))
                return [], info

        class PrepareDirectMetadata(PostProcessor):
            def run(self, info):
                nonlocal record, match, cover, output_folder
                from metadata import base_record
                from review import local_cover
                from tagging import fetch_cover
                record = base_record("YouTube" if info.get("extractor_key") == "Youtube" else "Fonte",
                                     str(info.get("id") or "audio"), info.get("webpage_url") or url, "Metadados informados pela fonte")
                record.update(title=info.get("track") or info.get("title") or "Música",
                              artists=[info.get("artist") or info.get("uploader") or info.get("channel") or "Artista desconhecido"],
                              album=info.get("album"), duration_ms=(info.get("duration") or 0) * 1000,
                              cover_url=info.get("thumbnail"))
                match = {"source_url": info.get("webpage_url") or url, "title": info.get("title"), "selection": "user", "match_score": None}
                record = ask_review(record, audio_source=match["source_url"])
                cover = local_cover(record["cover_path"]) if record.get("cover_path") else fetch_cover(record.get("cover_url"))
                info["artist"], info["track"] = record["artists"][0], record["title"]
                output_folder = destination(destination_config, record)
                return [], info

        options = build_options(config)
        options.update(logger=Logger(), progress_hooks=[progress], postprocessor_hooks=[postprocess])
        def configure(downloader):
            if not streaming and config.get("review_metadata") and config["mode"] in ("mp3", "m4a", "flac"):
                downloader.add_post_processor(PrepareDirectMetadata(downloader), when="pre_process")
            downloader.add_post_processor(EstimateSize(downloader), when="before_dl")
            if config["mode"] in ("mp3", "m4a"):
                from audio_quality import AudioQualityPP
                downloader.add_post_processor(AudioQualityPP(downloader, audio_bitrate(config), config["mode"]))
            downloader.add_post_processor(CaptureFile(downloader), when="after_move")
        code = download_with_recovery(url, options, configure, saved)
        if code or not saved:
            raise RuntimeError("Nenhum arquivo concluído ou parte da playlist falhou. Veja os detalhes.")
        try:
            staging.rmdir()
            staging.parent.rmdir()
        except OSError:
            pass
        emit("done", files=saved)
        return 0
    except Exception as exc:
        message = str(exc)
        from social_media import is_social, access_error
        if is_social(config.get("url", "")) and config.get("mode") not in ("photos", "social") and any(word in message.lower() for word in ("403", "401", "login", "log in", "private", "ip address is blocked")):
            message = access_error(exc)
        emit("error", message=message)
        return 1


def stop_process(process: subprocess.Popen):
    """Terminate this job and its FFmpeg children, including during conversion."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode and process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    try:
        configuration = json.loads(sys.stdin.readline())
    except (ValueError, OSError) as error:
        emit("error", message=str(error))
        sys.exit(1)
    sys.exit(run_worker(configuration))
