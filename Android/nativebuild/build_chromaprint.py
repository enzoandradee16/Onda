"""Build the pinned Chromaprint library for Android; no host installation required."""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

SOURCE_SHA256 = 'd54ada62c16b2db396d3251ec54fc7a58909c163131a1cfcf7fa6407dbc14360'


def build(work, output):
    work, output = Path(work).resolve(), Path(output).resolve()
    source = work / 'chromaprint-1.6.2'
    archive = work / 'chromaprint-1.6.2.tar.gz'
    if not source.is_dir():
        source = work / 'src/chromaprint-1.6.2'
    if not archive.is_file():
        archive = work / 'sources/chromaprint-1.6.2.tar.gz'
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == SOURCE_SHA256
    cmake = work / 'tooling/cmake/data/bin/cmake.exe'
    ninja = work / 'tooling/bin/ninja.exe'
    if not cmake.is_file():
        cmake = work / 'msys64/ucrt64/bin/cmake.exe'
    if not ninja.is_file():
        ninja = work / 'msys64/ucrt64/bin/ninja.exe'
    ndk = work / 'android-ndk-r28c'
    for abi in ('arm64-v8a', 'x86_64'):
        folder = work / ('chromaprint-build-' + abi)
        subprocess.run(
            [
                str(cmake),
                '-S',
                str(source),
                '-B',
                str(folder),
                '-G',
                'Ninja',
                '-DCMAKE_MAKE_PROGRAM=' + str(ninja),
                '-DCMAKE_TOOLCHAIN_FILE='
                + str(ndk / 'build/cmake/android.toolchain.cmake'),
                '-DANDROID_ABI=' + abi,
                '-DANDROID_PLATFORM=android-26',
                '-DANDROID_STL=c++_static',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DBUILD_TESTS=OFF',
                '-DBUILD_TOOLS=OFF',
                '-DBUILD_SHARED_LIBS=ON',
                '-DFFT_LIB=kissfft',
                '-DKISSFFT_SOURCE_DIR=' + str(source / 'src/3rdparty/kissfft'),
                '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384',
            ],
            check=True,
        )
        subprocess.run(
            [str(cmake), '--build', str(folder), '--target', 'chromaprint', '-j', '2'],
            check=True,
        )
        library = next((folder / 'src').glob('libchromaprint.so*'))
        target = output / abi / 'libchromaprint.so'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(library, target)
        strip = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe'
        subprocess.run([str(strip), '--strip-unneeded', str(target)], check=True)
        print(abi, target.stat().st_size, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True)
    parser.add_argument(
        '--output', default=str(Path(__file__).resolve().parents[1] / 'native-tools')
    )
    args = parser.parse_args()
    build(args.work, args.output)
