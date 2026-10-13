# Otimização de abertura e interface

Medição de 12/10/2026, posterior ao [ensaio inicial](DESEMPENHO.md).

## Alterações

- PC: as abas de pesquisa, imagens, playlists, histórico e efeitos são construídas somente ao acessar a aba ou usar uma ação que necessite dela. A página inicial respeita a ordem configurada. Temas, fontes e chamadas entre abas continuam disponíveis. Fechar o app ou consultar se há uma exportação não carrega abas ocultas.
- PC: playlists são desenhadas em blocos de 100 registros, cedendo tempo ao loop da interface. A pesquisa espera 150 ms sem digitação, reaproveita o índice de busca e aplica o filtro mais recente antes de uma ação com a seleção. Ações de download ficam desabilitadas enquanto a lista está sendo preenchida.
- Android: o índice de título/artistas é calculado uma vez por coleção, a busca espera 150 ms (sem permitir iniciar downloads com um filtro ainda pendente) e listas reutilizam a composição de linhas do mesmo tipo. As páginas já eram compostas sob demanda.
- Android: progresso visual limitado a uma atualização por 150 ms por download; notificações compartilham limite de 500 ms entre os downloads. Eventos finais, erros e pedidos de confirmação continuam imediatos. O limite afeta a apresentação, não a transferência ou a gravação dos arquivos.
- Android: cache compartilhado de capas limitado a 8% da memória disponível ao app e 24 MiB em disco. As imagens continuam sendo dimensionadas pelo Coil para o tamanho exibido. O limite não apaga capas incorporadas aos arquivos.

## PC: comparação direta

Mesmo computador Ryzen 5 5600X / 32 GB, emulador e compiladores parados. Cinco aberturas frias de processo por versão, sem limpar o cache do Windows, primeiro no portátil anterior e depois no atualizado. Cada ensaio usa uma cópia isolada do EXE/runtime, configurações temporárias e o mesmo gancho de diagnóstico descrito no ensaio inicial. Os dados abaixo são medianas; não são garantias de tempo em outro computador.

| Medição | Antes | Depois |
|---|---:|---:|
| Abertura pelo EXE | 1.276 s | 0.927 s |
| Preencher 5.000 músicas sintéticas | 77.5 ms | 137.2 ms |
| Maior atraso do callback da interface, mediana de três ensaios | 76.3 ms | 26.0 ms |

A abertura ficou aproximadamente **27% mais rápida** neste ensaio. Na playlist, preencher todos os registros levou mais tempo porque o trabalho foi dividido; o maior bloqueio observado diminuiu. A janela estava oculta durante o teste de lista, com o loop Tk ativo. Um callback de 1 ms acompanha carregamento e uma sequência de cinco filtros; sua demora mede a capacidade de atender outros eventos, não FPS ou latência de toque. Três repetições por versão, 5.000 faixas fictícias, 250 resultados no filtro final. Seleção e metadados foram preservados pelos testes.

## Android: verificação

No mesmo emulador x86_64 API 36 / 4 vCPUs / 2 GB / build debug, cinco aberturas sem instrumentação deram mediana de **2.89 s**. PSS em repouso: **104.2 MiB**. No ensaio anterior foram 3,08 s e 96,5 MiB; a variação de estado/caches e o pequeno número de amostras impedem afirmar redução de memória ou ganho significativo de abertura no Android. Nenhum resultado do emulador prevê o desempenho em celular físico.

Os ganhos de trabalho evitado no Android foram verificados com testes de rajadas de progresso, notificação compartilhada e downloads reais de conteúdo sintético. Não foi feita uma nova medição completa de CPU ou dos 18 lotes de conversão, pois o processamento de áudio não mudou. Não há alegação de conversão mais rápida nem de economia de RAM medida no celular.

## Validação e reprodução

- Suíte PC: `Ran 291 tests`, `OK`, com integração Tk e FFmpeg.
- Suíte Android: `OK (40 tests)` no emulador; testes de catálogo ao vivo e benchmarks longos seguem opt-in.
- Novos testes: abas sob demanda, temas, fechamento durante preenchimento de playlist, seleção com filtro pendente, 5.000 registros e limites de progresso/notificação.
- Scripts: `diagnosticos/benchmark_pc.py --startup-only`, `diagnosticos/benchmark_android_startup.py` e `diagnosticos/benchmark_playlist_ui.py`. As instruções gerais estão em `diagnosticos/README.md`.
- Dados brutos: `docs/desempenho/otimizacao/`. Não contêm credenciais, cookies ou nomes de arquivos pessoais.

O portátil, instalador e APK foram atualizados mantendo os nomes e versões existentes. Nenhuma configuração do usuário foi alterada automaticamente.
