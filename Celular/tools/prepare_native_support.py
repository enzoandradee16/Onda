"""Extract only FFmpeg's native support libraries from the upstream runtime archive."""
from pathlib import Path
import io
import sys
import zipfile

output=Path(sys.argv[1])
for filename in sys.argv[2:]:
    with zipfile.ZipFile(filename) as aar:
        for abi in ('arm64-v8a','x86_64'):
            name=f'jni/{abi}/libpython.zip.so'
            if not (output/abi).is_dir() or name not in aar.namelist():
                continue
            target=output/abi/'libonda-support.zip.so'
            target.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(aar.read(name))) as source, zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
                for info in source.infolist():
                    parts=Path(info.filename).parts
                    if len(parts)==3 and parts[:2]==('usr','lib') and '.so' in parts[-1] and not parts[-1].startswith('libpython'):
                        archive.writestr(info,source.read(info))
