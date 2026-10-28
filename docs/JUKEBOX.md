# Jukebox infinito

Referência revisada para **1.2.4**, em 27/10/2026. Veja [filas e reprodução no inventário](INVENTARIO-FUNCIONALIDADES.md#sec-09).

## Reprodução compartilhada

Efeitos e Jukebox compartilham uma música, uma fila e um player. Os dois painéis podem ser ativados juntos. Veja [Reprodução unificada](REPRODUCAO-UNIFICADA.md), incluindo migração de filas e preparação dos efeitos.

No Windows, há miniplayer flutuante, com capa, álbum, posição, volume, letras e fila compartilhados. A janela não acompanha a minimização da principal. A preferência **Minimizar ONDA ao abrir o miniplayer**, em Aparência, é consultada a cada abertura. É possível mover a janela pelo cabeçalho, capa e dados da faixa; controles não iniciam arraste. Fixar, restaurar, minimizar e fechar ficam no topo.

No Android, o player compacto e expandido pertence à interface do app. Efeitos e Jukebox ficam em cartões na mesma tela **Reprodução**; presets, manter tom e exportação ficam no menu de Efeitos.

- Abra um áudio local, pesquise uma música ou cole um link de música, álbum ou playlist. Coleções são adicionadas à fila; resultados avulsos permitem escolher a faixa. Fontes online são obtidas pelos mecanismos existentes do ONDA e precisam estar disponíveis; não há um servidor Eternal Jukebox integrado.
- A análise local compara pulsos, energia, timbre e conteúdo harmônico. Só permite saltos entre candidatos compatíveis; sem ritmo confiável ou correspondências, repete normalmente.
- Variação controla a frequência dos saltos; Transição suave ajusta a mistura curta nos pontos de mudança. Desligar Jukebox infinito ativa a reprodução normal, que avança pela fila. Volume, pausa/retomada e tempo ouvido funcionam sem reanalisar.
- No modo infinito, Mais fiel (variação zero) mantém saltos compatíveis pouco frequentes; também retorna antes do final quando há uma conexão segura para trás e evita repetir imediatamente o mesmo destino. Sem esse retorno disponível, continua repetindo a faixa normalmente.
- A análise e o áudio de trabalho ficam em cache por conteúdo. A limpeza de cache existente preserva arquivos ainda em uso; o original permanece intacto.
- Limite inicial: faixas de 3 segundos a 20 minutos; áudio de trabalho PCM estéreo de 16 bits/44,1 kHz. Pode ocupar mais espaço que o arquivo comprimido.
- Android: a reprodução integral continua ao navegar e usa uma sessão de mídia/notificação compartilhada em segundo plano. Foco de áudio, fones, bateria e ações do sistema podem pausar ou encerrar a reprodução.
- PC: sessão de mídia nativa do Windows para Jukebox e Efeitos, com metadados e comandos de reprodução disponíveis no player ativo.
- A variação muda a densidade do grafo nas duas versões, usando apenas conexões reais da análise.
- Implementação independente: não reproduz exatamente o algoritmo, as conexões ou a naturalidade do site Eternal Jukebox. As transições precisam ser avaliadas ouvindo diferentes faixas.

Traduções: português, inglês e espanhol. As identidades das abas antigas são mantidas para preservar ordem e ocultação. Os relatórios de versões anteriores preservam apenas as validações realizadas na época.

O equalizador de 10 bandas permite frequência, ganho e Q, pré-amplificação e sete presets. Atua na reprodução compartilhada e respeita Lembrar configurações. O grafo distingue conexões possíveis do trajeto reproduzido e acompanha o relógio da saída de áudio.

## Fila, preparação e restauração

O painel lateral da fila permite pesquisar texto ou links, adicionar músicas/coleções, tocar uma entrada, reorganizar, remover e limpar. Adicionar uma faixa não abre automaticamente o painel. As músicas já tocadas permanecem disponíveis para retroceder.

Repetição e reprodução aleatória controlam a ordem da fila; o modo infinito controla saltos dentro de uma faixa. Desligá-lo desativa os saltos. Estados por música informam preparação e disponibilidade, com preparação antecipada da próxima faixa quando possível.

Ao reabrir, o ONDA restaura filas, música e posição sem iniciar áudio automaticamente. Iniciar Efeitos pausa Jukebox e vice-versa, sem copiar a seleção entre abas. Navegar sozinho não deve interromper a música.

## Letras

O ícone de microfone abre as letras. A busca online usa LRCLIB e procura uma gravação compatível com título, artista, álbum, versão e duração; pode escolher automaticamente ou oferecer alternativas. Letras simples e sincronizadas dependem do que estiver disponível. No Android, o card de letra do player expandido abre também a tela cheia.
