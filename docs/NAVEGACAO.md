# Navegação e configurações

## Navegação Android 1.2.0

A barra principal contém Pesquisar, Downloads, Reprodução e Mais. Downloads alterna Em andamento / Concluídos; Reprodução alterna Efeitos / Jukebox infinito, respeitando a ordem configurada. Os dois usam o mesmo seletor arredondado de Salvos / Importar. O player compacto permanece disponível durante a navegação e abre a reprodução expandida. As [capturas da versão atual](../README.md) mostram esses fluxos.

Atualização de 12/10/2026.

## O que mudou

- **PC:** o tema e a fonte de cada controle são reaplicados quando a aparência muda ou o controle é criado. Reabrir uma janela ou trocar de categoria com a mesma aparência aproveita a configuração existente. Alterações de tema/fonte continuam atingindo controles de abas ocultas e janelas novas.
- **PC:** as categorias não recalculam largura de textos e região de rolagem quando essas medidas permanecem iguais. O redimensionamento da janela e a rolagem continuam disponíveis.
- **Android:** tocar no título de uma categoria vai diretamente à página escolhida, sem animar o percurso pelas categorias intermediárias. Deslizar para os lados continua funcionando.
- **Android:** o menu lateral fecha antes de construir a página ou abrir as configurações/sessão do YouTube. Cliques repetidos durante a transição não iniciam várias navegações. O retorno do teclado continua sendo condicionado à página e ao campo selecionado.
- **Android:** a credencial Spotify é lida em segundo plano ao acessar Contas, em vez de consultar o armazenamento criptografado toda vez que as configurações são abertas. O campo de segredo aguarda a leitura para evitar sobrescrever o valor salvo.
- **Android:** os sliders de duração da prévia atualizam o texto durante o arraste e gravam a configuração ao soltar. Os sliders de efeitos continuam atualizando a prévia como antes.

## Comparação no PC

Mesmo computador, configurações temporárias, sem emulador ou compilação durante a comparação. Cada versão percorreu as seis categorias quatro vezes e reabriu a janela a cada ciclo: 28 medições de navegação. O tempo engloba a troca de categoria/reabertura e o processamento dos eventos pendentes do Tk, com a janela visível. Não mede FPS nem garante estes tempos em outros computadores. A primeira exibição foi observada uma vez por versão.

| Medição | Antes | Depois |
|---|---:|---:|
| Mediana das trocas/reaberturas | 121.5 ms | 30.5 ms |
| Maior tempo observado | 237.9 ms | 54.1 ms |
| Primeira exibição das configurações | 412.2 ms | 110.7 ms |

A mediana ficou aproximadamente **75% menor** neste teste. Não foi feito um benchmark equivalente de navegação em celular físico; no Android a validação é funcional no emulador e não representa uma promessa de FPS.

Os dados brutos estão em `docs/desempenho/navegacao/`. Para reproduzir, use o mesmo hardware e execute `diagnosticos/benchmark_settings_navigation.py` indicando a pasta de código e um JSON de saída para cada revisão. O script usa configurações temporárias e não acessa a internet.

Validação: suíte PC de 291 testes, além da suíte Android no emulador, cobrindo navegação, deslizar entre categorias, temas, fontes, teclado, voltar e contas. O portátil, instalador e APK foram atualizados com os mesmos nomes e versões.
