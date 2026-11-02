"""Local playback snapshots; restoring never starts a decoder or audio output."""

import json
import math
from pathlib import Path

FIELDS = (
    'effectsQueue',
    'effectsQueueIndex',
    'effectsSource',
    'effectsRecord',
    'effectsCover',
    'position',
    'duration',
    'speed',
    'reverb',
    'keep_pitch',
    'effectsVolume',
    'effectsRepeat',
    'effectsShuffle',
)


def prepared_reference(model):
    if model.get('_stream'):
        return {}
    return {
        key: model[key]
        for key in (
            'cache',
            'source',
            'title',
            'media_title',
            'media_artist',
            'album',
            'cover_url',
        )
        if key in model
    }


def restored_prepared(reference):
    if not isinstance(reference, dict):
        return None
    try:
        base = Path(reference['cache'])
        if not (base / 'audio.wav').is_file():
            return None
        model = json.loads((base / 'analysis.json').read_text(encoding='utf-8'))
        from jukebox import validate_model

        validate_model(model)
        return dict(model, **reference, cached=True)
    except (OSError, ValueError, TypeError, KeyError):
        return None


def save(workspace, strict=False, background=False):
    bridge = workspace.bridge
    if (
        getattr(workspace, '_session_queue_snapshot', None) is None
        or getattr(workspace, '_session_queue_source', None) is not bridge.playlist
        or len(workspace._session_queue_snapshot) != len(bridge.playlist)
    ):
        workspace._session_queue_source = bridge.playlist
        from copy import deepcopy

        workspace._session_queue_snapshot = [
            (
                deepcopy(
                    dict(
                        row,
                        prepared_cache=prepared_reference(bridge._prepared[row['id']]),
                    )
                )
                if row.get('id') in bridge._prepared
                else deepcopy(row)
            )
            for row in bridge.playlist
        ]
    data = {
        'version': 1,
        'unified': True,
        'effectsEnabled': workspace.options.get('effectsEnabled', False),
        'effects': __import__('copy').deepcopy(
            {key: workspace.options[key] for key in FIELDS}
        ),
        'jukebox': {
            'queue': workspace._session_queue_snapshot,
            'index': bridge.queue_index,
            'current_id': (
                bridge.playlist[bridge.queue_index]['id']
                if 0 <= bridge.queue_index < len(bridge.playlist)
                else None
            ),
            'model': (
                prepared_reference(bridge.model)
                if bridge.model and not bridge.model.get('_stream')
                else None
            ),
            'seconds': (
                bridge.sourcePosition
                if bridge.model
                else next(
                    (
                        row.get('restore_seconds', 0)
                        for i, row in enumerate(bridge.playlist)
                        if i == bridge.queue_index
                    ),
                    0,
                )
            ),
            'position': bridge.position,
            'phase': bridge.phase,
            'params': bridge._params,
            'repeat': bridge.queue_repeat,
            'shuffle': bridge.queue_shuffle,
            'shuffle_order': list(bridge._shuffle_order),
            'recent': list(bridge._queue_history),
        },
    }
    target = workspace.store.path.with_name('playback-session.json')
    from session_writer import SessionWriter

    writer = getattr(workspace, '_session_writer', None)
    if writer is None:
        writer = workspace._session_writer = SessionWriter(target)
    future = writer.submit(data)
    if not background or strict:
        try:
            future.result()
        except (OSError, TypeError, ValueError) as error:
            if strict:
                raise ValueError(
                    'Não foi possível salvar a sessão antes de reiniciar.'
                ) from error


