"""Bounded local tool checks and persistent verification/update timestamps."""

from datetime import datetime, timezone
from pathlib import Path
import importlib
import json
import os
import subprocess
import sys
import tempfile
import re


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def read(root):
    try:
        value = json.loads(
            (Path(root) / 'tool-status.json').read_text(encoding='utf-8')
        )
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save(root, values):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    report = dict(read(root), **values)
    fd, name = tempfile.mkstemp(prefix='tool-status-', suffix='.tmp', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False)
        os.replace(name, root / 'tool-status.json')
    finally:
        Path(name).unlink(missing_ok=True)
    return report


def updated(root, success):
    return save(
        root,
        {
            'updated_at': now(),
            'update_state': (
                'Atualização concluída' if success else 'Falha na atualização'
            ),
            'restart_required': bool(success)
            or read(root).get('restart_required', False),
            'update_process': (
                os.getpid() if success else read(root).get('update_process')
            ),
        },
    )


def check(root, commands):
    rows = [
        {'name': 'Python', 'version': sys.version.split()[0], 'status': 'Disponível'}
    ]
    for name, module in (
        ('yt-dlp', 'yt_dlp.version'),
        ('gallery-dl', 'gallery_dl.version'),
        ('Pillow', 'PIL'),
        ('Mutagen', 'mutagen'),
    ):
        try:
            value = importlib.import_module(module)
            version = (
                getattr(value, '__version__', None)
                or getattr(value, 'version_string', None)
                or getattr(value, 'version', None)
            )
            rows.append(
                {'name': name, 'version': str(version or '—'), 'status': 'Disponível'}
            )
        except Exception:
            rows.append({'name': name, 'version': '—', 'status': 'Indisponível'})
    for name, command in commands.items():
        try:
            from audio_tools import process_options

            run = subprocess.run(
                command, capture_output=True, text=True, timeout=12, **process_options()
            )
            if run.returncode:
                raise ValueError()
            first = (run.stdout or run.stderr).strip().splitlines()[0]
            rows.append({'name': name, 'version': first[:180], 'status': 'Disponível'})
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            rows.append({'name': name, 'version': '—', 'status': 'Indisponível'})
    old = read(root)
    return save(
        root,
        {
            'checked_at': now(),
            'tools': rows,
            'restart_required': bool(
                old.get('restart_required') and old.get('update_process') == os.getpid()
            ),
        },
    )


def present(report):
    lines = ['Situação das ferramentas']
    if report.get('checked_at'):
        lines.append('Última verificação: ' + report['checked_at'])
    else:
        lines.append('Ferramentas ainda não verificadas.')
    if report.get('updated_at'):
        lines.extend(
            [
                'Última atualização: ' + report['updated_at'],
                report.get('update_state', ''),
            ]
        )
    if report.get('restart_required'):
        lines.append(
            'Reinicie o ONDA para aplicar a atualização; as versões abaixo são da última verificação.'
        )
    lines.extend(
        str(row.get('name', ''))
        + ' · '
        + str(row.get('status', 'Indisponível'))
        + ' · '
        + str(row.get('version', '—'))
        for row in (report.get('tools') or [])
        if isinstance(row, dict)
    )
    return '\n'.join(lines)


def display(report):
    """UI projection keeps full diagnostics while shortening version banners."""
    icons = {
        'Python': 'python',
        'yt-dlp': 'yt-dlp',
        'gallery-dl': 'gallery-dl',
        'Pillow': 'pillow',
        'Mutagen': 'mutagen',
        'ffmpeg': 'ffmpeg',
        'ffprobe': 'ffprobe',
        'ffplay': 'ffplay',
        'Node.js': 'node',
        'QuickJS': 'quickjs',
    }
    rows = []
    for row in report.get('tools') or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name', ''))
        raw = str(row.get('version') or '—')
        if name in ('ffmpeg', 'ffprobe', 'ffplay'):
            match = re.match(r'^\S+\s+version\s+(\S+)', raw)
            short = match[1].split('-essentials')[0].split('-full')[0] if match else raw
        elif name == 'QuickJS' and raw == 'Execução confirmada':
            short = 'Verificado'
        else:
            short = raw
        rows.append(
            dict(
                name=name,
                version=short,
                details=raw,
                icon=icons.get(name, 'tools'),
                available=row.get('status') == 'Disponível',
                status=row.get('status') or 'Indisponível',
            )
        )
    return dict(
        tools=rows,
        checked_at=report.get('checked_at') or '',
        updated_at=report.get('updated_at') or '',
        update_state=report.get('update_state') or '',
        restart_required=bool(
            report.get('restart_required')
            and report.get('update_process', os.getpid()) == os.getpid()
        ),
        can_restart=bool(
            report.get('checked_at') and rows and all(row['available'] for row in rows)
        ),
        details=present(report),
    )
