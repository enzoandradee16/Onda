"""Browser-assisted FLAC import: no challenge tokens or private service API."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from urllib.parse import urlencode

INSTRUCTIONS = ("Abra o serviço, escolha a música e baixe em FLAC. "
                "Se houver verificação de segurança, conclua no navegador. "
                "Depois volte ao ONDA e selecione o arquivo baixado. "
                "Confira artista, título e versão antes de importar.")


def search_url(record):
    query = " ".join([*(record.get("artists") or []), record["title"]])
    return "https://flacdownloader.com/pt/?" + urlencode({"q": query})


def validate_flac(path, record=None):
    from mutagen.flac import FLAC
    path = Path(path)
    if not path.is_file() or path.suffix.lower() != ".flac":
        raise ValueError("Selecione um arquivo FLAC concluído, não MP3 ou um download parcial.")
    with path.open("rb") as stream:
        if stream.read(4) != b"fLaC":
            raise ValueError("O arquivo selecionado não contém áudio FLAC.")
    try:
        audio = FLAC(path)
        info = audio.info
        if info.length <= 0 or info.sample_rate <= 0 or info.channels <= 0:
            raise ValueError()
    except Exception as exc:
        raise ValueError("Arquivo FLAC inválido ou incompleto.") from exc
    expected = (record or {}).get("duration_ms") or 0
    if expected and abs(info.length - expected / 1000) > max(20, expected / 1000 * .15):
        raise ValueError("A duração do FLAC difere da música escolhida. Confira a versão e tente novamente.")
    return info


def import_flac(config, record, ask_file, emit, ask_duplicate, *, source=None, match=None, consume=False):
    from audio_tools import executable, process_options
    from file_output import component, destination, publish
    from tagging import apply_tags, fetch_cover
    from review import local_cover

    url = search_url(record)
    source = Path(source) if source is not None else Path(ask_file(record, url))
    folder = destination(config, record)
    work = folder / ".onda-work"
    work.mkdir(parents=True, exist_ok=True)
    # Never modify or remove the browser's original download.
    with tempfile.TemporaryDirectory(prefix="flac-", dir=work) as temporary:
        target = Path(temporary) / (component(" - ".join([record["artists"][0], record["title"]])) + ".flac")
        emit("stage", message="Validando o arquivo FLAC selecionado…")
        validate_flac(source, record)
        os.replace(source, target) if consume else shutil.copyfile(source, target)
        result = subprocess.run([executable("ffmpeg", config.get("ffmpeg", "")), "-nostdin", "-v", "error", "-xerror",
                                 "-i", str(target), "-map", "0:a:0", "-f", "null", "-"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **process_options())
        if result.returncode:
            raise ValueError("Não foi possível decodificar o FLAC completo. Baixe novamente o arquivo.")
        if config.get("normalize_volume"):
            from audio_library import normalize_audio
            normalize_audio(str(target), config, emit)
        cover = None
        if record.get("cover_path"):
            cover = local_cover(record["cover_path"])
        elif record.get("cover_url"):
            try:
                cover = fetch_cover(record["cover_url"])
            except ValueError as exc:
                emit("log", message=str(exc) + " A capa existente no FLAC será preservada.")
        emit("stage", message="Gravando metadados e capa no arquivo…")
        match = match or {"source_url": url, "title": source.name, "selection": "user", "provider": "FLAC Downloader",
                 "note": "FLAC selecionado pelo usuário após download no serviço externo. O codec não comprova a origem ou a masterização sem perdas."}
        sidecar = apply_tags(str(target), record, match, cover)
        final, skipped = publish(target, folder, config.get("duplicate_policy", "keep"), ask_duplicate, config=config, record=record)
        if not skipped:
            os.replace(sidecar, final + ".metadata.json")
        emit("file", path=final, size=Path(final).stat().st_size, skipped=skipped, mode="FLAC")
        emit("done", files=[final])
    try:
        work.rmdir()
    except OSError:
        pass
    return 0
