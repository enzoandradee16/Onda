# Validação de desenvolvimento — 12/10/2026

ONDA Android 1.0.0-alpha.2. Emulador Pixel 7, Android 16/API 36, x86_64. APK universal com ARM64 e x86_64; ARM64 ainda não foi executado em aparelho físico.

## Alterações da alpha.2

- Navegação por menu lateral, ícone real ao lado do nome, cabeçalho compacto e status dispensável.
- Títulos, descrições e controles principais alinhados com o PC; presets iguais aos do PC, nome calculado pelos sliders e estado preservado entre áreas.
- Seletores de formato e qualidade lado a lado; prévia original e com efeitos; botão Ouvir/Parar vinculado ao estado do player.
- Inclusão de músicas de coleção em transação única no SQLite, fora da thread principal.
- Janela de sessão própria do YouTube com exportação privada de cookies; uso da sessão nas operações do yt-dlp e mensagem específica para exigência de verificação.

## Verificações concluídas

- Compilação `assembleDebug` e compilação dos testes Android concluídas.
- Testes instrumentados locais da versão anterior concluídos sem falhas: credenciais/fila; ferramentas/downloads/efeitos/imagens; navegação; serviço com publicação; confirmação de versão/revisão de metadados.
- FFmpeg 7.1.1, FFprobe e QuickJS executados no próprio Android; yt-dlp 2026.08.19 importado.
- Vídeo MP4 sintético criado e baixado por HTTP local; áudio extraído em MP3; foto JPEG baixada.
- Post misto sintético: foto e MP3 extraído do vídeo selecionados e exportados. O reconhecimento da plataforma foi substituído por uma fixture nesse teste; isso não comprova acesso aos sites reais.
- Efeito em MP3 com título modificado, artista/álbum preservados e capa preservada byte a byte. Prévia gerada a partir de outro ponto do áudio.
- Conversões PNG, WebP e SVG; importação CSV/TXT/M3U e exportação M3U; validação da seleção de mídia.
- Gravação e leitura de arquivo em Downloads/ONDA via MediaStore; opção de pular arquivo existente.
- Serviço em primeiro plano baixou e publicou arquivo, atualizando a fila para Concluído.
- Navegação pelas seis áreas e categorias de configuração; botões de confirmação de versão e edição conferidos.
- Assinatura APK v2 verificada por `apksigner`; pacote `br.com.onda.mobile`, minSdk 26, targetSdk 35.
- Inspeção visual da tela de pesquisa. O emulador apresentou um aviso de processo do sistema durante a sessão; não foi registrado ANR do aplicativo nos testes.

## Verificações da alpha.2

A compilação inicial dos ajustes passou com seis testes locais, incluindo troca de preset, preservação entre páginas e transição Ouvir → Parar. A execução final passou com sete testes locais, acrescentando o teste de salvar a sessão própria do YouTube. Capturas de tela estão em `validation/captures/` (ignoradas pelo Git).

O teste real do YouTube foi repetido e ainda recebeu exigência de verificação. A mensagem orienta a sessão, mas a resolução do bloqueio com uma conta real não foi comprovada. O teste da sessão usa cookies fictícios e comprova o fluxo de gravação, não a autorização pelo YouTube.

## Verificações online

- Busca “Stardust Music Sounds Better With You”: Apple/iTunes retornou 23 resultados e Deezer 16.
- Link Spotify `6xXEw4y39shgIp6pacKQFH`, sem Client ID/Secret: resolvido como “Make Luv”, com metadados complementados pelo Deezer.
- YouTube: o vídeo de fixture antigo estava indisponível. Outro vídeo público retornou “Sign in to confirm you’re not a bot”. A validação real do YouTube ficou bloqueada pela exigência de sessão nessa conexão. Não foi marcada como sucesso.
- O teste opcional de YouTube permanece disponível com `-e liveYoutube true`. Os testes de catálogos e Spotify usam `-e liveNetwork true` e `-e liveSpotify true`; ficam dispensados em execução local sem esses argumentos.

## Pendências para uma release Android

Testar aparelho ARM64 real, autenticação Spotify com conta, cookies próprios, plataformas sociais reais, playlists grandes, segundo plano prolongado, retomada após interrupções e pasta escolhida por SAF. Concluir assinatura definitiva e preparação das licenças/fontes dos componentes nativos antes de publicação pública.

O APK tem assinatura de desenvolvimento. O hash do pacote entregue fica ao lado dele em `APK/SHA256SUMS.txt`. Esta versão não substitui os arquivos Windows nem altera a release Windows existente.

## Alpha.3 — Histórico e revisão de paridade

Histórico inclui Usar em efeitos para áudio/vídeo, com leitura de URI de MediaStore/SAF fora da thread principal e abertura automática da área Efeitos. O original não é alterado. Cartões agora preenchem a largura da tela. Adicionado teste com MP3 sintético publicado em Downloads: clicar no histórico, importar, navegar e comparar os bytes do áudio. Fotos não oferecem o atalho.

A comparação por código está em `PARIDADE-PC-ANDROID.md`, incluindo recursos ausentes, adaptações de plataforma e funções existentes ainda sem validação real. Essa revisão não afirma equivalência integral com o PC.

## Alpha.4 — Pesquisa, duração e avisos

