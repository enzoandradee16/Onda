# Paridade de comportamentos — PC e Android

## Estado final da preparação 1.2.0

O PC agora oferece escolha de formato/qualidade por música ao clicar em Baixar agora e compartilha o miniplayer entre Efeitos e Jukebox, com minimização independente. O Android tem player compacto/expandido, letras em tela cheia e seletores arredondados comuns a Downloads, Reprodução e Álbuns. A documentação e as capturas atuais estão no [README](../README.md). Os parágrafos abaixo registram etapas anteriores da revisão e não substituem esse estado final.

Revisão dos commits `6e157f02c1d369d68af1b20ba0f3824f5ffa7961`, `0edd48a80284b678fb730370cbb5661ff4fb00f0` e `2d2194d3d0ec76f062927e8c4d221f6e7859380f`, consultados no GitHub e comparados com os fontes locais. Mantida a versão de teste 1.2.0 e as alterações locais anteriores.

## Diferenças verificadas e tratadas

| Área | Situação no Android e alinhamento |
| --- | --- |
| Transporte de Efeitos | Barra fixa, música inteira, pausa/retomada, parada no início, posição na música original, volume independente e anterior/próximo. Implementação da rodada anterior preservada e integrada à fila. |
| Fila de Efeitos | Acrescentados painel de fila, capas/metadados/duração, seleção de vários arquivos, tocar, mover, remover e limpar. Acrescentar arquivos e resultados não substitui a faixa atual. A identidade da faixa é preservada ao reordenar; retirar uma entrada não apaga seu arquivo. |
| Pesquisa em Efeitos | Enter/Pesquisar, Cancelar, fechar resultados e ações separadas Reproduzir/Adicionar à fila. O carregamento usa `fetch_audio(..., analyze=False)`, sem analisar o Jukebox. |
| Transição em Efeitos | Preparação antecipada da próxima faixa, duas saídas ExoPlayer durante a sobreposição e liberação da saída anterior ao pausar/parar. Usa Transição gradual e duração de 1–10 segundos de Áudio, como o PC. Sem transição gradual, troca sem sobreposição. |
| Jukebox | Anterior volta à faixa anterior ou ao início; Próxima usa a posição atual da fila. A fila preserva músicas reproduzidas para permitir voltar, além de mover e limpar entradas sem encerrar a música atual. Selecionar uma faixa aguardando análise agenda sua reprodução. |
| Controles do Jukebox | Letra, Retroceder, Pausar/Reproduzir, Avançar e Mais. Parar/Cancelar fica em Mais; volume independente e botões de transporte com áreas de toque Material. Notificações/MediaSession aceitam anterior/próximo. |
| Miniplayer | Mantido como card nativo Android, com título/capa e transporte separados em linhas para não comprimir os textos. Acesso a anterior/próximo, letras, parar, equalizador, timers, fila e volume. |
| Letras | Lista completa rolável, acompanhamento do verso ativo, toque por verso, controle de posição sem disputa com o relógio, reprodução/pausa e anterior/próximo. Texto simples permanece inteiro; LRC aprimorado mantém o destaque por palavra e esconde marcações de tempo nos versos inativos. |
| Animação da letra | Suave usa fade, Deslizar acrescenta deslocamento vertical de 10 dp e Zoom usa escala de 0,96 até 1. Preparação de 30 ms e entrada de 180 ms, como `AnimatedLyric.qml`. Desativada aplica o estado imediatamente. Aplicadas à janela de letras e ao verso exibido em Efeitos/Jukebox. |
| Busca de letras | Cache por arquivo durante a sessão, proteção contra respostas de outra faixa e escolha manual preservada. Busca automática não ocupa o estado de operação de áudio/pesquisa. |
| Espaçamento | Cards e controles de reprodução usam a preferência Compacto/Padrão/Confortável. Ações longas da janela de letras ficam em coluna; filas têm altura limitada e rolagem. Capas usam superfícies arredondadas. |
| Histórico/metadados | Já havia leitura de detalhes/capas, seleção de áudios e edição em lote. Preservados os caminhos Android por URI, compartilhamento e permissões de armazenamento. |
| Motor musical | Reverb, letras online e progressão do Jukebox dos três commits já fazem parte dos módulos Python compartilhados. O build Android copia os módulos atuais de `Onda`; não foi criado outro motor. |
| Fila de downloads e prévias | O Android já tem escopo de pedidos imediatos, cancelamento de prévias com geração/ID e controle próprio de pausas. As correções específicas do controlador Qt não foram copiadas sobre os serviços Android. |

## Recursos específicos do Windows

Janela flutuante sem bordas, fixação acima de outros programas, geometria/maximização, bandeja, atalhos de teclado do desktop e captura de teclas permanecem recursos do Windows. O Android usa o miniplayer interno, MediaSession, notificações e navegação do sistema, sem solicitar permissão para desenhar sobre outros aplicativos.

## Validação

