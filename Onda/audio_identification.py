"""Identify a local recording through Chromaprint and AcoustID."""

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

from app_version import VERSION

CLIENT = 'vRD9rnTlW1'
FPCALC_ASSET = 'chromaprint-fpcalc-1.6.1-windows-x86_64'
FPCALC_SHA256 = '735d6182b38e9f364b84ce6f4ccd682c75e2851de89735711d6b762d12b92a4e'


def fingerprint_tool():
    installed = shutil.which('fpcalc')
    if installed:
        return installed
    if os.name != 'nt':
        raise RuntimeError('Instale o Chromaprint (fpcalc) para identificar pelo áudio.')
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Onda/tools/chromaprint/1.6.1'
    executable = folder / 'fpcalc.exe'
    if executable.is_file():
        return executable
    url = f'https://github.com/acoustid/chromaprint/releases/download/v1.6.1/{FPCALC_ASSET}.zip'
    with urlopen(url, timeout=30) as response:
        archive = response.read(32 * 1024 * 1024)
    if hashlib.sha256(archive).hexdigest() != FPCALC_SHA256:
        raise RuntimeError('Não foi possível verificar o Chromaprint.')
    folder.mkdir(parents=True, exist_ok=True)
    with ZipFile(io.BytesIO(archive)) as package:
        binary = package.read(f'{FPCALC_ASSET}/fpcalc.exe')
    with tempfile.TemporaryDirectory(dir=folder) as staging:
        temporary = Path(staging) / executable.name
        temporary.write_bytes(binary)
        try:
            temporary.replace(executable)
        except PermissionError:
            if not executable.is_file():
                raise
    return executable


def identify_audio(source, cancel):
    tool = fingerprint_tool()
    if cancel.is_set():
        return {}
    result = subprocess.run(
        [str(tool), '-json', '-length', '120', str(Path(source).resolve())],
        capture_output=True,
        timeout=45,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    if cancel.is_set():
        return {}
    try:
        fingerprint = json.loads(result.stdout)
        duration = round(float(fingerprint['duration']))
        fingerprint = fingerprint['fingerprint']
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError('Não foi possível gerar a impressão digital do áudio.') from error
    if duration <= 0 or not fingerprint:
        return {}
    data = urlencode({
        'client': CLIENT,
        'duration': duration,
        'fingerprint': fingerprint,
        'meta': 'recordings releasegroups',
        'format': 'json',
    }).encode('ascii')
    request = Request(
        'https://api.acoustid.org/v2/lookup', data=data,
        headers={'User-Agent': f'ONDA/{VERSION} (https://github.com/enzoandradee16/Onda)'},
    )
    with urlopen(request, timeout=15) as response:
        result = json.load(response)
    if result.get('status') != 'ok':
        raise RuntimeError('O AcoustID não conseguiu consultar a gravação.')
    for match in sorted(result.get('results', []), key=lambda item: item['score'], reverse=True):
        if match['score'] < 0.8:
            break
        recordings = [
            row for row in match.get('recordings', [])
            if row.get('title') and row.get('artists')
        ]
        if not recordings:
            continue
        recording = min(recordings, key=lambda row: abs((row.get('duration') or duration) - duration))
        fields = dict(title=recording['title'], artists=[artist['name'] for artist in recording['artists']])
        return enrich_recording(recording.get('id'), fields, cancel)
    return {}


def enrich_recording(identity, fields, cancel):
    import requests
    from artist_alias_lookup import AliasCache, LookupUnavailable, get_json
    from uuid import UUID

    if not identity or cancel.is_set():
        return fields
    try:
        identity = str(UUID(identity))
        cache = AliasCache()
        recording = get_json(f'recording/{identity}', {'inc': 'releases+isrcs'}, cache)
        codes = set(recording.get('isrcs', []))
        if len(codes) == 1:
            fields['isrc'] = codes.pop()
        editions = [row for row in recording.get('releases', []) if row.get('status') == 'Official']
        if not editions or cancel.is_set():
            return fields
        edition = min(editions, key=lambda row: (row.get('date') or '9999', row['id']))
        release_id = str(UUID(edition['id']))
        release = get_json(f'release/{release_id}', {'inc': 'recordings'}, cache)
        fields['album'] = release['title']
        if release.get('date'):
            fields['release_date'] = release['date']
        for medium in release.get('media', []):
            track = next((track for track in medium.get('tracks', [])
                          if track.get('recording', {}).get('id') == identity), None)
            if track:
                fields['track_number'] = str(track['position'])
                fields['disc_number'] = str(medium['position'])
                break
        if release.get('cover-art-archive', {}).get('front') and not cancel.is_set():
            url = f'https://coverartarchive.org/release/{release_id}/front-500'
            with urlopen(url, timeout=10) as response:
                cover = response.read(5 * 1024 * 1024 + 1)
            if len(cover) <= 5 * 1024 * 1024 and cover.startswith(b"\xff\xd8\xff"):
                fields['cover'] = 'data:image/jpeg;base64,' + base64.b64encode(cover).decode('ascii')
    except (OSError, ValueError, LookupUnavailable, requests.RequestException):
        pass
    return fields