- Efeitos e player exibem posição/duração em minutos:segundos (183s → 3:03; 429s → 7:09). Resultados de pesquisa mostram duração quando informada pelo catálogo.
- Fila da pesquisa identifica itens com `_origin=search` no SQLite, acompanha os estados/progresso do serviço e permite iniciar somente esses pendentes, tentar novamente e limpar. A fila geral continua refletindo os mesmos trabalhos; não são criados downloads duplicados. Itens antigos sem origem permanecem somente na lista geral.
- Atalho Spotify Developers abre o dashboard oficial no navegador do Android. Client ID vazio é validado antes de iniciar OAuth; Client Secret continua opcional no fluxo PKCE.
- Avisos/resultados de operações de configurações aparecem em AlertDialog acima das janelas. Falhas de importar capa/cookies e de prévia de versão usam a mesma camada. Progresso de ferramentas/conexão fica visível no painel enquanto a operação está em andamento; status de ações da tela principal permanece no topo.
- Novo teste verifica duração, inclusão na fila da pesquisa, transições Baixando/Concluído, atalho visível e validação Spotify acima do painel, com retorno à configuração após fechar o aviso. Estados da fila são simulados nesse teste; o teste do serviço continua cobrindo um download HTTP local real.

Alpha.6: botão Remover por música na fila da pesquisa. Remove somente o registro selecionado, preservando arquivos baixados; fica desabilitado para o item ativo. Compilação concluída e teste instrumentado removeOnlyOneSearchQueueItem passou, conferindo persistência, preservação do outro item e proteção do item ativo.

## Alpha.7 — 2026-10-12

Build assembleDebug e assembleDebugAndroidTest: sucesso. Seis testes de instrumentação passaram: remoção individual do histórico preservando bytes do arquivo e outro registro, deslize de categorias nas duas direções, regeneração automática da prévia ao alterar sliders e bloqueio após Parar, navegação geral/configurações, fila de pesquisa/avisos acima do painel e Usar em efeitos no histórico. Após separar a reprodução de prévias normais da prévia de efeitos, o teste dos sliders passou novamente no APK final. Áudio sintético local de 40 segundos; emulador x86_64 API 36. APK alpha.7 verificado com apksigner. Não representa validação em aparelho ARM64 real ou da autorização real do Spotify no navegador.

## Alpha.8 — 2026-10-12

assembleDebug e assembleDebugAndroidTest: sucesso. NavigationTest completo (12 testes) e MobileRuntimeTest.spotifyAuthorizationReturn passaram: OK (13 tests), emulador x86_64 API 36. Inclui migração Menta/Sistema, navegação/categorias, avisos, escolhas, fila/histórico e efeitos automáticos. Auditoria estática encontrou 220 textos literais do PC no Android e verificou nomes e 32 tons das 16 cores, além da igualdade dos módulos atualizados entre fonte, portátil e motor compartilhado. Python PC: 20 testes declarados, 15 executados com sucesso e 5 integrações Tk ignoradas. Inno Setup 6.7.3: compilação do instalador concluída; não foi feita instalação no PC do usuário. APK validado com apksigner. Autorização Spotify real no navegador e aparelho ARM64 continuam fora desta validação.

## Alpha.9 — 2026-10-12

Escolha de fontes em Aparência: assembleDebug e assembleDebugAndroidTest concluídos. PC: 9 testes passaram, incluindo integrações Tk ativadas, fonte em estilos ttk, texto de canvas, widgets e novas janelas, preservação de tamanho/negrito/itálico, persistência ao reabrir e restauração seletiva. Android: 3 testes passaram no emulador x86_64 API 36, incluindo comparação de pixels de um título fora da prévia para comprovar aplicação global da família, persistência, retorno ao padrão, migração de aparência e deslize entre categorias. Fontes nativas; nenhuma dependência ou download de fonte novo. Instalador Inno Setup recompilado com o novo módulo interface_fonts.py; pacote portátil sincronizado e APK verificado com apksigner. Aparelho ARM64 real não testado nesta rodada.

## Alpha.10 — 2026-10-12

Build assembleDebug e assembleDebugAndroidTest concluídos. PC: dois testes Tk passaram, cobrindo Enter/KP_Enter na pesquisa, normalização da consulta, prevenção de cancelamento ao pressionar novamente e Enter na consulta avulsa de metadados. O campo de links mantém sua entrada multilinha. Android: teste de instrumentação passou no emulador x86_64 API 36, com consulta de catálogo simulada em módulo de debug: Enter físico produziu um resultado e uma consulta; ação IME Pesquisar produziu o segundo resultado e somente mais uma consulta; Enter no campo LINKS criou a quebra de linha sem consultar o catálogo. Todos os demais campos Android configurados como singleLine. APK verificado com apksigner, portátil sincronizado e instalador recompilado. Sem teste em aparelho ARM64 real nesta rodada.

## Android alpha.11 — ícone arredondado
- Ícones do cabeçalho e menu lateral com cantos arredondados em 25%.
- assembleDebug concluído com sucesso; assinatura do APK verificada com apksigner.
- Alteração visual simples, sem novo teste instrumental.


## Android alpha.12 — conectar Spotify na pesquisa
- Botão Conectar Spotify visível somente no catálogo Spotify; usa o mesmo fluxo OAuth das configurações e orienta onde preencher o Client ID.
- assembleDebug e assembleDebugAndroidTest concluídos; assinatura verificada com apksigner.
- Teste instrumental spotifyConnectAppearsOnlyForSpotifyAndValidatesClientId: OK (1 test), 9.721s, emulador API 36.
- APK alpha.11 removido; mantido somente alpha.12.
