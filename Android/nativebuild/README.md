# Ferramentas nativas Android construídas pelo ONDA

FFmpeg, FFprobe, QuickJS e Chromaprint são compilados a partir dos fontes verificados em `source-lock.json`. O Python do aplicativo é fornecido pelo Chaquopy.

## Componentes e construção

- FFmpeg / FFprobe 9.0.2: configuração resultante GPL-3.0-or-later.
- LAME 4.0 (MP3), x264 b35605ace3ddf7c1a5d67a2eb553f034aef41d55 (H.264), WebP 1.6.0, Opus 1.5.2, Ogg 1.3.6 e Vorbis 1.3.7.
- Mbed TLS 3.6.8 para HTTPS. AAC, FLAC, WAV, filtros e demais codecs internos são fornecidos pelo FFmpeg.
- QuickJS 2026-06-04, MIT, para yt-dlp/ejs.
- Android NDK r28c, API 26, ARM64. Alinhamento de segmentos de 16 KiB. As dependências dos executáveis são somente bibliotecas do sistema Android; os codecs acima são ligados estaticamente.

Os arquivos compactados originais, incluindo licenças, são distribuídos no pacote `Fontes-nativos-Android` da mesma release. Os fontes não foram modificados. A configuração e os passos para gerar o REPL do QuickJS estão em `build-native.sh`; `arm64-config.h`, `arm64-config_components.h` e `arm64-ffmpeg-config.log` registram a construção realizada. `NATIVE_ARTIFACTS.json` registra os executáveis e suas dependências. `SHA256SUMS.txt` permite ao Gradle recusar binários diferentes dos preparados.

## Reconstruir no Windows

Requer Python 3.11 atualizado (3.11.8 ou posterior para extração segura), internet na preparação do ambiente e aproximadamente 8 GB livres. O script baixa e confere os fontes e as ferramentas por SHA-256, prepara um MSYS2 portátil e não instala WSL nem altera o SDK do sistema.

Na pasta `Android`:

```powershell
$work=Join-Path $env:LOCALAPPDATA 'OndaNativeBuild'
python .\nativebuild\bootstrap.py --work $work --abi arm64-v8a --install-to .\native-tools
.\gradlew.bat -Ponda.abis=arm64-v8a :app:assembleDebug
```

O primeiro comando copia os três executáveis e atualiza os hashes desta construção. Para o emulador x86_64, repita com `--abi x86_64` e compile com `-Ponda.abis=x86_64`. Antes de distribuir resultados novos, rode os testes Android. Se alterar fontes, versão ou opções de compilação, use outra pasta de trabalho vazia para não reutilizar os marcadores de uma construção anterior.

Caminhos de instalação e ferramentas auxiliares podem alterar os bytes finais. Os hashes registrados identificam esta construção; não são uma promessa de resultados byte a byte idênticos em qualquer computador. Os fontes e a receita utilizados estão fixados e disponíveis.

O pacote Fontes-nativos-Android também permite obter os fontes sem preparar compiladores:

```powershell
python .\bootstrap.py --work .\fontes-extraidos --sources-only
```

`bootstrap.py` aproveita os arquivos em `sources/` ao lado dele quando presentes. Os compiladores não são redistribuídos no APK. As licenças estão em `licenses/` e no aplicativo, em Menu → Licenças e fontes. Os componentes Python/Android e seus avisos estão nos outros pacotes de fontes e em THIRD_PARTY_NOTICES_ANDROID.md.

Chromaprint 1.6.2 usa a biblioteca Kiss FFT incluída nos fontes. `build_chromaprint.py --work <pasta>` gera `libchromaprint.so` para ARM64 e x86_64 com NDK r28c, CMake e Ninja do MSYS2, ligação C++ estática e alinhamento de 16 KiB. A pasta preparada pelo bootstrap contém os fontes em `src/`, arquivos verificados em `sources/`, NDK em `android-ndk-r28c` e CMake/Ninja em `msys64/ucrt64/bin`. O formato anterior com `tooling/` também é aceito. O hash dos fontes está em `source-lock.json`; os hashes resultantes devem ser registrados em `SHA256SUMS.txt` antes do empacotamento.

## Compilar os APKs no ambiente local

O aplicativo usa Python 3.13 no Android. O Python 3.15 do portátil é independente e não deve ser passado como `onda.buildPython`.

Na pasta `E:\Projetos\Onda\Android`, depois de preparar as ferramentas nativas:

```powershell
$env:JAVA_HOME = 'E:\Projetos\Onda-Local\Compilacao\jdk\jdk-25.0.5+8'
$env:ANDROID_HOME = 'E:\Projetos\Onda-Local\Compilacao\android-sdk'
$env:ANDROID_USER_HOME = 'E:\Projetos\Onda-Local\Compilacao\android-user'
$env:GRADLE_USER_HOME = 'E:\Projetos\Onda-Local\Compilacao\gradle-cache'
$BuildPython = 'E:\Projetos\Onda-Local\Compilacao\python-3.13.17\python.exe'
$ProjectCache = 'E:\Projetos\Onda-Local\Compilacao\gradle-project-9'
.\gradlew.bat :app:assembleRelease :app:testDebugUnitTest --project-cache-dir "$ProjectCache" '-Ponda.abis=arm64-v8a' "-Ponda.buildPython=$BuildPython"
.\gradlew.bat :app:assembleRelease --project-cache-dir "$ProjectCache" '-Ponda.abis=x86_64' "-Ponda.buildPython=$BuildPython"
```

A compilação usa JDK 25, Gradle 9.7, Android Gradle Plugin 9.5.1 e Kotlin 2.4.21. Os comandos acima geram APKs sem assinatura; a assinatura de produção é feita separadamente pelo processo local de empacotamento.