Na revisão final das barras, o PC mantém Retroceder, Pausar/Reproduzir e Avançar no centro exato das duas barras, com Timer e Letra à esquerda e Fila, Miniplayer e Volume à direita. O timer de Efeitos controla sua própria reprodução, sem alterar os timers do Jukebox. No Android, Fila fica entre Avançar e Mais, a linha auxiliar e o miniplayer foram retirados, e o volume é controlado pelo sistema. O microfone usa o mesmo desenho do PC. Os 70 testes Qt passaram, incluindo pausa e disparo dos timers independentes; a ordem e a centralização foram verificadas nos componentes QML carregados.

A rodada atual acrescentou notificação de Efeitos, separação das abas, miniplayer de Efeitos e fila lateral direita com metadados nas duas plataformas. Os controles do PC foram conferidos por suas posições no QML; o painel e a janela compacta carregaram na verificação isolada. Os 69 testes da interface Qt passaram. O Android compilou os testes instrumentados, mas sua execução em aparelho continua pendente. As configurações de duração dos efeitos e de continuidade entre abas foram retiradas; a duração de prévias das pesquisas permanece disponível.

- 66 testes JVM aprovados, sem falhas. Cobrem ordem/identidade da fila, limites de movimento, relógio com velocidade alterada, fim da faixa, versos sincronizados e texto sem marcações.
- Testes instrumentados atualizados para transporte fixo, pausa/posição/parada, letras completas e toque por verso, fila e sobreposição das duas saídas. Compilação dos APKs de teste verificada.
- Testes de referência do PC: 89 casos, 84 aprovados e 5 ignorados conforme suas condições; nenhuma falha.
- Backend Android verificado com FFmpeg/ffprobe reais no Windows: duração, remoção do prefixo de importação, metadados de catálogo sem substituir tags locais, reprodução integral de 205 segundos, busca no último meio segundo e preservação do limite das prévias comuns.
- O emulador API 35 x86_64 foi instalado, mas falhou neste Windows sem driver de aceleração, inclusive com tentativas de renderização por software. Não houve execução instrumentada nem validação visual em aparelho nesta rodada.
- APKs release devem ter assinatura original, versão 1.2.0/code26 e alinhamento de 16 KB verificados antes da substituição. Portátil sincronizado e verificado com o teste isolado de abertura.


## Player Android compacto/expandido

A barra Android foi substituída pelo player compacto com capa, título, artista, fila, reprodução/pausa e progresso, presente durante a navegação. Tocar no corpo abre uma janela de reprodução com capa do álbum e transporte completo. O Canvas permanece apenas na ferramenta de análise do Jukebox; a janela expandida usa uma imagem estática da capa. As filas e os controles continuam independentes entre Efeitos e Jukebox.

Os testes instrumentados foram adaptados para abrir/recolher a janela, conferir a capa, buscar pela linha do tempo e abrir a fila. A execução em aparelho continua necessária; este ambiente verifica compilação e testes JVM.


A experiência de letras Android agora inclui card de prévia no player expandido e uma janela em tela cheia, com metadados, texto grande, compartilhamento, menu de busca/importação, progresso e reprodução/pausa. Foram preservados acompanhamento, animações, destaque por palavra e navegação por verso. O teste instrumentado cobre abrir o card, conferir título/artista, navegar, pausar e recolher; sua execução em aparelho permanece pendente.


Nas abas Android de reprodução, Abrir arquivo foi posicionado à direita de Pesquisar, na mesma linha abaixo da busca.


A barra compacta Android ganhou acabamento liquid glass com a cor predominante da capa, desfoque da imagem, lente translúcida, reflexos e bordas. Há adaptação a temas claros, escuros e alto contraste, e cor de destaque como fallback. Testes JVM verificam a extração da cor e o contraste do título/artista sobre as camadas compostas, incluindo capas extremas e transparências.


Após a preparação da rc2, o Android recebeu um ajuste de reprodução para testes: Reprodução normal visível e reativa na aba Jukebox, ações de reprodução em cada aba e troca pelo menu expandido. Iniciar/retomar Jukebox pausa Efeitos inclusive na retomada; iniciar Efeitos pausa Jukebox. A simples alternância não reinicia a renderização de Efeitos. Novos cenários instrumentados cobrem alternância, retomada e preservação de músicas e opção normal; execução em aparelho continua pendente. Estes ajustes locais não alteram os pacotes do rascunho rc2 já preparado.


Os botões Android de troca ficaram condicionais à reprodução controlada pela barra e foram movidos para os metadados da música. No PC, os transportes separados já permitem iniciar cada aba; foi corrigida a pausa de Efeitos ao iniciar ou retomar Jukebox, preservando a posição e a faixa.


### Correção de letras e capas

