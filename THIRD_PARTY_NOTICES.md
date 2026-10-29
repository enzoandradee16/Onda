# Componentes de terceiros

Copyright (c) 2026 Enzo Andrade para o código próprio do ONDA, licenciado sob GPL-2.0-only. Dependências e executáveis externos não são relicenciados por este aviso; conservam suas licenças e titulares originais.

| Componente | Licença / localização no pacote |
| --- | --- |
| Inter | SIL Open Font License 1.1; `Onda/assets/fonts/OFL-Inter.txt`; no Android, `assets/licenses/OFL-Inter.txt` |
| gallery-dl | GPL-2.0-only; `_runtime/python/Lib/site-packages/gallery_dl-*.dist-info/licenses/LICENSE` |
| Mutagen | GPL-2.0-or-later; licença na pasta `.dist-info/licenses` correspondente |
| yt-dlp e dependências | Licenças individuais nas pastas `.dist-info`; consulte os arquivos originais |
| Qt, PySide6 e Shiboken (portátil Qt) | Licenças e avisos originais preservados em `_runtime/qt/pyside6_essentials-*.dist-info/licenses` e `_runtime/qt/shiboken6-*.dist-info/licenses` |
| CPython, Tcl/Tk e componentes | `_runtime/python/LICENSE.txt` e avisos dentro do runtime |
| FFmpeg / ffprobe / ffplay | Não incluídos nos pacotes do ONDA. Obtidos diretamente de gyan.dev pelo usuário na primeira preparação. Licença GPLv3, README e origem preservados no cache local |
| Node.js | MIT e avisos dos componentes incorporados, em `_runtime/node/LICENSE.txt` |
| Requests, Pillow, curl-cffi e demais pacotes | Licenças individuais nas respectivas pastas `.dist-info` |

O inventário das dependências Python está em `docs/dependencias.json`. Os pacotes preservam os arquivos de licença existentes no runtime. Consulte os originais para termos completos; esta tabela não substitui as licenças.

Referências de origem: https://github.com/mikf/gallery-dl, https://github.com/quodlibet/mutagen, https://github.com/yt-dlp/yt-dlp, https://www.python.org/, https://nodejs.org/, https://www.gyan.dev/ffmpeg/builds/ e https://ffmpeg.org/legal.html.

O pacote de fontes de terceiros reúne gallery-dl, Mutagen e yt-dlp, correspondentes às versões Python incluídas. O FFmpeg é uma ferramenta externa obtida diretamente do seu distribuidor, não acompanha os arquivos publicados do ONDA. Não adicione os executáveis do cache local a futuros ZIPs ou instaladores.

Origem fixa do download: https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip. SHA-256 esperado: `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`. Licença e fontes do build são responsabilidade da distribuição de origem; os respectivos avisos são conservados no download local.
