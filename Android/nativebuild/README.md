# Ferramentas nativas Android construídas pelo ONDA

A alpha.2 substitui as ferramentas do AAR youtubedl-android por executáveis próprios compilados dos arquivos de `source-lock.json`. Não incorpora libffmpeg.zip.so, libpython.zip.so nem libonda-support.zip.so. O Python utilizado pelo aplicativo continua sendo o do Chaquopy.

## Componentes e construção

- FFmpeg / FFprobe 7.1.3: configuração resultante GPL-3.0-or-later.
- LAME 3.100 (MP3), x264 b35605ace3ddf7c1a5d67a2eb553f034aef41d55 (H.264), WebP 1.6.0, Opus 1.5.2, Ogg 1.3.6 e Vorbis 1.3.7.
- Mbed TLS 3.6.4 para HTTPS. AAC, FLAC, WAV, filtros e demais codecs internos são fornecidos pelo FFmpeg.
- QuickJS 2025-09-13 (arquivo oficial de revisão `-2`), MIT, para yt-dlp/ejs.
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
