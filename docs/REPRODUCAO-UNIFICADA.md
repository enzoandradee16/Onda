# Reprodução unificada

Disponível na versão **1.2.4**, no PC e Android.

PC e Android passam a apresentar uma tela **Reprodução**, com uma música selecionada, uma fila e uma saída de áudio. Os painéis **Efeitos** e **Jukebox infinito** podem ser ligados juntos ou separadamente.

| Efeitos | Jukebox infinito | Comportamento |
| --- | --- | --- |
| Desligado | Desligado | Reprodução normal; avança pela fila ao terminar. |
| Ligado | Desligado | Reprodução normal com velocidade, reverb e preservação de tom configurados. |
| Desligado | Ligado | Navegação infinita entre trechos compatíveis da música original. |
| Ligado | Ligado | Navegação infinita com os efeitos aplicados ao áudio reproduzido. |

## Interface

- No PC, os ajustes ficam lado a lado, com uma visão compacta da fila quando há largura suficiente. A fila completa continua acessível pelo ícone da barra e permite pesquisar, adicionar arquivos, reorganizar, remover e preparar novamente músicas com falha.
- No Android, os mesmos ajustes ficam em cartões na tela rolável. A barra compacta permanece única e abre o player expandido, com capa, letra e controles de reprodução. O ícone de fila também aparece no cabeçalho, inclusive antes de selecionar uma música.
- Timer, letra, equalizador, repetição e reprodução aleatória usam a mesma seleção e fila. Miniplayer e volume continuam disponíveis no PC; no Android, o volume permanece controlado pelo sistema.
- A repetição é ajustada pelo botão da reprodução: desativada → todas → uma → desativada. O modo de uma música usa o ícone de repetição com **1**; os modos ativos recebem destaque. O seletor foi retirado da fila.
- No PC, o Equalizador é aberto pelo ícone de ajustes na barra de reprodução; o botão de texto foi retirado do painel do Jukebox. No Android, o acesso ao equalizador permanece no menu do player expandido.
- Presets e exportação da música inteira continuam disponíveis. A exportação salva o arquivo com os efeitos escolhidos; não grava a sequência infinita de saltos do Jukebox.
- A exportação sugere **Artista - Música - Efeito**, usando os efeitos ativos, por exemplo **Tomoko Aran - Midnight Pretenders - Slowed + Reverb.mp3**. Título, artista, álbum, data, demais campos disponíveis e capa acompanham o arquivo, mesmo quando a reprodução usa um WAV temporário sem tags. Os parâmetros são capturados antes da janela de salvar; o destino inicial é a pasta configurada para downloads, não o cache.
- A configuração de ordem das antigas abas deixa de aparecer, pois não há mais duas abas para ordenar.
- A pesquisa da fila tem um botão **Fechar pesquisa** para limpar a consulta e os resultados, mantendo o painel e as músicas. No PC, Escape no campo tem a mesma função.
- A busca de letras automática escolhe a melhor correspondência. **Buscar letra online**, acionado pelo usuário, oferece outras gravações para escolher; cancelar mantém a letra atual.
- **Transição gradual** também sobrepõe automaticamente as músicas da fila em reprodução normal, sem timer e com efeitos ligados. A duração respeita o tempo restante da faixa; no fim da fila, há saída gradual. Desligar a opção mantém a troca sem sobreposição.

## Processamento

A análise de ritmo e os vínculos entre trechos usam o áudio original. O processamento de efeitos gera uma cópia temporária; os tempos usados na leitura dessa cópia são ajustados à velocidade sem alterar a análise original nem o arquivo de origem.

Ao ajustar efeitos durante a reprodução, a versão que já está tocando continua até a nova cópia ficar pronta. O painel informa essa preparação; portanto, a primeira aplicação de uma combinação de efeitos pode levar alguns segundos. Versões já preparadas são reutilizadas. A preparação das próximas músicas também aquece esse cache.

O processamento é limitado a um FFmpeg de efeitos por vez, com cancelamento de solicitações substituídas e publicação atômica do resultado. Mantém até três combinações de efeitos por música, preservando arquivos que ainda estejam abertos por uma sessão no Windows. A limpeza geral de cache continua aplicável.

## Sessões anteriores

As filas antigas são reunidas uma vez, mantendo a fila do Jukebox e acrescentando os itens de Efeitos. Repetições existentes não são descartadas por título. A posição da música de Efeitos é mantida para retomar quando ela for a seleção migrada; uma seleção já restaurada do Jukebox tem precedência.

Os dados da sessão antiga de Efeitos permanecem disponíveis no armazenamento local. A migração não inicia áudio automaticamente. A preparação e a reprodução da seleção migrada só começam por uma ação de reprodução.

## Verificação

- Testes Python verificam cópia processada com FFmpeg real, preservação da análise, duração com velocidade alterada, efeitos com saltos, retorno ao áudio original, migração única e carregamento do QML.
- Testes instrumentados Android verificam os dois controles sobre o mesmo player, migração silenciosa e chamadas reais de preparação e reprodução PCM com efeitos.
- O aparelho físico ARM64 ainda exige verificação prática; testes no emulador não substituem essa validação.
