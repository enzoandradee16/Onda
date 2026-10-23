#!/usr/bin/env bash
set -euo pipefail
BASE=$(cd "$(dirname "$0")" && pwd)
export PATH="$BASE/msys64/ucrt64/bin:$BASE/msys64/usr/bin:$PATH"
export GCC_EXEC_PREFIX="$(cygpath -m "$BASE/msys64/ucrt64/lib/gcc")/"
NDK="$BASE/android-ndk-r28c"
TC="$NDK/toolchains/llvm/prebuilt/windows-x86_64/bin"
mkdir -p "$BASE/tmp"
export TMPDIR="$(cygpath -m "$BASE/tmp")"
export TMP="$TMPDIR" TEMP="$TMPDIR"
ABI=${1:-arm64-v8a}
case "$ABI" in arm64-v8a) TARGET=aarch64-linux-android; ARCH=aarch64;; x86_64) TARGET=x86_64-linux-android; ARCH=x86_64;; *) exit 2;; esac
PREFIX="$BASE/install/$ABI"
BUILD="$BASE/build/$ABI"
mkdir -p "$PREFIX" "$BUILD" "$BASE/out/$ABI"
export CC="$TC/clang.exe --target=${TARGET}26"
export CXX="$TC/clang++.exe --target=${TARGET}26"
export AR="$TC/llvm-ar.exe" RANLIB="$TC/llvm-ranlib.exe" STRIP="$TC/llvm-strip.exe"
export CFLAGS='-O2 -fPIC -ffunction-sections -fdata-sections'
export LDFLAGS='-Wl,-z,max-page-size=16384 -Wl,--gc-sections'
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"
export PKG_CONFIG='pkgconf --static'
JOBS=6
cmake_build() {
 local name=$1;shift
 if [[ -f "$BUILD/$name.done" ]];then return;fi
 cmake -S "$BASE/src/$name" -B "$BUILD/$name" -G 'MSYS Makefiles' \
  -DCMAKE_TOOLCHAIN_FILE="$(cygpath -m "$NDK/build/cmake/android.toolchain.cmake")" \
  -DANDROID_ABI="$ABI" -DANDROID_PLATFORM=android-26 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$(cygpath -m "$PREFIX")" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_SHARED_LIBS=OFF "$@"
 cmake --build "$BUILD/$name" -j "$JOBS"
 cmake --install "$BUILD/$name"
 touch "$BUILD/$name.done"
}
cmake_build libogg-1.3.6 -DBUILD_TESTING=OFF
cmake_build libvorbis-1.3.7 -DBUILD_TESTING=OFF -DOGG_INCLUDE_DIR="$(cygpath -m "$PREFIX/include")" -DOGG_LIBRARY="$(cygpath -m "$PREFIX/lib/libogg.a")"
cmake_build opus-1.5.2 -DOPUS_BUILD_TESTING=OFF -DOPUS_BUILD_PROGRAMS=OFF
cmake_build libwebp-1.6.0 -DWEBP_BUILD_ANIM_UTILS=OFF -DWEBP_BUILD_CWEBP=OFF -DWEBP_BUILD_DWEBP=OFF -DWEBP_BUILD_GIF2WEBP=OFF -DWEBP_BUILD_IMG2WEBP=OFF -DWEBP_BUILD_VWEBP=OFF -DWEBP_BUILD_WEBPINFO=OFF -DWEBP_BUILD_EXTRAS=OFF -DWEBP_BUILD_WEBPMUX=OFF -DWEBP_BUILD_LIBWEBPMUX=ON -DWEBP_BUILD_LIBWEBPDEMUX=ON
cmake_build mbedtls-3.6.4 -DENABLE_PROGRAMS=OFF -DENABLE_TESTING=OFF -DMBEDTLS_FATAL_WARNINGS=OFF
if [[ ! -f "$BUILD/lame.done" ]];then
 mkdir -p "$BUILD/lame";cd "$BUILD/lame"
 "$BASE/src/lame-3.100/configure" --host="$TARGET" --prefix="$PREFIX" --disable-shared --enable-static --disable-frontend --disable-dependency-tracking
 make -j "$JOBS";make install;touch "$BUILD/lame.done"
fi
if [[ ! -f "$BUILD/x264.done" ]];then
 mkdir -p "$BUILD/x264";cd "$BUILD/x264"
 "$BASE/src/x264-b35605ace3ddf7c1a5d67a2eb553f034aef41d55/configure" --host="$TARGET" --prefix="$PREFIX" --enable-static --enable-pic --disable-cli --disable-opencl
 make -j "$JOBS";make install;touch "$BUILD/x264.done"
fi
if [[ ! -f "$BUILD/ffmpeg.done" ]];then
 mkdir -p "$BUILD/ffmpeg";cd "$BUILD/ffmpeg"
 "$BASE/src/ffmpeg-7.1.3/configure" --prefix="$PREFIX" --target-os=android --arch="$ARCH" --enable-cross-compile \
  --cc="$CC" --cxx="$CXX" --ar="$AR" --ranlib="$RANLIB" --strip="$STRIP" --nm="$TC/llvm-nm.exe" \
  --host-cc=gcc --extra-libs=-lm --pkg-config=pkgconf --pkg-config-flags=--static \
  --extra-cflags="-I$PREFIX/include -O2 -fPIC" --extra-ldflags="-L$PREFIX/lib -Wl,-z,max-page-size=16384 -Wl,--gc-sections" \
  --enable-static --disable-shared --enable-gpl --enable-version3 --enable-libmp3lame --enable-libx264 --enable-libwebp \
  --enable-libopus --enable-libvorbis --enable-mbedtls --enable-jni --enable-mediacodec \
  --disable-autodetect --disable-doc --disable-debug --disable-ffplay --disable-indevs --enable-indev=lavfi --disable-outdevs --enable-zlib
 make -j "$JOBS" ffmpeg ffprobe
 cp ffmpeg "$BASE/out/$ABI/libffmpeg.so";cp ffprobe "$BASE/out/$ABI/libffprobe.so"
 cp config.h config_components.h "$BASE/out/$ABI/"
 cp ffbuild/config.log "$BASE/out/$ABI/ffmpeg-config.log"
 touch "$BUILD/ffmpeg.done"
fi
if [[ ! -f "$BASE/build/host-qjsc.done" ]];then
 mkdir -p "$BASE/build/quickjs-host"
 cp -R "$BASE/src/quickjs-2025-09-13/." "$BASE/build/quickjs-host/"
 cd "$BASE/build/quickjs-host"
 make -j "$JOBS" qjsc.exe CONFIG_WIN32=y CROSS_PREFIX= CC=gcc AR=ar LDFLAGS=
 touch "$BASE/build/host-qjsc.done"
fi
if [[ ! -f "$BUILD/quickjs.done" ]];then
 mkdir -p "$BUILD/quickjs";cp -R "$BASE/src/quickjs-2025-09-13/." "$BUILD/quickjs/";cd "$BUILD/quickjs"
 "$BASE/build/quickjs-host/qjsc.exe" -c -o repl.c -m repl.js
 $CC $CFLAGS -D_GNU_SOURCE '-DCONFIG_VERSION="2025-09-13"' qjs.c repl.c quickjs.c dtoa.c libregexp.c libunicode.c cutils.c quickjs-libc.c -lm -ldl -pthread $LDFLAGS -o "$BASE/out/$ABI/libqjs.so"
 touch "$BUILD/quickjs.done"
fi
for name in ffmpeg ffprobe qjs;do "$STRIP" "$BASE/out/$ABI/lib$name.so";done
printf 'Finished native tools: %s\n' "$ABI"
