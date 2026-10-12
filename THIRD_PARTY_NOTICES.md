# Componentes de terceiros

Copyright (c) 2026 Enzo Andrade para o código próprio do ONDA, licenciado sob GPL-2.0-only. Dependências e executáveis externos não são relicenciados por este aviso; conservam suas licenças e titulares originais.

| Componente | Licença / localização no pacote |
| --- | --- |
| gallery-dl | GPL-2.0-only; `_runtime/python/Lib/site-packages/gallery_dl-*.dist-info/licenses/LICENSE` |
| Mutagen | GPL-2.0-or-later; licença na pasta `.dist-info/licenses` correspondente |
| yt-dlp e dependências | Licenças individuais nas pastas `.dist-info`; consulte os arquivos originais |
| CPython, Tcl/Tk e componentes | `_runtime/python/LICENSE.txt` e avisos dentro do runtime |
| FFmpeg / ffprobe / ffplay, build Gyan essentials 9.0.2 | Build GPLv3; `_runtime/ffmpeg/LICENSE.txt`, `README.txt` e documentação. Executáveis externos ao código Python do ONDA |
| Node.js | MIT e avisos dos componentes incorporados, em `_runtime/node/LICENSE.txt` |
| Requests, Pillow, curl-cffi e demais pacotes | Licenças individuais nas respectivas pastas `.dist-info` |

O inventário das dependências Python está em `docs/dependencias.json`. Os pacotes preservam os arquivos de licença existentes no runtime. Consulte os originais para termos completos; esta tabela não substitui as licenças.

Referências de origem: https://github.com/mikf/gallery-dl, https://github.com/quodlibet/mutagen, https://github.com/yt-dlp/yt-dlp, https://www.python.org/, https://nodejs.org/, https://www.gyan.dev/ffmpeg/builds/ e https://ffmpeg.org/legal.html.

O pacote de fontes da beta reúne fontes principais e a proveniência da construção. Antes de redistribuir os binários, verifique também os fontes correspondentes das bibliotecas vinculadas pelo build externo do FFmpeg; não considere este inventário uma certificação da completude dessas fontes.
