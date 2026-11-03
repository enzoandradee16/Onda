"""Prepare the pinned Windows CPU-only image inference runtime (no npm scripts)."""

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import urllib.request


def prepare(target, archives=None):
    target = Path(target).resolve()
    packages = json.loads(
        Path(__file__)
        .with_name('background-runtime.json')
        .read_text(encoding='utf-8-sig')
    )
    for package in packages:
        if archives:
            data = (Path(archives) / (package['name'] + '.tgz')).read_bytes()
        else:
            with urllib.request.urlopen(package['url'], timeout=60) as response:
                data = response.read(150 * 1024 * 1024 + 1)
        if len(data) > 150 * 1024 * 1024:
            raise ValueError('Archive exceeds expected size')
        expected = package['integrity'].removeprefix('sha512-')
        if base64.b64encode(hashlib.sha512(data).digest()).decode() != expected:
            raise ValueError('Runtime archive checksum mismatch')
        destination = target / 'node_modules' / package['name']
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                relative = PurePosixPath(member.name).relative_to('package')
                if '..' in relative.parts:
                    raise ValueError('Invalid archive member')
                allowed = (
                    relative.parts[0] == 'dist'
                    and relative.suffix in ('.js', '.json')
                    or str(relative) == 'package.json'
                    or 'license' in relative.name.lower()
                    or 'notice' in relative.name.lower()
                    or str(relative)
                    in (
                        'bin/napi-v6/win32/x64/onnxruntime.dll',
                        'bin/napi-v6/win32/x64/onnxruntime_binding.node',
                    )
                )
                if not allowed:
                    continue
                output = (destination / Path(*relative.parts)).resolve()
                if not output.is_relative_to(target):
                    raise ValueError('Extraction path outside runtime')
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, output.open('wb') as result:
                    shutil.copyfileobj(source, result)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--target',
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / 'Portatil/_runtime/image-background-node',
    )
    parser.add_argument('--archives', type=Path)
    args = parser.parse_args()
    print(prepare(args.target, args.archives))
