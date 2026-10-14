# ONDA 1.0.0

Primeira versão oficial para Windows 10/11 x64 e Android 8 ou superior, ARM64.

## Novidades desde a última pré-release

- Histórico completo em cards ou compacto, com capas e informações da música, seleção individual e ajuste discreto do tamanho dos cards. No PC, Ctrl + roda do mouse também ajusta o tamanho.
- Preto puro com opção de bordas e separações. No Android, popups e barra de navegação acompanham o tema.
- Ícone interno acompanha a cor de destaque; no PC, os ícones das janelas também acompanham a cor.
- PC: rolagem da página inteira, edição de metadados na própria aba e abertura direta pelo histórico, ajustes de capa e destaque de álbum/artista.
- PC: até 15 downloads simultâneos, com aviso de maior consumo; Backspace também remove itens selecionados nas listas que oferecem remoção.
- Android: correções na importação de imagens locais e permissões, seleção automática de versões e abertura de metadados pelo histórico.
- Android: opção de escolher manualmente a versão quando a seleção automática não encontra uma correspondência suficientemente compatível.
- Correções de acesso às publicações Kwai, consultando páginas desktop e mobile e evitando baixar vídeos recomendados no lugar do solicitado.
- Vídeos: correção da escolha de resolução/FPS no Kwai e demais plataformas; consideração do lado menor em vídeos verticais, preferência por qualidades nativas compatíveis e redução quando a fonte excede os limites escolhidos.
- Avisos com duração padrão de três segundos em novas instalações e melhor distribuição dos botões da pesquisa Android.
- Cache limitado de capas/metadados, menos releituras no histórico, substituição de arquivos Android com cópia de segurança e limpeza de código sem uso.

Mantém pesquisa de músicas, FLAC direto do Monochrome quando disponível, downloads de áudio/vídeo/imagens, álbuns e playlists, edição de metadados/capas/letras, normalização, Slowed/Sped Up/Reverb e personalização.

## Qual arquivo baixar?

- `Onda-1.0.0-Setup-Windows-x64.exe`: instalação por usuário, com atalhos e desinstalador.
- `Onda-1.0.0-Portable-Windows-x64.zip`: extraia tudo e abra Onda.exe; Python e Node incluídos. FFmpeg preparado no primeiro uso com internet.
- `ONDA-Android-1.0.0-arm64-v8a.apk`: Android ARM64, assinado com a mesma chave de produção; versionCode 16.
- `Onda-1.0.0-Fontes.zip`: código-fonte e scripts de construção.
- `Onda-1.0.0-Fontes-nativos-Android.zip`: fontes e receitas das ferramentas nativas Android.
- `Onda-1.0.0-Fontes-de-terceiros.zip`: fontes e avisos das dependências Python.
- `SHA256SUMS.txt` e `MANIFEST.json`: integridade e informações dos pacotes.

## Validação e distribuição

Revisão final com 346 testes PC aprovados, cinco testes unitários Android e 59 casos instrumentados distintos aprovados na rodada principal. As correções finais tiveram testes adicionais de metadados, seleção de versões, popups e barra de navegação. O usuário confirmou funcionamento dos fluxos no celular e das últimas correções antes da preparação oficial. Consulte `VALIDACAO.md` para limites e resultados específicos.

Os executáveis Windows não possuem assinatura Authenticode. O APK Android usa a chave de produção ONDA. Atualize por cima da versão anterior assinada com essa mesma chave para preservar os dados.

O acesso às plataformas e a disponibilidade de FLAC dependem de terceiros e podem exigir autenticação. MP3/M4A de músicas de catálogo usam uma versão correspondente no YouTube. Use conteúdo que você tenha autorização para baixar.
