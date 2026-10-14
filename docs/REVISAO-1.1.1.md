# Revisão de código — ONDA 1.1.1

Revisão estática dos 77 módulos Python de produção e compilação/lint dos 35 arquivos Kotlin da aplicação. Inspeção dos caminhos de fila, consultas de metadados, cache de capas e histórico, preferências, subprocessos, atualização, ciclo de vida, notificações e substituição de áudio. Imports usados para validar dependências no autoteste foram mantidos mesmo quando não têm uma referência posterior: sua importação é parte da validação.

## Mudanças

- PC: removida a segunda atualização da lista ao selecionar um card. O teste observa uma única chamada e confirma a seleção.
- PC: removidos um import local repetido e uma segunda escrita idêntica do status do histórico.
- Android: consultas do DownloadManager rodam fora da thread da interface, somente com a tela iniciada. Estados ocioso, concluído ou falho encerram o ciclo; voltar à tela atualiza o estado novamente. Cancelamento de coroutine é propagado.
- Android: os controles de prévia deixam de consultar posição com a tela parada, preservando a reprodução em segundo plano.
- Android: a criação/configuração do canal de notificações ocorre apenas quando necessário, preservando configurações existentes.
- Android: quatro imports sem uso removidos. Mantida a correção que adia a troca de componente do ícone até o app ficar em segundo plano.

## Verificação

PC: 63 módulos, 392 testes aprovados, nenhum ignorado, cada módulo executado em processo separado. Logs em optimization-review-pc-tests na pasta de trabalho. Android: 19 testes instrumentados e cinco unitários aprovados; builds release/debug e lint concluídos, zero erros, 66 avisos e duas sugestões. A rodada inicial encontrou uma janela de permissão de notificações bloqueando o foco; a permissão de teste foi concedida e a rodada completa passou. Logs iniciais foram preservados. Os testes de launcher foram ajustados para consultar a tarefa correta e não depender de uma ida e volta cronometrada ao segundo plano.

Autoteste do portátil e integridade dos pacotes são verificados antes da entrega. A release pública 1.1.0 é preservada; 1.1.1 permanece em preparação local, sem publicação.

## Limites

Não foi medido consumo de bateria nem executado benchmark em aparelho físico; as reduções são de operações identificadas no código e verificadas por testes. Falta confirmar o comportamento do launcher no celular do usuário. Não foi repetida instalação/desinstalação Windows em ambiente limpo. Lint contém sugestões de modernização que não foram aplicadas em massa para evitar alterações cosméticas extensas. Nenhuma revisão garante a ausência de todos os defeitos ou de mudanças futuras nas plataformas externas.
