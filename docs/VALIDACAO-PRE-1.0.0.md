# Validação antes da versão 1.0.0

Revisão de 13/10/2026, concluída após a meia-noite UTC. Avaliação da árvore de trabalho local, incluindo alterações ainda não publicadas.

## Resultado

Nenhum bloqueador foi encontrado nos cenários aprovados abaixo. Os builds corrigidos estão preparados para a etapa de lançamento, mas esta revisão não publicou uma release nem alterou a numeração para estável. Ainda é recomendável confirmar os fluxos principais em um aparelho Android físico antes de declarar suporte estável nas duas plataformas.

## Correções e otimizações

- Cache limitado de metadados e capas no histórico: até 64 entradas no PC e 24 no Android. Evita releituras repetidas. No PC, tamanho e data de modificação invalidam a entrada; no Android, alterações internas e reentrada no histórico atualizam o cache.
- Substituição de downloads Android preserva a URI existente e usa cópia de segurança e restauração em caso de falha, em vez de apagar o arquivo antes da gravação.
- Configurações da busca Android passam a acompanhar mudanças pelo estado observado da interface.
- Removida a opção de 64 kbps no diálogo Android, incompatível com as opções aceitas pelo mecanismo de download.
- Cancelamento de atualização de layout pendente ao destruir uma página rolável no PC.
- Removidos imports sem uso e uma chave duplicada de configuração de continuação de download. Imports usados para diagnóstico de dependências foram mantidos.
- Testes de fila atualizados para o comportamento paralelo atual. Testes Android de interface preparam a permissão de notificações para evitar que o diálogo do sistema bloqueie a tela.

Não foram adicionadas dependências de produção. A ferramenta de análise estática foi instalada somente no diretório temporário da auditoria. Não foi medido um percentual de ganho de desempenho.

## Verificações

| Verificação | Resultado |
| --- | --- |
| PC: 56 módulos de testes, executados em processos separados | 346 testes aprovados, nenhum ignorado |
| Android: testes unitários | 5 aprovados |
| Android: testes instrumentados distintos | 59 aprovados; 2 benchmarks opcionais não executados |
| Android: análise lint | 0 erros, 56 avisos |
| Android: debug, testes e release | Compilação aprovada |
| Python: compilação e análise estática | Sem erro de sintaxe ou nome indefinido identificado; avisos remanescentes de imports diagnósticos/testes |
| Git: diff --check | Aprovado |

A validação PC incluiu conversões reais com FFmpeg, efeitos, metadados, capas, letras, proteção do original, filas, preferências, histórico e interface em janelas pequenas. Uma execução monolítica encontrou falha de encerramento do Tcl envolvendo múltiplas raízes de testes e threads; a execução isolada de todos os módulos passou. Isso não foi tratado como evidência de estabilidade de uma execução monolítica.

Sete testes Android inicialmente foram bloqueados pelo diálogo de permissão de notificações; após corrigir a preparação dos testes, os sete passaram. Três testes online opcionais também passaram: catálogos Apple/Deezer, link Spotify e metadados YouTube. Os 59 aprovados são casos distintos, não a soma de tentativas repetidas.

Os avisos lint incluem sugestões de dependências/API, estilo e verificações de contexto/permissões. Não foi feita uma atualização ampla de bibliotecas nesta fase.

## Instalação e atualização

- PC: instalação limpa e atualização de uma cópia da versão anterior testadas em diretórios isolados, usando a receita do instalador sem atalhos, registro de desinstalação ou execução automática. Inicialização e sete abas verificadas; arquivo adicional preservado.
- PC portátil: autodiagnóstico aprovado, incluindo disponibilidade das ferramentas de mídia.
- Android: reinstalação de atualização debug preservou os hashes das preferências e banco de dados.
- Android: APK de produção assinado instalado do zero no emulador e iniciado; processo ativo e registro de falhas vazio.
- Instalador Windows e APK Android finais reconstruídos após as correções.

## Limites e próximos critérios

Não foram testados nesta revisão um aparelho Android físico, todas as versões Android suportadas, integração de atalhos/desinstalação Windows ou atualização de uma instalação Android antiga de produção. Os dois benchmarks instrumentados opcionais não foram executados. Os testes online não garantem disponibilidade de todas as publicações, regiões ou sessões autenticadas.

A correção Kwai foi validada anteriormente nesta sessão com o vídeo exato solicitado (59 segundos, 720 × 1280), sem substituir por vídeo recomendado; não houve novo download Kwai Android nesta rodada final.

Antes de publicar, confirmar no aparelho físico importação de imagem, download, histórico, edição e efeitos. Em seguida, preparar a numeração estável, notas e artefatos da release. Nenhuma publicação foi realizada por esta revisão.

## Artefatos

- Windows: `Instalador/Onda-Setup.exe`
- Android: `Celular/APK/ONDA-Android-1.0.0-alpha.2-arm64-v8a.apk`
- Evidências locais: `diagnosticos/resultados/pre-1.0.0/` (não versionadas).

SHA-256 do instalador: `A1CB935FD69E503F9B75F5DE64C3EEAF97F198B4BDBBF46FA6882158DA71BB33`.

SHA-256 do APK: `7B7B0079DBBD7BB3C1725FF7576D53947167561375DCE7B5DAC1C715DCE5DC44`.
