# Funções e validação Android

**Atualização 1.1.0:** idiomas PT/ES/EN, cards e controles da fila/Histórico e reinício pendente PC. Consulte a [validação 1.1.0](../docs/VALIDACAO-1.1.0.md). O levantamento abaixo é histórico e mantém o contexto da versão em que foi escrito.

Versão: 1.0.0-alpha.1. Este documento distingue implementação de comprovação em aparelho real. A versão Windows permanece independente.

| Área | Implementação Android | Validação atual |
|---|---|---|
| Links | Baixar agora, adicionar à fila, áudio/vídeo, qualidade, resolução, FPS, estimativa de tamanho | Downloads HTTP de foto, MP4 e extração MP3 no emulador |
| Fila | Persistência SQLite, selecionar/remover/limpar, tentar novamente, progresso, cancelar, serviço com notificação | Persistência, serviço de download e publicação verificadas; falta ensaio longo com tela apagada em aparelho real |
| Músicas | Pesquisa Deezer/Apple/Spotify, metadados, capa, escolha de catálogo/versão, correspondência automática, edição antes de baixar | Deezer, Apple/iTunes e link Spotify sem API testados online; confirmação/revisão testadas; login de conta ainda pendente |
| Redes sociais | TikTok, Instagram, Twitter/X e Kwai pelo motor compartilhado; fotos, vídeos e seleção em posts mistos; áudio por vídeo | Foto e extração de áudio de vídeo no mesmo post validadas com fixture; acessos reais sujeitos a cookies e bloqueios da plataforma |
| Playlists e álbuns | Importação por link, CSV/Exportify, TXT/M3U; busca, seleção, conferir correspondências, baixar agora/fila; opções próprias; exportar TXT/M3U; janela somente lista | Importação/exportação testadas com dados sintéticos; playlists grandes e OAuth ainda precisam teste real |
| Organização | Artista - Música; pastas de playlist original e Artista - Álbum; organização por artista/álbum; duplicados | Publicação e política de pular duplicados no MediaStore verificadas no emulador |
| Imagens | Link/arquivo, Original/JPG/PNG/WebP/SVG, dimensões, proporção, prévia | PNG/WebP/SVG e download de JPEG testados no Android; SVG de foto incorpora raster |
| Histórico | Pesquisa, abrir, compartilhar, usar em efeitos, limpar sem apagar os arquivos | Implementado; abrir/compartilhar depende dos aplicativos instalados |
| Efeitos | Slowed, Sped Up, Reverb independentes; presets; manter tom; início/duração da prévia; reprodução com busca; exportação e títulos condicionais | Renderização, prévia e preservação de artista/álbum/capa testadas com MP3 sintético |
| Aparência | Tema claro/escuro/sistema, 16 cores, ordem das abas | Navegação automatizada e inspeção visual em emulador |
| Configuração | Primeira entrada dispensável; lembrar opções; categorias; restauração geral/seletiva; duração de prévias; continuar ao trocar de aba | Implementado; credenciais cifradas e fila sem Client Secret testadas |
| Ferramentas | Python e ferramentas nativas internas; verificar ferramentas; atualização de yt-dlp com SHA-256 | FFmpeg, FFprobe e QuickJS executados no emulador |
| Integração Android | Compartilhar link para ONDA, seletor de arquivos/pasta, MediaStore, notificações, uma Activity reaproveitada | MediaStore e abertura do app testados; demais fluxos requerem aparelho real |

## Diferenças da plataforma

- Não há BAT, EXE, wizard Windows ou pasta portátil: instala-se o APK e o Android gerencia a desinstalação. A exclusão de dados fica nos controles do sistema.
- Android 10+ exporta para Downloads/ONDA por padrão. Escolher outra pasta usa o seletor do sistema. Android 8/9 precisa de pasta escolhida para manter os arquivos fora dos dados do app.
- Downloads em segundo plano usam serviço e notificação. Fabricantes, economia de bateria e limites do Android podem interromper trabalhos; a fila é preservada para tentar novamente.
- O app não transforma uma fonte com perdas em áudio lossless original de streaming. FLAC conserva a qualidade da fonte recebida.
- Cookies são importados por arquivo; não há extração automática dos cookies de outros apps. A biblioteca de impersonação curl_cffi do PC não está incorporada neste APK.
- APIs, plataformas e restrições de login continuam valendo. Não há promessa de acesso a qualquer link ou de contornar bloqueios.

