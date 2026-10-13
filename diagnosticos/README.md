# Diagnósticos de desempenho

Os diagnósticos usam mídia sintética local. Não fazem parte da interface do ONDA e não executam nos testes normais. O relatório do ensaio de 12/10/2026 está em [docs/DESEMPENHO.md](../docs/DESEMPENHO.md), com os dados brutos em [docs/desempenho](../docs/desempenho/).

Faça os ensaios com o aplicativo sem downloads pessoais ativos. Não compile durante a medição e execute os testes de PC e Android separadamente. Cada ensaio de carga pode levar vários minutos.

## Windows

Pré-requisitos: pacote `Portatil` já construído e FFmpeg preparado pelo ONDA. Execute na raiz do repositório:

```powershell
& '.\Portatil\_runtime\python\python.exe' '.\diagnosticos\benchmark_pc.py'
```

O script cria uma cópia temporária do programa, liga seu runtime por uma junção, inicia o mesmo `Onda.exe` e registra cinco aberturas, repouso e três repetições de seis cenários. A junção é removida sem apagar seu destino. Os dados e arquivos de teste são temporários; as configurações do usuário não são usadas nem alteradas. A cópia fecha automaticamente.

Para repetir apenas as aberturas e preservar os resultados anteriores de carga:

```powershell
& '.\Portatil\_runtime\python\python.exe' '.\diagnosticos\benchmark_pc.py' --startup-only
```

Saídas padrão: `diagnosticos/resultados/pc-results.json` e arquivos de amostras. `ONDA_BENCH_REPO` e `ONDA_BENCH_OUT` permitem escolher raiz do projeto e pasta de resultados. O medidor Windows usa APIs do sistema; não precisa de psutil nem adiciona dependências ao programa.

## Android

Use um emulador dedicado. Construa o app e o APK de instrumentação com ABI `x86_64`, pelo Gradle configurado no projeto, usando as tarefas `:app:assembleDebug :app:assembleDebugAndroidTest`. Instale ambos no emulador; permita notificações. O APK de teste nunca é o arquivo distribuído ao usuário.

Para cinco aberturas com processo encerrado entre tentativas, memória PSS e CPU em repouso fora de instrumentação:

```powershell
& '.\Portatil\_runtime\python\python.exe' '.\diagnosticos\benchmark_android_startup.py' --serial emulator-5580
```

O script usa `adb` no PATH, no SDK indicado por `ANDROID_HOME`/`ANDROID_SDK_ROOT` ou na localização padrão do SDK deste ambiente. Use `--adb` para um caminho diferente. Ele encerra somente o ONDA do dispositivo indicado entre tentativas. Não limpa seus dados.

Para os seis cenários de carga, com três repetições cada:

```powershell
adb -s emulator-5580 shell am instrument -w `
  -e class br.com.onda.mobile.PerformanceBenchmarkTest `
  -e ondaBenchmark true `
  br.com.onda.mobile.test/androidx.test.runner.AndroidJUnitRunner
```

É obrigatório informar `ondaBenchmark=true`; sem isso, o teste é ignorado. O teste preserva as preferências, baixa quatro WAV sintéticos de um minuto através do serviço normal, gera MP3, mede o consumo do app e de seus filhos, remove somente os arquivos/registros criados por ele e restaura as opções anteriores. Não rode enquanto outro trabalho do ONDA estiver em andamento.

O resultado fica em `files/performance-results.json` do app de teste. Copie usando o ADB da build debug:

```powershell
adb -s emulator-5580 shell run-as br.com.onda.mobile cat files/performance-results.json
```

O arquivo não contém credenciais, cookies ou nomes de arquivos pessoais. Os dados sob carga incluem o custo da instrumentação e do medidor. Tempos do emulador, RSS e CPU não devem ser tratados como previsão de desempenho em aparelho físico. A abertura é medida separadamente, sem a instrumentação JUnit.

## Comparações

Use o mesmo hardware, ABI, build, ferramentas, conteúdo, taxa de transferência e condições térmicas. Registre todas as tentativas e identifique aquecimento/interferências. Memória RSS, PSS e memória privada são métricas diferentes. O atraso do callback UI de 20 ms não mede FPS ou latência de toque. O relatório informa os limites do ensaio; não extrapole seus resultados para vídeos 4K, playlists grandes ou plataformas de streaming.

## Lista grande no PC

`python diagnosticos/benchmark_playlist_ui.py` usa a pasta `Onda` por padrão, com configurações temporárias e 5.000 faixas fictícias. Mede três carregamentos, atraso do callback de 1 ms e uma sequência de filtros; não faz downloads nem acessa a internet. O resultado vai para `diagnosticos/resultados/playlist-ui.json`. É possível passar a pasta de código e o JSON de saída como argumentos posicionais. Para comparação, execute o mesmo script e hardware em cada revisão. A janela fica oculta; o callback não mede FPS.
