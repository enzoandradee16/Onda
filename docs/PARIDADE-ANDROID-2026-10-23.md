# Paridade de comportamentos — PC e Android

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
