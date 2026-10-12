"""Build an offline Windows bundle from a local CPython with Tcl/Tk."""
import argparse
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

parser = argparse.ArgumentParser()
parser.add_argument('--python-home', required=True, type=Path)
parser.add_argument('--ffmpeg-home', required=True, type=Path)
parser.add_argument('--node', required=True, type=Path)
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
runtime = out / '_runtime' / 'python'
runtime.mkdir(parents=True, exist_ok=True)
for pattern in ('*.exe', '*.dll', 'LICENSE.txt'):
    for path in args.python_home.glob(pattern):
        shutil.copy2(path, runtime / path.name)
for name in ('Lib', 'DLLs', 'tcl'):
    shutil.copytree(args.python_home / name, runtime / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', 'test', 'tests', 'site-packages', 'idlelib', 'ensurepip', 'EXTERNALLY-MANAGED'))
shutil.copytree(args.python_home / 'Lib/site-packages', runtime / 'Lib/site-packages', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(args.source, out / 'Onda', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', 'downloads', '.venv', 'test_*.py', '*.bat'))
ffmpeg = out / '_runtime/ffmpeg'
shutil.copytree(args.ffmpeg_home / 'bin', ffmpeg, dirs_exist_ok=True)
shutil.copy2(args.ffmpeg_home / 'LICENSE', ffmpeg / 'LICENSE.txt')
shutil.copy2(args.ffmpeg_home / 'README.txt', ffmpeg / 'README.txt')
shutil.copytree(args.ffmpeg_home / 'doc', ffmpeg / 'doc', dirs_exist_ok=True)
node = out / '_runtime/node'
node.mkdir(parents=True, exist_ok=True)
shutil.copy2(args.node, node / 'node.exe')

# Code-drawn wave icon, stored as PNG inside a Windows ICO.
size = 64
rows = []
for y in range(size):
    row = bytearray([0])
    for x in range(size):
        on = any(abs(x - center) <= 2 and low <= y <= high for center, low, high in ((12,24,40),(22,14,50),(32,7,57),(42,19,45),(52,26,38)))
        row.extend((121,226,196,255) if on else (16,20,25,255))
    rows.append(row)
def chunk(name, data):
    return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size,size,8,6,0,0,0)) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')
(out / 'onda.ico').write_bytes(struct.pack('<HHH',0,1,1) + struct.pack('<BBBBHHII',size,size,0,0,1,32,len(png),22) + png)
subprocess.run([str(runtime / 'python.exe'), '-s', '-m', 'pip', '--disable-pip-version-check', 'install', '-r', str(out / 'Onda/requirements.txt')], check=True)
print('Bundle ready:', out)
