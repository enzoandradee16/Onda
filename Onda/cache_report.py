"""Read-only accounting and targeted eviction of known disposable cache groups."""

from pathlib import Path
import json
import time


def report(root, protected=(), limit_mb=1024, models=()):
    from cache_cleanup import cache_files, linked
    from playback_cache_budget import _entries, recent_paths
    from jukebox import _active_lock, _active
    from progressive_audio_cache import _lock, _active as streams

    root = Path(root)
    playback = root / 'jukebox'
    with _active_lock:
        leases = [Path(p).resolve() for p in _active]
    with _lock:
        leases += list(streams)
    leases += [Path(p).resolve() for p in protected]
    entries = list(_entries(playback))
    recent = recent_paths(playback, entries=entries)
    categories = {
        'Áudio temporário': 0,
        'Efeitos': 0,
        'Capas e imagens': 0,
        'Buscas e metadados': 0,
    }
    index = playback / 'cache-names.json'
    names = {}
    try:
        if index.is_file() and not linked(index) and index.stat().st_size < 1048576:
            names = json.loads(index.read_text(encoding='utf8'))
    except (OSError, ValueError):
        pass
    if not isinstance(names, dict):
        names = {}
    changed = False
    models = list(models)
    session = root / 'playback-session.json'
    try:
        if (
            session.is_file()
            and not linked(session)
            and session.stat().st_size < 8 * 1024 * 1024
        ):
            saved = json.loads(session.read_text(encoding='utf8')).get('jukebox', {})
            if isinstance(saved.get('model'), dict):
                models.append(saved['model'])
            models += [
                dict(
                    row['prepared_cache'],
                    media_title=row.get('title')
                    or row['prepared_cache'].get('media_title'),
                )
                for row in saved.get('queue', [])
                if isinstance(row, dict) and isinstance(row.get('prepared_cache'), dict)
            ]
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    for model in models:
        if not isinstance(model, dict):
            continue
        title = model.get('media_title') or model.get('title')
        location = model.get('cache')
        if title and isinstance(location, str):
            try:
                key = str(Path(location).resolve().relative_to(playback.resolve()))
                if names.get(key) != title:
                    names[key] = str(title)[:300]
                    changed = True
            except ValueError:
                pass
    if changed and playback.is_dir() and not linked(playback):
        import uuid, os

        temporary = playback / ('names-' + uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_text(
                json.dumps(dict(list(names.items())[-2000:]), ensure_ascii=False),
                encoding='utf8',
            )
            os.replace(temporary, index)
        except OSError:
            temporary.unlink(missing_ok=True)
    tracks = []
    protected_bytes = 0
    for _, modified, _, size, path in entries:
        category = 'Efeitos' if path.name.startswith('effects-') else 'Áudio temporário'
        try:
            effects = (
                size
                if category == 'Efeitos'
                else (
                    sum(
                        p.stat().st_size
                        for p in path.iterdir()
                        if p.name.startswith('effects-')
                    )
                    if path.is_dir()
                    else 0
                )
            )
        except OSError:
            continue
        categories['Efeitos'] += effects
        categories['Áudio temporário'] += size - effects
        resolved = path.resolve()
        active = any(
            p == resolved or p.is_relative_to(resolved) or resolved.is_relative_to(p)
            for p in leases
        )
        fresh = time.time() - modified < 120
        keep = active or path in recent or fresh
        if keep:
            protected_bytes += size
        try:
            files = list(path.iterdir()) if path.is_dir() else [path]
            audio = [
                item
                for item in files
                if item.suffix.lower()
                in ('.wav', '.pcm', '.mka', '.mp3', '.m4a', '.flac', '.ogg', '.opus')
                and item.stat().st_size > 0
            ]
        except OSError:
            continue
        if not audio:
            continue
        title = names.get(str(path.relative_to(playback)), 'Áudio sem identificação')
        manifest = path / 'analysis.json'
        if path.is_dir() and manifest.is_file() and not linked(manifest):
            try:
                if manifest.stat().st_size <= 8 * 1024 * 1024:
                    model = json.loads(manifest.read_text(encoding='utf8'))
                    title = model.get('media_title') or model.get('title') or title
            except (ValueError, OSError):
                pass
        tracks.append(
            dict(
                id=str(path.relative_to(playback)),
                name=title,
                bytes=size,
                protected=keep,
                reason=(
                    'Em uso ou preparada'
                    if active
                    else (
                        'Preservada para voltar'
                        if path in recent
                        else (
                            'Preparada recentemente'
                            if fresh
                            else 'Pode ser preparada novamente'
                        )
                    )
                ),
            )
        )
    for path in cache_files(root):
        relative = path.relative_to(root)
        if relative.parts[0] == 'jukebox':
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        categories[
            (
                'Capas e imagens'
                if relative.parts[0] in ('image-preview', 'online-image-preview')
                else 'Buscas e metadados'
            )
        ] += size
    alias = root / 'artist-aliases.sqlite3'
    if alias.is_file() and not linked(alias):
        categories['Buscas e metadados'] += alias.stat().st_size
    total = sum(categories.values())
    return dict(
        bytes=total,
        categories=[dict(name=name, bytes=size) for name, size in categories.items()],
        tracks=tracks,
        protected_bytes=protected_bytes,
        removable_bytes=max(0, total - protected_bytes),
        limit_mb=limit_mb,
        over_budget=categories['Áudio temporário'] + categories['Efeitos']
        > limit_mb * 1048576,
    )


def remove(root, identity, protected=()):
    from playback_cache_budget import prune, _entries

    root = Path(root)
    playback = root / 'jukebox'
    data = report(root, protected)
    row = next((r for r in data['tracks'] if r['id'] == identity), None)
    if not row:
        raise ValueError('Este cache não está mais disponível.')
    if row['protected']:
        raise ValueError('Esta música está protegida para reprodução ou para voltar.')
    target = (playback / identity).resolve()
    if not target.is_relative_to(playback.resolve()):
        raise ValueError('Cache inválido.')
    keep = list(protected) + [
        str(p) for *_, p in _entries(playback) if p.resolve() != target
    ]
    result = prune(playback, protected=keep, max_bytes=0)
    return dict(
        result, message='Cache removido. A música poderá ser preparada novamente.'
    )
