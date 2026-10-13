# Medições de desempenho — ONDA

Data: 12/10/2026. Windows 1.0.0-beta.1 e Android 1.0.0-alpha.1. Estes números descrevem o ambiente e os cenários abaixo; não são uma garantia para qualquer computador, aparelho ou plataforma de mídia.

## Resultado principal

- **Windows:** abertura pelo EXE em **1.53 s** na mediana; repouso em **65.9 MiB de working set somado** e **0.08% de CPU total**.
- **Android no emulador:** primeiro quadro em **3.08 s** na mediana; repouso sem instrumentação em **96.5 MiB de PSS** e **0.07% de CPU total**.
- O motor de mídia Android levou **1.44 s** para inicializar na primeira utilização do processo, com as ferramentas já preparadas. Essa inicialização é adiada e não faz parte da abertura da tela.
- Aumentar a concorrência reduziu o tempo do lote e elevou o pico de memória. Normalização em duas passagens aumentou CPU e duração. Não há comparação com uma versão antiga: este ensaio compara opções da versão atual.

## Ambiente e método

Host: AMD Ryzen 5 5600X, 6 núcleos / 12 threads, aproximadamente 32 GB de RAM, Windows. Android: emulador Pixel 7, API 36, x86_64, 4 CPUs virtuais e 2 GB de RAM, com GPU por software. O aplicativo Android é uma build debug. O APK distribuído para celular é ARM64; **a velocidade e a memória medidas no emulador não preveem as de um aparelho físico**.

Cada cenário baixa **quatro áudios sintéticos de 60 segundos**, WAV mono PCM16 / 48 kHz, e gera MP3 de 320 kbps. O servidor HTTP é local e limita cada conexão a aproximadamente 2 MiB/s por pausas entre blocos; a taxa efetiva depende do agendador do sistema. O servidor pertence ao processo de diagnóstico, portanto seu pequeno custo está incluído. Não foram usados músicas do usuário, credenciais, cookies ou downloads da internet.

Foram comparados 1, 2 e 4 downloads simultâneos, com e sem normalização para −16 LUFS. Todos os lotes concluíram os quatro arquivos. Os tempos incluem a fila, extração/conversão e, no Android, publicação em MediaStore e o serviço de download com notificação.

O PC usa uma cópia isolada do portátil, com o mesmo EXE e runtime. Somente um gancho de medição, o nome da trava de instância e a dispensa das boas-vindas diferem. A janela é mapeada para marcar a abertura e fica oculta durante o ensaio de carga, mantendo o loop Tk ativo. Dados e arquivos são temporários; configurações reais permanecem intactas.

Cinco aberturas foram medidas em cada plataforma, encerrando o processo entre tentativas, sem limpar o cache de arquivos do sistema. São aberturas frias de processo, não uma instalação nova. No PC, a série inicial foi descartada como aquecimento/interferência da preparação do emulador: a tabela usa as duas repetições seguintes de cada cenário, com o emulador desligado. No Android, a tabela usa três repetições por cenário. A compilação não rodou durante as medições válidas.

## Downloads — Windows

Medianas de duas repetições válidas. CPU total considera os 12 processadores lógicos do host.

| Simultâneos | Normalizar | Tempo total (s) | Pico RSS (MiB) | CPU média total | Atraso UI p95 / máx. (ms) |
|---:|---|---:|---:|---:|---:|
| 1 | Não | 18.80 | 157 | 3.1% | 11.2 / 35.9 |
| 1 | Sim | 29.60 | 210 | 5.4% | 11.2 / 32.1 |
| 2 | Não | 9.96 | 245 | 6.3% | 11.2 / 65.6 |
| 2 | Sim | 17.32 | 333 | 10.6% | 11.3 / 56.5 |
| 4 | Não | 5.41 | 422 | 13.7% | 11.3 / 166.5 |
| 4 | Sim | 8.60 | 535 | 21.0% | 11.4 / 100.9 |

## Downloads — Android emulado

Medianas de três repetições. CPU total considera as quatro CPUs virtuais do emulador. Os valores sob carga incluem instrumentação JUnit/Compose e o próprio medidor. Por isso, o repouso sem instrumentação acima é a referência de consumo quando o app está simplesmente aberto.

| Simultâneos | Normalizar | Tempo total (s) | Pico RSS (MiB) | CPU média total | Atraso UI p95 / máx. (ms) |
|---:|---|---:|---:|---:|---:|
| 1 | Não | 16.35 | 269 | 10.3% | 1.0 / 8.0 |
| 1 | Sim | 28.97 | 330 | 22.1% | 1.0 / 22.0 |
| 2 | Não | 10.00 | 309 | 20.2% | 1.0 / 30.0 |
| 2 | Sim | 16.65 | 384 | 40.9% | 1.0 / 25.0 |
| 4 | Não | 5.37 | 409 | 27.9% | 1.0 / 6.0 |
| 4 | Sim | 11.72 | 499 | 59.3% | 2.0 / 24.0 |

## Como interpretar memória, CPU e resposta

- **Repouso:** Windows usa soma do working set do EXE e Python; Android usa PSS obtido por dumpsys fora dos testes. São medidas diferentes e não devem ser comparadas como se fossem idênticas.
- **Pico RSS:** soma da memória residente do app e dos subprocessos ativos, incluindo FFmpeg, amostrada a cada 100 ms. Pode contar páginas compartilhadas mais de uma vez; é um pico observado, não um limite garantido. O PC também registra memória privada nos dados brutos.
- **CPU:** tempo de CPU do app e subprocessos dividido pelo tempo de parede e pela quantidade de CPUs lógicas. Dados brutos também registram CPU em segundos e porcentagem equivalente a um núcleo. A amostragem Windows pode perder pequenos subprocessos que terminem entre leituras. Android inclui CPU de filhos já coletados pelo processo.
- **Atraso UI:** atraso de um callback solicitado a cada 20 ms, com p95 e o maior valor observado. Não é FPS, latência de toque, fluidez de animações nem uma auditoria completa de travamentos. O temporizador Tk/Windows apresenta granularidade própria.

Dois downloads simultâneos oferecem um compromisso entre duração e memória neste ensaio. Quatro reduziram mais o tempo, com pico maior. Manter um único download continua sendo a opção mais econômica em memória. A normalização deve continuar opcional, pois seu custo foi confirmado. Nenhum padrão do usuário foi alterado automaticamente.

Este ensaio não mede vídeos 4K, playlists de milhares de itens, renderização de efeitos ou bloqueios de plataformas. A primeira preparação das ferramentas e a transferência pela internet também ficam fora da medição de abertura. Uma comparação antes/depois de otimizações ou em aparelho físico requer outro ensaio controlado.

## Reproduzir

Os scripts e instruções ficam em `diagnosticos/README.md`. O benchmark Android é opt-in e fica ignorado nos testes normais sem o argumento `ondaBenchmark=true`. Os dados numéricos foram salvos em `docs/desempenho/`; não contêm contas ou caminhos de arquivos do usuário.