## Roteiro no celular

1. Instalar o APK, abrir, fechar a configuração inicial e abrir novamente: o aviso inicial deve aparecer uma única vez.
2. Permitir notificações e escolher uma pasta em Configurações → Downloads.
3. Testar um link autorizado de vídeo em MP4 e o mesmo link em MP3; conferir o arquivo na pasta e no histórico.
4. Adicionar três itens à fila, remover um, fechar/abrir o app e conferir os pendentes. Testar cancelar e tentar novamente.
5. Pesquisar música, ouvir a prévia e baixar com capa. Conferir título, artista, álbum e arquivo Artista - Música.
6. Testar um post público somente com fotos, somente com vídeo e um misto; na escolha do misto, selecionar uma foto e áudio de um vídeo.
7. Carregar playlist/álbum, filtrar uma música, testar formatos próprios, exportar TXT/M3U e importar CSV. Verificar subpasta da coleção.
8. Em Efeitos, selecionar MP3 com tags/capa, testar velocidade 90%, 120%, reverb isolado e manter tom. Ouvir, buscar na prévia e exportar; conferir os títulos e a capa.
9. Trocar tema/cor/ordem das abas, reiniciar e conferir persistência. Testar restauração seletiva.
10. Testar download com tela apagada e uso prolongado no aparelho real. Relatar modelo, Android e log sem cookies/segredos.

Antes de publicar como release Android, concluir assinatura definitiva, testes ARM64 reais e revisão dos componentes nativos descrita nos avisos de terceiros.

## Auditoria de paridade

Veja [PARIDADE-PC-ANDROID.md](PARIDADE-PC-ANDROID.md) para as lacunas identificadas. A existência de funções nesta tabela não significa equivalência integral com o PC.


### Fonte da interface

Em Configurações → Aparência → Fonte da interface, escolha Padrão do sistema, Sem serifa, Serifada, Monoespaçada, Condensada, Cursiva ou Arredondada. A prévia e a interface mudam imediatamente. Ative Lembrar configurações para manter a escolha ao reabrir; restaurar Aparência também restaura a fonte. Esta versão usa fontes nativas do Android, sem baixar arquivos de fontes.


### Enter nos campos

Em Pesquisar músicas, Enter do teclado físico ou a ação Pesquisar do teclado virtual inicia a busca, sem inserir uma linha. Os demais campos são de uma linha. Somente o campo LINKS em Links e fila aceita Enter para separar os links.

## Barra de reprodução em Efeitos

A barra fixa abaixo dos ajustes segue o transporte do PC: reproduz a faixa inteira com os efeitos atuais, pausa preservando a posição, retoma desse ponto e volta ao início ao parar. A linha do tempo mostra a posição na música original mesmo quando a velocidade muda; o volume é independente do Jukebox. O preset Original permite ouvir sem efeitos.

Abrir áudio aceita vários arquivos. Os botões anterior/próximo navegam pelos arquivos carregados, e a reprodução avança ao terminar uma faixa. Sem faixa anterior, Retroceder volta ao início. A barra e o acesso à letra permanecem visíveis durante a rolagem dos ajustes.

As filas de Efeitos e Jukebox permitem tocar, mover, remover e limpar entradas, preservando a música atual. A fila de Efeitos mostra capa, artista e duração; resultados de pesquisa têm ações distintas para reproduzir e adicionar à fila. A transição gradual respeita os segundos definidos em Áudio e prepara a próxima faixa antes da troca.

O botão de microfone abre a letra completa, com rolagem acompanhando o verso atual, toque para navegar e controles de transporte. O miniplayer do Jukebox oferece anterior/próximo e acesso a letras, parar, equalizador, timer, fila e volume. Cards e barras acompanham o espaçamento escolhido em Aparência.

Consulte a [revisão de paridade dos três commits](../docs/PARIDADE-ANDROID-2026-10-23.md) para os comportamentos verificados e os limites da validação.

