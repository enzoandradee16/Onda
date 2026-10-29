"""Apply only explicitly selected metadata fields, using atomic per-file saves."""

from pathlib import Path
from audio_library import FIELDS, edit_copy


def edit_batch(config, emit=lambda *args, **kwargs: None, *, cancelled=lambda: False):
    entries = config.get('sources')
    changes = config.get('changes', {})
    if not isinstance(entries, list) or not 1 <= len(entries) <= 500:
        raise ValueError('Escolha de 1 a 500 arquivos de áudio.')
    if not isinstance(changes, dict) or set(changes) - set(FIELDS):
        raise ValueError('Campo de metadados inválido.')
    if not changes and not config.get('cover_path'):
        raise ValueError('Selecione pelo menos um campo ou uma capa para aplicar.')
    for key, value in changes.items():
        if key == 'artists':
            if not isinstance(value, list) or any(
                not isinstance(part, str) or len(part) > 4096 for part in value
            ):
                raise ValueError('Campo de metadados inválido.')
        elif not isinstance(value, str) or len(value) > 4096:
            raise ValueError('Campo de metadados inválido.')
        if key in ('track_number', 'disc_number') and value:
            from output_rules import positive_number

            if not positive_number(value):
                raise ValueError('Informe um número de faixa ou disco válido.')
    results, errors, seen = [], [], set()
    for index, entry in enumerate(entries):
        if cancelled():
            raise InterruptedError('Operação cancelada.')
        path = Path(entry['source']).resolve()
        if path in seen:
            continue
        seen.add(path)
        emit('stage', message=f'Editando arquivo {index + 1} de {len(entries)}')
        try:
            options = dict(
                config,
                source=str(path),
                output_name=entry.get('output_name') or path.stem,
                edit_metadata=True,
                normalize_volume=False,
                lyrics_path='',
            )
            if config.get('_android_batch'):
                options['overwrite_original'] = False
            result = edit_copy(options, emit, cancelled=cancelled)
            if config.get('_android_batch'):
                if config.get('overwrite_original'):
                    emit(
                        'batch_original',
                        **result,
                        source=str(path),
                        original_uri=entry['original_uri'],
                    )
                else:
                    emit('file', **result)
            results.append(result)
        except InterruptedError:
            raise
        except Exception as error:
            errors.append(
                {'name': entry.get('output_name') or path.name, 'error': str(error)}
            )
            continue
    return {
        'results': results,
        'errors': errors,
        'message': f'{len(results)} arquivos salvos; {len(errors)} falhas.',
    }
