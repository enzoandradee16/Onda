# Validação da release ONDA 1.2.1 — 24/10/2026

Android: 1.2.1/código 28. Windows: 1.2.1, executáveis 1.2.1.0. Release preparada em pasta Release/1.2.1 e como rascunho no GitHub, sem publicação automática.

## Verificação final

- BlueStacks 5 aberto, Android 11/API 30/x86_64. Aplicativo de testes isolado br.com.onda.mobile.uitest.
- 91 testes instrumentados aprovados em 35 suítes, cobrindo reprodução, notificações, filas, letras, armazenamento, temas, acessibilidade, conversão, limites de vídeo, edição/sobrescrita de metadados, importação de imagens, atualizações e licenças.
- Um download TikTok real adicional em MP4 passou com o código final, incluindo publicação e leitura pelos provedores Android. A primeira auditoria também validou o link fornecido em automático, MP3, M4A, áudio original e FLAC, fotos TikTok, Reel e carrossel Instagram.
- Corrida de cancelamento reproduzida antes da correção no teste Python e validada depois também com FFmpeg real no Android. O processo recém-criado é encerrado e coletado, inclusive quando o cancelamento chega antes do registro.
- Testes de seleção recente, Parar durante preparação, recuperação de cache, nova tentativa de metadados, fila de 100 músicas e retorno a faixas antigas depois de liberar modelos aprovados.
- Testes de letras incluem tempos repetidos, documentos fora de ordem, sincronização por palavra e um documento de 20.000 versos. 76 testes JVM aprovados, incluindo quatro testes locais adicionais incorporados pelo ambiente Testes.
- 102 testes finais do PC, versão, extratores e adaptador Android aprovados, sem testes ignorados. Os 34 testes Tkinter também passam, ativados por processo com perfis separados e ONDA_UI_TESTS=1 apenas no ambiente local de teste.

## Pacotes e fontes

APKs ARM64 e x86_64 compilados separadamente, assinados com a chave original e verificados com alinhamento de 16 KB. Certificado SHA-256: 0edd6f5de88fc24b7a45212b51ba7d428030302459e9ed8d619d7dbc29fb81b3.

Portátil e instalador Windows usam o runtime já distribuído; launcher, instalador e desinstalador passam por autotestes. FFmpeg Windows não é incluído nos pacotes.

O pacote de fontes de terceiros mantém as versões usadas pelo Windows e acrescenta gallery-dl 1.32.17, yt-dlp 2026.10.21 e certifi 2026.10.23 do Android. Os fontes foram obtidos do PyPI, conferidos pelos hashes de distribuição e registrados em ORIGENS.json. Fontes e receitas dos executáveis nativos Android não mudaram; o respectivo arquivo foi verificado contra a release anterior.

SOURCE_MANIFEST.json identifica o commit e os hashes de cada fonte do aplicativo. MANIFEST.json e SHA256SUMS.txt registram os pacotes finais e suas verificações. A pasta local Testes, seus perfis e caches, credenciais, cookies e chaves privadas não entram nos arquivos de fontes ou nos binários distribuídos.

## Limites

Não houve validação direta em aparelho ARM64 físico. O teste em BlueStacks x86_64 não substitui essa confirmação. As regressões usam principalmente arquivos sintéticos e servidores locais; os testes de rede documentados não abrangem todas as publicações, contas e plataformas disponíveis.

Relatórios detalhados e logs locais estão em Testes/auditoria-release-1.2.1; essa pasta permanece excluída do Git neste checkout.
