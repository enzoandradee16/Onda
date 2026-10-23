"""Build a Windows bundle; FFmpeg is fetched on first launch from a local CPython with Tcl/Tk."""
import argparse
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--python-home', required=True, type=Path)
parser.add_argument('--ffmpeg-home', type=Path, help='Deprecated; FFmpeg is downloaded on first launch')
parser.add_argument('--node', required=True, type=Path)
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
from sync_version import sync_version
sync_version(args.source.resolve().parent)
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
# Do not silently retain FFmpeg from an older output directory.
if (out / '_runtime/ffmpeg').exists():
    raise RuntimeError('Use a fresh output folder: FFmpeg must not be bundled.')
node = out / '_runtime/node'
node.mkdir(parents=True, exist_ok=True)
shutil.copy2(args.node, node / 'node.exe')

# Preserve application licensing and dependency inventory in distributions.
for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md'):
    shutil.copy2(args.source.parent / name, out / name)
shutil.copytree(args.source.parent / 'docs', out / 'docs', dirs_exist_ok=True)

# Install into the private runtime before rendering (a fresh build host need not have Pillow).
subprocess.run([str(runtime / 'python.exe'), '-s', '-m', 'pip', '--disable-pip-version-check', 'install', '-r', str(out / 'Onda/requirements.txt')], check=True)
# Use the same continuous wave as the running application at every Windows icon size.
render_icon="import sys;sys.path.insert(0,sys.argv[1]);from brand_mark import icon;icon(256).save(sys.argv[2],format='ICO',sizes=[(n,n) for n in (16,24,32,48,64,128,256)])"
subprocess.run([str(runtime/'python.exe'),'-s','-c',render_icon,str((out/'Onda').resolve()),str(out/'onda.ico')],check=True)
print('Bundle ready:', out)
