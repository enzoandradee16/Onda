# Componentes do ONDA Android

O código próprio mantém a licença GPL-2.0-only do repositório. Bibliotecas mantêm suas licenças originais. Esta lista é um inventário de desenvolvimento, não uma declaração de auditoria jurídica concluída.

| Componente | Origem | Licença de referência |
|---|---|---|
| Kotlin | https://github.com/JetBrains/kotlin | Apache-2.0 |
| AndroidX / Compose / Media3 | https://android.googlesource.com/platform/frameworks/support/ | Apache-2.0 |
| Chaquopy 17.0.0 | https://github.com/chaquo/chaquopy | MIT; Python e módulos nativos com licenças próprias |
| Python 3.11 | https://www.python.org/ | PSF e avisos de componentes |
| yt-dlp 2026.08.19 | https://github.com/yt-dlp/yt-dlp | Unlicense para código próprio; consultar componentes |
| yt-dlp-ejs 0.8.0 | https://github.com/yt-dlp/ejs | Consultar LICENSE do pacote |
| gallery-dl 1.32.16 | https://github.com/mikf/gallery-dl | GPL-2.0-only |
| Mutagen 1.47.0 | https://github.com/quodlibet/mutagen | GPL-2.0-or-later |
| Requests 2.32.5 | https://github.com/psf/requests | Apache-2.0 |
| Pillow 11.0.0 | https://github.com/python-pillow/Pillow | HPND e avisos das bibliotecas nativas |
| Coil 2.7.0 | https://github.com/coil-kt/coil | Apache-2.0 |
| kotlinx.coroutines | https://github.com/Kotlin/kotlinx.coroutines | Apache-2.0 |
| FFmpeg e QuickJS Android | https://github.com/yausername/youtubedl-android | Wrapper Apache-2.0; binários e dependências com licenças próprias |

Os artefatos `io.github.junkfood02.youtubedl-android:{ffmpeg,library}:0.18.1` fornecem FFmpeg, FFprobe, QuickJS e bibliotecas de suporte. A versão Android, ao contrário do pacote Windows atual, incorpora componentes nativos ao APK para execução compatível com as restrições do Android. O script seleciona somente ferramentas/bibliotecas necessárias e não usa o runtime Python do wrapper.

Antes da publicação pública, registrar versões/configuração reais do FFmpeg (saída de `-version`), revisar sua licença resultante e disponibilizar os fontes correspondentes das bibliotecas incorporadas e scripts necessários. Apenas apontar para o repositório do wrapper não substitui essa preparação. Não publicar o APK como release final enquanto essa revisão e a assinatura definitiva estiverem pendentes.
