"""Atomic, bounded updates of allowlisted pure-Python Android tools from PyPI.

Native libraries remain part of the signed APK. A failed download never replaces
the active generation, and a newer APK always wins over an older cached bundle.
"""

import hashlib
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from urllib.parse import urlparse
import uuid
import zipfile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

# Entire dependency closure is kept together; no arbitrary packages or native code.
PACKAGES = {
    'yt-dlp': '',
    'yt-dlp-ejs': '<0.9',
    'gallery-dl': '<2',
    'mutagen': '<2',
    'requests': '<3',
    'urllib3': '<3',
    'charset-normalizer': '<4',
    'idna': '<4',
    'certifi': '',
}
LIMIT = 40 * 1024 * 1024


def _canonical(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def _get(client, url, host, **kwargs):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != host or parsed.username:
        raise ValueError('Origem da atualização inválida.')
    response = client.get(url, timeout=(10, 30), allow_redirects=False, **kwargs)
    response.raise_for_status()
    if response.status_code != 200:
        raise ValueError('Resposta da atualização inválida.')
    return response


def _validate_dependencies(infos, versions):
    environment = dict(default_environment(), extra='')
    for info in infos:
        for text in info.get('requires_dist') or []:
            req = Requirement(text)
            if req.marker and not req.marker.evaluate(environment):
                continue
            name = _canonical(req.name)
            try:
                installed = versions.get(name) or metadata.version(name)
            except metadata.PackageNotFoundError:
                raise ValueError('Dependência indisponível: ' + name) from None
            if req.url or not req.specifier.contains(installed, prereleases=False):
                raise ValueError('Dependência incompatível: ' + name)


def _verify_wheel(path, package, version):
    with zipfile.ZipFile(path) as archive:
        total = 0
        for member in archive.infolist():
            parts = member.filename.split('/')
            total += member.file_size
            if member.is_dir() or not member.filename:
                continue
            if (
                any(p in ('', '.', '..') for p in parts)
                or '\\' in member.filename
                or ':' in member.filename
                or member.filename.lower().endswith(('.so', '.dll', '.pyd', '.pth'))
                or total > 150 * 1024 * 1024
            ):
                raise ValueError('Conteúdo de atualização inválido.')
        records = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
        if len(records) != 1 or archive.testzip():
            raise ValueError('Pacote de atualização inválido.')
        from email.parser import BytesParser

        info = BytesParser().parsebytes(archive.read(records[0]))
        if _canonical(info['Name']) != package or Version(info['Version']) != Version(
            version
        ):
            raise ValueError('Identificação do pacote inválida.')


def prepare(root, emit=lambda *a, **k: None, client=None):
    if client is None:
        import requests

        client = requests
    folder = Path(root) / 'tools' / 'python-updates'
    folder.mkdir(parents=True, exist_ok=True)
    previous, cached = {}, None
    try:
        active = (folder / 'active').read_text(encoding='ascii')
        if re.fullmatch('[0-9a-f]{32}', active):
            cached = folder / active
            previous = json.loads((cached / 'manifest.json').read_text(encoding='utf8'))
            if (
                not isinstance(previous, dict)
                or not isinstance(previous.get('versions'), dict)
                or not isinstance(previous.get('hashes'), dict)
            ):
                previous = {}
    except (OSError, ValueError):
        pass
    for orphan in folder.glob('pending-*'):
        if (
            orphan.is_dir()
            and not orphan.is_symlink()
            and orphan.resolve().parent == folder.resolve()
            and time.time() - orphan.stat().st_mtime > 86400
        ):
            shutil.rmtree(orphan, ignore_errors=True)
    # Staging is private and becomes active only after every package is verified.
    stage = Path(tempfile.mkdtemp(prefix='pending-', dir=folder))
    try:
        versions, files, infos = {}, {}, []
        all_reused = True
        for name, constraint in PACKAGES.items():
            emit('stage', message='Consultando ' + name + '…', done=0, total=0)
            data = _get(
                client, 'https://pypi.org/pypi/' + name + '/json', 'pypi.org'
            ).json()
            info = data['info']
            value = Version(info['version'])
            if (
                value.is_prerelease
                or value.is_devrelease
                or value not in SpecifierSet(constraint)
            ):
                raise ValueError('Nova versão requer atualização do ONDA: ' + name)
            if not SpecifierSet(info.get('requires_python') or '').contains(
                sys.version.split()[0]
            ):
                raise ValueError(
                    'Nova versão requer atualização do Python no ONDA: ' + name
                )
            try:
                if value < Version(metadata.version(name)):
                    raise ValueError(
                        'A atualização não pode diminuir a versão: ' + name
                    )
            except metadata.PackageNotFoundError:
                pass
            wheel = next(
                (
                    f
                    for f in data['urls']
                    if not f.get('yanked')
                    and f['filename'].endswith(
                        ('-py3-none-any.whl', '-py2.py3-none-any.whl')
                    )
                    and SpecifierSet(f.get('requires_python') or '').contains(
                        sys.version.split()[0]
                    )
                ),
                None,
            )
            if not wheel:
                raise ValueError('Pacote compatível indisponível: ' + name)
            path = stage / (name + '.whl')
            expected = wheel['digests']['sha256']
            reused = False
            if (
                cached is not None
                and previous.get('versions', {}).get(name) == str(value)
                and previous.get('hashes', {}).get(name) == expected
            ):
                existing = cached / path.name
                try:
                    if (
                        existing.is_file()
                        and not existing.is_symlink()
                        and existing.stat().st_size <= LIMIT
                    ):
                        shutil.copyfile(existing, path)
                        with path.open('rb') as stream:
                            reused = (
                                hashlib.file_digest(stream, 'sha256').hexdigest()
                                == expected
                            )
                except OSError:
                    pass
            if reused:
                emit('stage', message='Verificando ' + name + '…', done=0, total=0)
                _verify_wheel(path, name, str(value))
                versions[name], files[name] = str(value), expected
                infos.append(info)
                continue
            all_reused = False
            digest, size = hashlib.sha256(), 0
            with _get(
                client, wheel['url'], 'files.pythonhosted.org', stream=True
            ) as response:
                with path.open('wb') as stream:
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > LIMIT:
                            raise ValueError('Atualização acima do limite.')
                        digest.update(chunk)
                        stream.write(chunk)
                        emit(
                            'stage',
                            message='Baixando ' + name + '…',
                            done=size,
                            total=int(wheel.get('size') or 0),
                        )
            if digest.hexdigest() != expected:
                raise ValueError('A verificação da atualização falhou: ' + name)
            _verify_wheel(path, name, str(value))
            versions[name] = str(value)
            files[name] = digest.hexdigest()
            infos.append(info)
        emit(
            'stage', message='Verificando atualização das ferramentas…', done=0, total=0
        )
        _validate_dependencies(infos, versions)
        if (
            all_reused
            and previous.get('versions') == versions
            and previous.get('hashes') == files
        ):
            return versions
        manifest = dict(
            generation=uuid.uuid4().hex,
            versions=versions,
            hashes=files,
            dependencies=infos,
        )
        # Store only dependency metadata, never the remote project descriptions.
        manifest['dependencies'] = [
            {'requires_dist': i.get('requires_dist')} for i in infos
        ]
        (stage / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        destination = folder / manifest['generation']
        os.replace(stage, destination)
        pointer = folder / 'active.next'
        pointer.write_text(manifest['generation'], encoding='ascii')
        os.replace(pointer, folder / 'active')
        # Retain the preceding generation and any wheel still used by this process.
        generations = sorted(
            (
                p
                for p in folder.iterdir()
                if p.is_dir() and re.fullmatch('[0-9a-f]{32}', p.name)
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in generations[2:]:
            if (
                not any(str(old) in path for path in sys.path)
                and old.resolve().parent == folder.resolve()
            ):
                shutil.rmtree(old, ignore_errors=True)
        return versions
    finally:
        # This is always the mkdtemp directory inside the update folder.
        if stage.is_dir() and stage.parent.resolve() == folder.resolve():
            shutil.rmtree(stage)


def activate(root):
    """Verify cache again, reject downgrades, then prepend verified wheel paths."""
    folder = Path(root) / 'tools' / 'python-updates'
    try:
        generation = (folder / 'active').read_text(encoding='ascii')
        if not re.fullmatch('[0-9a-f]{32}', generation):
            return False
        stage = folder / generation
        manifest = json.loads((stage / 'manifest.json').read_text(encoding='utf8'))
        versions = manifest['versions']
        if set(versions) != set(PACKAGES):
            return False
        newer = False
        paths = []
        for name, value in versions.items():
            baseline = Version(metadata.version(name))
            if Version(value) < baseline or Version(value) not in SpecifierSet(
                PACKAGES[name]
            ):
                return False
            newer |= Version(value) > baseline
            path = stage / (name + '.whl')
            if (
                path.stat().st_size > LIMIT
                or hashlib.sha256(path.read_bytes()).hexdigest()
                != manifest['hashes'][name]
            ):
                return False
            _verify_wheel(path, name, value)
            paths.append(str(path))
        if not newer:
            return False
        _validate_dependencies(manifest['dependencies'], versions)
        previous_modules = set(sys.modules)
        sys.path[:0] = paths
        try:
            for module in ('yt_dlp', 'yt_dlp_ejs', 'gallery_dl', 'mutagen', 'requests'):
                importlib.import_module(module)
        except Exception:
            sys.path[:] = [p for p in sys.path if p not in paths]
            for module in set(sys.modules) - previous_modules:
                sys.modules.pop(module, None)
            return False
        return True
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        metadata.PackageNotFoundError,
    ):
        return False