def restore(workspace):
    try:
        data = json.loads(
            workspace.store.path.with_name('playback-session.json').read_text(
                encoding='utf-8'
            )
        )
        if data.get('version') != 1:
            return
        effects = data['effects']
        bridge = workspace.bridge
        jukebox = data['jukebox']
        if not isinstance(effects, dict) or not isinstance(jukebox, dict):
            return
        for key in FIELDS:
            if key not in effects:
                continue
            value = effects[key]
            default = workspace.options[key]
            if type(default) in (int, float):
                if type(value) not in (int, float):
                    return
            elif not isinstance(value, type(default)):
                return
            if isinstance(value, (int, float)) and not math.isfinite(value):
                return
        rows = [
            row
            for row in effects.get('effectsQueue', [])
            if isinstance(row, dict)
            and isinstance(row.get('source'), str)
            and Path(row['source']).is_file()
            and isinstance(row.get('record'), dict)
            and isinstance(row.get('duration'), (int, float))
            and math.isfinite(row['duration'])
            and row['duration'] > 0
        ]
        source = effects.get('effectsSource', '')
        if isinstance(source, str) and Path(source).is_file():
            workspace.options.update(
                {key: effects[key] for key in FIELDS if key in effects}
            )
            workspace.options['position'] = max(
                0,
                min(
                    float(effects.get('position', 0)), float(effects.get('duration', 0))
                ),
            )
        workspace.options.update(
            effectsQueue=rows,
            effectsQueueIndex=next(
                (i for i, r in enumerate(rows) if r['source'] == source), -1
            ),
            effectsPaused=True,
            previewActive=False,
        )
        old_queue = [row for row in jukebox.get('queue', []) if isinstance(row, dict)]
        old_index = int(jukebox.get('index', -1))
        current_id = jukebox.get('current_id')
        if (
            not isinstance(current_id, str)
            or not current_id
            or not any(row.get('id') == current_id for row in old_queue)
        ):
            current_id = (
                old_queue[old_index].get('id')
                if 0 <= old_index < len(old_queue)
                else None
            )
        bridge.playlist = [
            (
                dict(row, kind='catalog', analysis='pending')
                if row.get('kind') == 'file'
                and not Path(row.get('source', '')).is_file()
                and isinstance(row.get('record'), dict)
                and row['record'].get('source_url')
                else dict(row, analysis='pending')
            )
            for row in old_queue
            if row.get('id')
            and (
                row.get('kind') == 'catalog'
                and isinstance(row.get('record'), dict)
                or row.get('kind') == 'file'
                and isinstance(row.get('source'), str)
                and (
                    Path(row['source']).is_file()
                    or isinstance(row.get('record'), dict)
                    and row['record'].get('source_url')
                )
            )
        ]
        bridge._prepared.clear()
        restored_index = next(
            (i for i, row in enumerate(bridge.playlist) if row['id'] == current_id), 0
        )
        # Neighbours are restored by the preparation worker when actually needed.
        for entry in bridge.playlist[restored_index : restored_index + 1]:
            model = restored_prepared(entry.get('prepared_cache'))
            if model:
                model['_cover'] = (
                    entry.get('cover', '').partition(',')[2]
                    if entry.get('cover', '').startswith('data:')
                    else ''
                )
                bridge._prepared[entry['id']] = bridge.retain_media_metadata(
                    model, entry
                )
                entry.update(analysis='ready', error='')
        legacy_records = {
            row.get('source'): row.get('record')
            for row in effects.get('effectsQueue', [])
            if isinstance(row, dict) and isinstance(row.get('record'), dict)
        }
        if source and effects.get('effectsRecord'):
            legacy_records[source] = effects['effectsRecord']
        for entry in bridge.playlist:
            if (
                entry.get('kind') == 'file'
                and not entry.get('record')
                and entry.get('source') in legacy_records
            ):
                entry['record'] = dict(legacy_records[entry['source']])
                bridge.queue_info(entry, entry['record'])
        bridge.queue_index = next(
            (i for i, row in enumerate(bridge.playlist) if row['id'] == current_id), -1
        )
        if not 0 <= bridge.queue_index < len(bridge.playlist):
            bridge.queue_index = -1
        bridge.setQueueRepeat(jukebox.get('repeat', 'Desativada'))
        bridge.queue_shuffle = bool(jukebox.get('shuffle', False))
        bridge._shuffle_order = [
            identity
            for identity in jukebox.get('shuffle_order', [])
            if isinstance(identity, str)
        ]
        bridge._queue_history = [
            identity
            for identity in jukebox.get('recent', [])
            if isinstance(identity, str)
        ][-200:]
        model = jukebox.get('model')
        if not model and bridge.queue_index >= 0:
            model = bridge._prepared.get(bridge.playlist[bridge.queue_index]['id'])
        if isinstance(model, dict) and 'beats' not in model:
            cached = bridge._prepared.get(current_id)
            model = (
                cached
                if cached and cached.get('cache') == model.get('cache')
                else restored_prepared(model)
            )
        seconds = jukebox.get('seconds')
        if seconds is None and isinstance(model, dict):
            beats = model.get('beats', [])
            index = min(int(jukebox.get('position', 0)), len(beats) - 2)
            if index >= 0:
                seconds = beats[index] + (beats[index + 1] - beats[index]) * float(
                    jukebox.get('phase', 0)
                )
        if type(seconds) not in (int, float) or not math.isfinite(seconds):
            seconds = 0
        seconds = max(0, seconds)
        current = (
            bridge.playlist[bridge.queue_index] if bridge.queue_index >= 0 else None
        )
        if current is not None:
            current['restore_seconds'] = seconds
        if (
            isinstance(model, dict)
            and (Path(model.get('cache', '')) / 'analysis.json').is_file()
        ):
            bridge.handle_event(bridge.revision, 'result', model)
            import bisect

            beats = model.get('beats', [])
            if len(beats) >= 2:
                seconds = min(seconds, beats[-1])
                index = max(
                    0, min(len(beats) - 2, bisect.bisect_right(beats, seconds) - 1)
                )
                phase = max(
                    0.0,
                    min(
                        1.0,
                        (seconds - beats[index])
                        / max(0.000001, beats[index + 1] - beats[index]),
                    ),
                )
                bridge._position = index + phase
                bridge._phase = phase
            params = jukebox.get('params')
            if (
                isinstance(params, list)
                and len(params) == 4
                and all(
                    isinstance(v, (int, float, bool)) and math.isfinite(v)
                    for v in params
                )
            ):
                bridge._params = tuple(params)
            bridge.update_state(
                status=__import__('i18n').tr('Sessão restaurada. Toque em reproduzir.'),
                playing=False,
                paused=False,
            )
            bridge.positionChanged.emit()
            if bridge.queue_index >= 0:
                entry = bridge.playlist[bridge.queue_index]
                entry.pop('restore_seconds', None)
                bridge._prepared[entry['id']] = model
                entry.update(analysis='ready', error='')
        elif current is not None:
            params = jukebox.get('params')
            if (
                isinstance(params, list)
                and len(params) == 4
                and all(
                    type(value) in (int, float) and math.isfinite(value)
                    for value in params[:3]
                )
                and type(params[3]) is bool
            ):
                bridge.setParams(*params)
            bridge.update_state(
                title=current.get('title')
                or current.get('record', {}).get('title', ''),
                artist=current.get('artist')
                or ', '.join(current.get('record', {}).get('artists', [])),
                album=current.get('album')
                or current.get('record', {}).get('album', ''),
                cover=current.get('cover')
                or current.get('record', {}).get('cover_url', ''),
                ready=True,
                status=__import__('i18n').tr('Sessão restaurada. Toque em reproduzir.'),
                playing=False,
                paused=False,
            )
        workspace.options['effectsEnabled'] = data.get('effectsEnabled', False) is True
        if not data.get('unified'):
            import uuid

            # Merge once. The original effects snapshot is retained for recovery.
            candidates = list(effects.get('effectsQueue', []))
            if source and not any(row.get('source') == source for row in candidates):
                candidates.insert(
                    0, dict(source=source, record=effects.get('effectsRecord', {}))
                )
            for row in candidates:
                if not isinstance(row, dict):
                    continue
                path = row.get('source', '')
                record = row.get('record') or {}
                if Path(path).is_file():
                    entry = dict(
                        id=uuid.uuid4().hex,
                        kind='file',
                        source=path,
                        record=dict(record),
                        title=record.get('title') or Path(path).stem,
                        analysis='pending',
                    )
                    if path == source:
                        entry['restore_seconds'] = max(
                            0, float(effects.get('position', 0))
                        )
                    bridge.queue_info(entry, record)
                    bridge.playlist.append(entry)
                elif record.get('source_url'):
                    entry = dict(
                        id=uuid.uuid4().hex,
                        kind='catalog',
                        record=record,
                        title=record.get('title') or path,
                        analysis='pending',
                    )
                    bridge.queue_info(entry, record)
                    bridge.playlist.append(entry)
            if not bridge.model and Path(source).is_file():
                # Restoration stays silent; preparation starts only on an explicit play.
                bridge.queue_index = next(
                    (
                        i
                        for i, row in enumerate(bridge.playlist)
                        if row.get('source') == source
                    ),
                    -1,
                )
                bridge.update_state(
                    title=effects.get('effectsRecord', {}).get('title')
                    or Path(source).stem,
                    status='Sessão restaurada. Toque em reproduzir.',
                )
                bridge._params = bridge._params[:3] + (True,)
                bridge._params = bridge._params[:2] + (
                    effects.get('effectsVolume', 80),
                    True,
                )
                bridge.setQueueRepeat(effects.get('effectsRepeat', 'Desativada'))
                bridge.setQueueShuffle(bool(effects.get('effectsShuffle', False)))
                workspace.options['effectsEnabled'] = True
        workspace.optionsChanged.emit()
        bridge.queueChanged.emit()
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return