As duas abas Android passam os metadados da gravação à integração LRCLIB compartilhada com o PC. Os metadados de catálogo têm prioridade sobre tags do áudio temporário, e o nome de arquivo sem tags não substitui o título. Efeitos mantém cover_url e usa a capa de catálogo na página, fila e barra compacta quando não há imagem embutida. A conclusão da leitura dos metadados reinicia uma busca prematura de letras.

Validação: 10 testes de letras; consultas reais ao LRCLIB para Stardust e Daft Punk retornaram letras sincronizadas; teste do adaptador Android confirmou título, artista, capa e duração; autoteste do portátil aprovado. Validação visual em aparelho permanece pendente.

O cartão e a janela de letras Android usam a cor predominante da capa (embutida ou de catálogo), compartilhando a extração usada pela barra compacta. Na ausência de capa usam o tema. Cores de texto são escolhidas por luminância, com teste de contraste para capas extremas e alto contraste.

As barras compactas Android de Efeitos e Jukebox incluem o botão de microfone antes da fila, abrindo diretamente a janela de letras da faixa atual.


### Cache em aparelhos Android e progresso único

A promoção do áudio baixado para o cache de Efeitos copia somente os bytes (copyfile), sem copystat/xattrs de segurança, que podem ser negados pelo SELinux em aparelhos. O teste de obtenção de áudio simula PermissionError ao copiar atributos e confirma que o áudio fica legível e a pasta temporária é removida. Essa é uma correção para o caminho de cópia; a confirmação no aparelho que apresentou o erro permanece pendente.

Operações vm.busy usam apenas a barra geral. Removidas barras redundantes em Efeitos, coleções, metadados, configurações, conversor e recuperação de falhas. Preparação local de metadados em lote mostra sua barra somente sem uma operação geral ativa. Indicadores de tarefas independentes e progresso de reprodução foram mantidos.

Validação Python: 53 testes, 4 ignorados, nenhuma falha.

As pesquisas do Jukebox Android (página e fila) aceitam Enter/ação Pesquisar do teclado. Consultas vazias e novos envios durante uma operação ativa são ignorados.

A página Jukebox usa o cartão Sua música com campo rotulado e botões de contorno, além do mesmo componente de informações de faixa de Efeitos (capa, título, artista, álbum, duração). Reprodução normal fica após os cartões.

A tela Reprodução Android separa os botões Efeitos/Jukebox com intervalo de seção (16 dp no modo Padrão), alinhando suas margens aos cartões. Os controles internos ganham 2 dp e os intervalos de seção 4 dp, somente nas páginas de reprodução. Os cartões de ambas as abas usam intervalos de seção; os modos Compacto e Confortável continuam respeitados.

A busca automática de letras compartilhada PC/Android consulta alternativas LRCLIB quando não há resultado exato. Classifica por título, artista, álbum, proximidade da duração e sincronização; descarta incompatibilidades de versão (live/remix/radio etc.) e duração acima de 8 s ou 4%, o maior. Não escolhe a primeira letra indiscriminadamente; seleção manual preservada. Validação: 14 testes de letras aprovados.

Filas Android de Efeitos e Jukebox agora abrem em folha inferior, com capa, título, artista, duração e seções Já tocadas/Tocando agora/A seguir. Editar revela opções de reordenação e remoção; tocar uma faixa mantém a folha aberta. Seleções diretas no Jukebox entram na fila com modelo preparado, permitindo Retroceder após novas escolhas e mantendo as anteriores durante a sessão. Nenhuma faixa é removida automaticamente ao avançar.

Resultados da pesquisa na fila Jukebox exibem capa, título, artista e álbum no Android e PC. Android divide a área disponível entre resultados roláveis e fila, mantendo o toque para adicionar. O PC preserva seleção/reprodução e botão Adicionar à fila. Sem capa, usa o símbolo de música. Testes PC: 74 aprovados.

Pesquisas gerais de Efeitos e Jukebox Android exibem capa, título, artista e álbum, mantendo seus comandos de reprodução/adição. A pesquisa de Efeitos PC também ganhou capa e álbum (Jukebox PC já usa esse padrão). O ícone compartilhado close agora desenha X, corrigindo o fallback de três linhas em todos os botões de fechar/remover que o utilizam.

Correção da faixa exibida como audio na fila de Efeitos PC: o resultado de catálogo agora acompanha o caminho do cache até a leitura dos itens da fila, preservando título, artistas, álbum e cover_url. A capa embutida mantém prioridade visual; sem ela, usa a URL de catálogo. No Android, appendEffectsRecord atualiza informações já carregadas, e leituras em andamento incorporam os metadados mais recentes antes de publicar o resultado. Dois testes de regressão confirmam os adaptadores PC e Android com áudio temporário sem tags.

Resultados da pesquisa principal do Jukebox Android passam a usar o mesmo formato de Efeitos: cabeçalho Resultados com X para fechar, linha de capa/título/artista/álbum sem contorno e ações separadas Reproduzir/Adicionar à fila. Reproduzir prepara e inicia a faixa; adicionar mantém a reprodução atual.
