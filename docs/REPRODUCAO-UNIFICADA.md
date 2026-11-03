# Reprodução unificada

Disponível na versão **1.2.4**, no PC e Android.

PC e Android passam a apresentar uma tela **Reprodução**, com uma música selecionada, uma fila e uma saída de áudio. Os painéis **Efeitos** e **Jukebox infinito** podem ser ligados juntos ou separadamente.

| Efeitos | Jukebox infinito | Comportamento |
| --- | --- | --- |
| Desligado | Desligado | Reprodução normal; avança pela fila ao terminar. |
| Ligado | Desligado | Reprodução normal com velocidade, reverb e preservação de tom configurados. |
| Desligado | Ligado | Navegação infinita entre trechos compatíveis da música original. |
| Ligado | Ligado | Navegação infinita com os efeitos aplicados ao áudio reproduzido. |

## Streaming na versão 1.2.5-rc

Faixas de catálogo podem tocar por streaming no PC e no Android. A reprodução começa com uma reserva pequena e completa o carregamento em segundo plano em um cache temporário de até 256 MB. O PC guarda PCM decodificado em disco e o Android guarda segmentos do player nativo e, para HLS, um arquivo temporário com os pacotes de áudio originais sem recodificação; a barra mostra a região disponível. Saltos pelos trechos carregados dispensam nova conexão. O cache é separado dos downloads, pode ser limpo nas configurações e respeita a limpeza automática de arquivos antigos. Trechos ainda não carregados dependem da rede. Endereços de streaming podem expirar e são resolvidos novamente quando necessário.

Slowed, Jukebox e outros efeitos que exigem processamento preparam o áudio em segundo plano. A faixa atual continua tocando; a posição mais recente é usada quando a versão processada está pronta. A preparação pode usar o cache de áudio. Desligar o processamento permite voltar à reprodução normal. A sessão conserva a faixa e a posição, sem persistir os endereços temporários e seus cabeçalhos de acesso.

## Interface

No PC, o acesso fica em **Biblioteca → Reprodução** na barra lateral e nas configurações de ordem/visibilidade. No Android, **Reprodução** continua no mesmo lugar da barra inferior.

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


## Transferir a música entre PC e Android

Na mesma rede, ative o controle remoto no PC e abra **Dispositivos** no player do Android.

- Para continuar no telefone, selecione **Este telefone → Continuar neste telefone** enquanto controla o PC.
- Para continuar no PC, use **Transferir música para o computador** no menu do dispositivo. Conectar normalmente apenas abre o controle e preserva a música que já toca no PC.
- Para conectar sem digitar o endereço e o código, use **Ler QR Code** e aponte a câmera para o código exibido no PC. O endereço e o código continuam disponíveis para digitação manual.

Esta primeira implementação transfere apenas a música atual de catálogo (Spotify, Deezer ou Apple/iTunes), com a posição e o estado de pausa. Cada aparelho prepara o próprio áudio; a origem permanece tocando durante a preparação. As configurações de efeitos de cada aparelho são mantidas. A fila, arquivos locais e links diretos de áudio/vídeo não são transferidos.

Ambos os aplicativos precisam estar atualizados. **Somente desconectar** encerra o controle remoto sem transferir o áudio.


A transferência só é concluída depois de o destino confirmar o início do áudio (ou a posição pronta, quando pausada). Cancelar a preparação interrompe também o processamento nativo. Se a conexão cair depois da pausa provisória do PC e antes da confirmação, o PC recupera a reprodução quando ainda é a mesma faixa e o usuário não mexeu nos controles. Uma ação posterior do usuário tem prioridade sobre essa recuperação.
