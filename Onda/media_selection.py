"""Validated per-video output choices shared by UI and worker."""

VIDEO_OUTPUTS = {
    'Vídeo · MP4': 'mp4',
    'Vídeo · MKV': 'video',
    'Só áudio · MP3': 'mp3',
    'Só áudio · M4A': 'm4a',
    'Só áudio · FLAC': 'flac',
    'Só áudio · original': 'original',
}


PHOTO_OUTPUTS = {'Só foto': 'photos', 'Foto com música · MP4': 'photo_video'}


def output_choices(candidate):
    if candidate.get('kind') == 'Vídeo':
        return VIDEO_OUTPUTS
    if candidate.get('photo_choice'):
        return PHOTO_OUTPUTS if candidate.get('has_audio') else {'Só foto': 'photos'}
    return {}


def validate_selection(value, candidates):
    if not isinstance(value, dict):
        raise ValueError('Seleção de mídias inválida.')
    selected = value.get('selected_ids')
    allowed = {item['id']: item for item in candidates}
    if (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(key, str) for key in selected)
    ):
        raise ValueError('Selecione pelo menos uma mídia válida.')
    if len(set(selected)) != len(selected) or not set(selected).issubset(allowed):
        raise ValueError('Seleção de mídias inválida.')
    modes = value.get('media_modes', {})
    if not isinstance(modes, dict):
        raise ValueError('Formatos de mídia inválidos.')
    for key, mode in modes.items():
        if key not in selected or mode not in output_choices(allowed[key]).values():
            raise ValueError('Formato inválido para a mídia selecionada.')
    return selected, modes
