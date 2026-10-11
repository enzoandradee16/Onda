"""Output-size estimates based on selected formats, not all formats on a page."""


def positive(value):
    return isinstance(value, (int, float)) and value > 0


def estimate_size(info, config, cover_bytes=0):
    duration = info.get("duration")
    mode = config["mode"]
    if mode in ("mp3", "m4a"):
        if not positive(duration):
            return None, "Duração não informada pela fonte"
        from engine import audio_bitrate
        payload = duration * int(audio_bitrate(config)) * 1000 / 8
        return int(payload * 1.02 + cover_bytes + 8192), "Duração × bitrate selecionado; inclui margem para tags e contêiner"
    if mode == "flac":
        return None, "O tamanho FLAC depende do conteúdo e da compressão; será mostrado ao concluir"
    streams = info.get("requested_formats") or [info]
    total = 0
    for stream in streams:
        size = stream.get("filesize") or stream.get("filesize_approx")
        if not positive(size):
            bitrate = stream.get("tbr") or stream.get("abr")
            if not positive(bitrate) or not positive(duration):
                return None, "A fonte não informa tamanho ou bitrate suficientes"
            size = duration * bitrate * 1000 / 8
        total += size
    return int(total * 1.01 + cover_bytes), "Soma das faixas selecionadas com margem para o contêiner"
