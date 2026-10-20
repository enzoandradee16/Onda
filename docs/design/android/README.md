# Referências de interface Android

Referências visuais usadas na atualização da interface Android em Compose. Os exemplos de músicas, capas e percentuais nas imagens são ilustrativos.

- `telas-principais.png`: pesquisa, downloads e Jukebox Infinito.
- `menu-mais.png`: ferramentas e biblioteca, com miniplayer persistente.

A navegação planejada tem quatro destinos: Pesquisar, Downloads, Reprodução e Mais. A imagem das telas principais ainda mostra três destinos; o quarto destino está representado na imagem do menu Mais. O botão + em Downloads serve para adicionar links à fila.

## Implementação

- Navegação inferior com Pesquisa, Downloads, Reprodução e Mais.
- Downloads reúne a fila; o botão + abre o painel de links com as opções existentes de formato e qualidade.
- Mais agrupa ferramentas e biblioteca, respeitando as abas ocultas e sua ordem salva.
- A engrenagem abre as configurações existentes; seus valores não são redefinidos.
- O miniplayer do Jukebox acompanha a navegação quando a opção existente de reprodução em segundo plano está habilitada.
- O tamanho dos cards de Downloads e da Pesquisa pode ser ajustado entre Pequeno, Médio e Grande, com a escolha salva.
- Ações adicionais das músicas ficam no menu de três pontos. Os controles completos da fila continuam em Mais ações → Gerenciar fila.
- O reconhecimento de links copiados continua disponível, com Baixar agora e Adicionar à fila.

Os recursos de processamento, downloads, reprodução e os presets do equalizador continuam usando os mesmos componentes e configurações anteriores.

Para testes de interface sem substituir o aplicativo instalado, use `-Ponda.isolatedUiTest=true` em uma compilação debug. Esse modo usa um identificador separado e não modifica os dados do app normal.

## Ajustes de navegação e fidelidade visual

- Arraste horizontal entre Pesquisa, Downloads, Reprodução e Mais, com animação de entrada. Sliders conservam seu gesto e área de toque, sem navegar por acidente.
- Capas das listas ampliadas; Downloads mostra progresso e percentual na mesma linha, com até três concluídos recentes abaixo dos ativos.
- Jukebox com capa maior, botão contornado de equalizador, grafo adaptado à altura disponível e controles adicionais no menu de reprodução.
- Esta rodada gera apenas o APK x86_64 de produção; o APK ARM64 anterior não é recompilado.
