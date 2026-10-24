# Componentes do ONDA Android

O código próprio mantém a licença GPL-2.0-only do repositório. Bibliotecas mantêm suas licenças originais. Versões e avisos usados nesta release são registrados em `nativebuild/`; a lista não substitui aconselhamento jurídico.

| Componente | Origem | Licença de referência |
|---|---|---|
| Kotlin | https://github.com/JetBrains/kotlin | Apache-2.0 |
| AndroidX / Compose / Media3 | https://android.googlesource.com/platform/frameworks/support/ | Apache-2.0 |
| Chaquopy 17.0.0 | https://github.com/chaquo/chaquopy | MIT; Python e módulos nativos com licenças próprias |
| Python 3.11 | https://www.python.org/ | PSF e avisos de componentes |
| yt-dlp 2026.10.21 | https://github.com/yt-dlp/yt-dlp | Unlicense para código próprio; consultar componentes |
| yt-dlp-ejs 0.8.0 | https://github.com/yt-dlp/ejs | Consultar LICENSE do pacote |
| gallery-dl 1.32.17 | https://github.com/mikf/gallery-dl | GPL-2.0-only |
| Mutagen 1.47.0 | https://github.com/quodlibet/mutagen | GPL-2.0-or-later |
| Requests 2.32.5 | https://github.com/psf/requests | Apache-2.0 |
| Pillow 11.0.0 | https://github.com/python-pillow/Pillow | HPND e avisos das bibliotecas nativas |
| Coil 2.7.0 | https://github.com/coil-kt/coil | Apache-2.0 |
| kotlinx.coroutines | https://github.com/Kotlin/kotlinx.coroutines | Apache-2.0 |
| FFmpeg / FFprobe 7.1.3 | https://ffmpeg.org/ | GPL-3.0-or-later na configuração utilizada |
| QuickJS 2025-09-13 | https://bellard.org/quickjs/ | MIT |
| LAME 3.100 | https://lame.sourceforge.io/ | LGPL-2.0-or-later |
| x264 b35605ace3ddf7c1a5d67a2eb553f034aef41d55 | https://code.videolan.org/videolan/x264 | GPL-2.0-or-later |
| WebP 1.6.0 | https://chromium.googlesource.com/webm/libwebp | BSD e avisos PATENTS |
| Opus 1.5.2 / Ogg 1.3.6 / Vorbis 1.3.7 | https://xiph.org/ | BSD e avisos dos componentes |
| Mbed TLS 3.6.4 | https://github.com/Mbed-TLS/mbedtls | Apache-2.0 ou GPL-2.0-or-later |
| FreeType 2.9.1 / libjpeg-turbo 1.5.3 | dependências do Pillow para Chaquopy | FTL e avisos libjpeg-turbo |
| OpenSSL 3.0.18 / SQLite | runtime Python Chaquopy | Apache-2.0 / domínio público e avisos próprios |

FFmpeg, FFprobe e QuickJS são executáveis separados, chamados como processos. Eles foram compilados pelo ONDA a partir dos arquivos originais registrados em `nativebuild/source-lock.json`, sem alterações nos fontes. A configuração do FFmpeg habilita GPL/version3; sua licença resultante é GPL-3.0-or-later. Os codecs são ligados estaticamente; somente bibliotecas do sistema Android são dependências dinâmicas desses três executáveis.

O pacote `Fontes-nativos-Android` da mesma release contém os fontes originais completos dos componentes desses executáveis, receitas, configurações e licenças. `nativebuild/README.md` explica a reconstrução. Os binários anteriores youtubedl-android e os arquivos ZIP de suporte Termux deixaram de ser usados.

`nativebuild/RUNTIME_DEPENDENCIES.json` lista as 98 bibliotecas de execução resolvidas pelo Gradle, com versões, hashes e informações de licença do POM. Os avisos embutidos nos artefatos e nas dependências Python foram preservados em `nativebuild/licenses/` e no APK, acessíveis por Menu → Licenças e fontes. Python 3.11.14, Chaquopy 17.0.0, Pillow e bibliotecas auxiliares mantêm suas licenças originais; não são parte da reconstrução FFmpeg.

A assinatura de produção foi verificada. A validação atual da versão 1.2.1 usa BlueStacks com Android 11/API 30, x86_64. Os APKs ARM64 são compilados e verificados; a validação física ARM64 permanece pendente.
