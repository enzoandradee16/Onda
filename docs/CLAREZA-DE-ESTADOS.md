# Ferramentas, estados e preparação das músicas

Implementação de testes da **1.2.3**, em 27/10/2026. Estes ajustes ainda não representam uma nova publicação da release.

## Situação das ferramentas

Em **Configurações → Ferramentas**, a verificação apresenta versões e disponibilidade dos componentes, data da última verificação e resultado/data da tentativa de atualização. Uma ferramenta indisponível não oculta o resultado das outras.

O relatório é local e persistente. Ao atualizar, as versões exibidas podem pertencer à verificação anterior; o aplicativo informa quando é necessário reiniciar. A verificação testa os componentes locais, sem prometer que um site externo continuará aceitando downloads. No Android, QuickJS informa confirmação de execução; isso não é um número de versão detectado.

### Visualização

O PC apresenta uma grade adaptada à largura e ao tamanho da fonte; o Android usa linhas compactas e botões lado a lado. Cada ferramenta tem um ícone identificador próprio do ONDA, nome, versão curta e indicação de disponibilidade. Os ícones são incluídos no aplicativo, sem consultas externas.

Datas são apresentadas de forma legível no fuso do sistema. Banners de compilação, copyright e versões completas ficam em **Detalhes técnicos**, recolhidos por padrão. A informação original da verificação não é descartada.

A revisão visual passou em 39 testes direcionados do PC, com renderização nos temas Claro, Preto puro e Alto contraste e fonte em 130%; o Android passou em 80 testes JVM. Os testes instrumentados foram compilados, sem execução nesta rodada por indisponibilidade do emulador via ADB.

### Reiniciar após verificar

Quando a última verificação confirmou todas as ferramentas disponíveis, **Reiniciar ONDA** aparece nas duas versões. O botão fica desabilitado durante operações em andamento; a ação também revalida essa condição antes de encerrar.

O reinício troca o processo inteiro para carregar ferramentas atualizadas. Filas, preferências e sessão são salvas antes da troca, e falhas de gravação impedem o reinício. A restauração da reprodução não inicia áudio automaticamente. No PC, o reinício ignora a opção de minimizar para a bandeja e aguarda o encerramento da instância anterior. No Android, usa um componente privado em processo separado, sem permissão de alarme ou agendamento de abertura em segundo plano.

O fluxo passou em 38 testes direcionados do PC, incluindo a espera entre processos, bloqueio durante operações e falha ao salvar. No Android, o teste real no emulador x86_64 usou a instalação isolada: o PID mudou, o auxiliar encerrou, o download pendente e as duas filas de reprodução foram preservados, com posição e preferências restauradas e áudio parado. A compilação e os 80 testes JVM passaram; não houve teste físico ARM64 nesta rodada.

## Ações e estados

Os dados antigos da fila são preservados; a apresentação normaliza os nomes entre plataformas:

| Situação | Nome visível |
| --- | --- |
| Aguardando download | Pendente |
| Transferência em execução | Baixando |
| Aguardando uma decisão do usuário | Aguardando confirmação |
| Download com erro | Falhou |
| Reprodução ainda não preparada | Aguardando preparação |
| Preparação em execução | Preparando |
| Preparação disponível | Pronta para reproduzir |
| Preparação com erro | Falha na preparação |

Pausar, Retomar e Tentar novamente respeitam os estados compatíveis. A nova tentativa não recoloca downloads concluídos na fila; para obter outra cópia, use a ação explícita de baixar novamente. Repetir um download com falha e repetir a preparação de áudio são ações diferentes.

Filtros de downloads incluem **Pausados** nas duas versões. Nomes técnicos persistidos e detalhes específicos de etapas não são removidos.

## Coleções parcialmente carregadas

Álbuns e playlists mostram quantas faixas foram carregadas. Se a origem informa o total, o aplicativo apresenta a relação carregadas/total. Limite atingido e itens ignorados são indicados quando conhecidos.

Quando a página pública não informa um total confiável, o ONDA mostra **total não confirmado**, sem afirmar que a coleção está completa. Uma página pública Spotify pode estar parcial mesmo com poucas músicas.

**Conferir lista importada** compara os links da coleção atual com um TXT, M3U ou CSV, sem substituir a coleção nem iniciar downloads. Apresenta correspondentes, ausentes e itens fora da referência, considerando repetições e parâmetros de compartilhamento reconhecidos. Links de catálogos diferentes não comprovam identidade da gravação; uma referência incompleta também limita a conferência.

## Falhas por música

As filas de Efeitos/Jukebox mostram o erro junto da música, orientação de causa provável e nova tentativa. Falhas de uma coleção em Efeitos permanecem representadas na fila em vez de desaparecerem.

**Tentar novamente** prepara a música afetada, preserva a ordem e não inicia o áudio por conta própria. No PC, Efeitos processa em tempo real: sua preparação verifica/lê o arquivo; não é a mesma renderização antecipada usada no Android.

Erros continuam sujeitos à conexão, origem, permissões, arquivo e ferramentas disponíveis. Uma orientação de causa provável não é uma confirmação de que o diagnóstico se aplica a todo erro técnico.

## Implementação e validação

- Comum: `Onda/collection_coverage.py`, `Onda/tool_status.py` e `Onda/workflow_status.py`.
- PC: controladores Qt e componentes de configurações, biblioteca, downloads e fila de reprodução.
- Android: `ToolStatusControls.kt`, `WorkflowStatus.kt`, telas de coleções/downloads e preparação dos players.
- **PC:** 72 testes dos fluxos alterados e 37 de traduções, filtros e restauração aprovados, total de 109. O autoteste de abertura do portátil também passou.
- **Ferramentas Windows:** verificação local real de Python, yt-dlp, gallery-dl, Pillow, Mutagen, FFmpeg, FFprobe, FFplay e Node.js; disponibilidade e versões retornadas sem consulta a sites.
- **Android:** 79 testes JVM aprovados e novos testes instrumentados compilados. A conexão ADB local do BlueStacks estava indisponível nesta rodada, portanto não houve execução dos novos testes de interface no emulador nem validação física ARM64.
- **Distribuição de testes:** portátil e APKs ARM64/x86_64 mantêm a numeração 1.2.3. O rascunho de release no GitHub não é atualizado automaticamente por estas compilações locais.