### Abas independentes e notificação de Efeitos

Efeitos e Jukebox mantêm músicas e filas separadas. Alternar as abas não copia a música nem inicia uma análise na outra aba. Os ajustes de cada aba são preservados durante a alternância. Ao iniciar a reprodução em uma delas, a outra pausa.

A reprodução integral de Efeitos usa uma notificação de mídia própria, com título, artista, capa, posição e controles de reprodução, pausa, anterior, próxima faixa disponível e parada. Tocar na notificação abre Efeitos. A fila e as transições continuam sendo controladas fora da tela, permitindo avançar sem manter a aba aberta.

Na barra de Efeitos, a ordem é Letra, Retroceder, Pausar/Reproduzir e Avançar. No Jukebox, a mesma sequência é seguida por Mais; Parar/Cancelar fica nesse menu.

A barra de Efeitos usa uma única linha: Letra, Retroceder, Pausar/Reproduzir, Avançar, Fila e Mais. Não há botão de miniplayer nem linha auxiliar. O botão Fila abre um painel pela direita, com capa, título, artista e duração, além de tocar, mover, remover e limpar entradas. O transporte do Jukebox também apresenta Fila entre Avançar e Mais.

O volume das duas reproduções é controlado pelo sistema Android, inclusive pelas teclas físicas. Os sliders de volume foram removidos e o ganho normal do aplicativo é de 100%. O desenho do microfone acompanha o ícone inclinado do PC. Há 8 dp de espaço entre a linha divisória e os controles nas barras de Efeitos e Jukebox.

A duração configurável de prévias aplica-se somente às músicas das pesquisas. Foram retiradas as opções de duração de prévia dos efeitos e de continuidade entre abas/segundo plano; a reprodução integral continua ao navegar. Avisos de preparação redundantes com indicadores de progresso não aparecem no topo.


### Player compacto e reprodução expandida

A reprodução de Efeitos e Jukebox aparece em uma barra compacta acima da navegação, com capa, título, artista, Fila, reproduzir/pausar e progresso. Ela acompanha a navegação. O botão Fila substitui o acesso a dispositivos da referência visual e abre a fila correspondente à reprodução atual.

Tocar na capa ou no título abre a reprodução expandida. A capa do álbum ocupa a área visual, sem Canvas ou vídeo. A janela oferece linha do tempo, anterior/próxima, reprodução/pausa, letra, fila e menu; ao recolher ou voltar, a música continua. O menu mantém Parar, acesso aos ajustes de Efeitos e, no Jukebox, reprodução normal, timer e equalizador. As músicas, filas e efeitos permanecem separados entre as abas. O volume continua sob controle do sistema.


### Card de letras e tela cheia

O player expandido mostra um card Letra com o verso atual e os próximos versos. Tocar no card ou no ícone Expandir abre a letra completa em tela cheia, com título e artista, texto grande alinhado à esquerda, progresso e botão central de reprodução/pausa. A letra acompanha a música, mantém as animações e o destaque por palavra de LRC aprimorado, e permite tocar em versos sincronizados para navegar.

Recolher ou voltar retorna ao player sem interromper o áudio. Buscar letra online e Escolher letra estão no menu Mais da tela de letras. O botão Compartilhar abre o seletor de compartilhamento do Android. O recurso usa a música e a posição da reprodução correspondente, tanto em Efeitos quanto em Jukebox.


Em Efeitos e Jukebox, Pesquisar e Abrir arquivo ficam na mesma linha, abaixo do campo de busca, nessa ordem.


### Cor da capa e liquid glass

A barra compacta extrai a cor predominante da capa, com processamento fora da interface e reaproveitamento do cache de imagens. O fundo combina a capa desfocada, uma lente translúcida em degradê, reflexos, borda e sombra suave. Sem capa válida, usa a cor de destaque do tema.

Nos temas claros, o vidro recebe uma base clara com texto escuro; nos escuros, uma base escura com texto claro. Alto contraste mantém a tonalidade da capa, com lente menos transparente, borda reforçada, ícones e texto de alto contraste. A troca de música ou tema recalcula as cores sem alterar os controles.
