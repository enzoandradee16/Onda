# ONDA 1.2.5

Versão 1.2.5 para Windows x64 e Android ARM64 e x86_64.

## Controle remoto e transferência PC ↔ Android

- Controle da reprodução do PC pelo Android, com capa, posição, fila, tocado recentemente e notificação de mídia.
- Ajustes de Efeitos e Jukebox e pesquisa para adicionar músicas à fila do PC pelo celular.
- Pareamento manual ou por QR Code, usando o código temporário exibido no PC. Os aparelhos precisam estar na mesma rede.
- Transferência da música atual de catálogo nos dois sentidos, preservando posição e estado de pausa. A fila, arquivos locais e configurações de efeitos não são transferidos.
- A origem continua durante a preparação e a troca só conclui após a confirmação do destino. Quando disponível, o Android aproveita o áudio já resolvido pelo PC.
- Proteções contra conexões atrasadas, comandos duplicados, transferências simultâneas, cache removido, mudanças de faixa/efeitos e preparação cancelada.
- Corrigido crash Android em reconexões rápidas e o encerramento da conexão quando o PC desativa o remoto.

## Reprodução, busca e playlists

- A preparação da fila aguarda o áudio e os efeitos ativos; troca entre streams preserva o foco de áudio no Android.
- Carregamento progressivo em cache temporário limitado a 256 MB no PC e Android, com indicação na barra e saltos pelos trechos carregados sem nova espera de rede.
- Reprodução normal por streaming no PC e Android; preparação de efeitos mantém o áudio atual até a nova versão ficar pronta.
- Melhorias na aplicação/remoção dos efeitos, no processamento de áudio e na continuidade da reprodução.
- Playlists da conta Spotify disponíveis para reprodução ou download pelo motor do ONDA; o catálogo não fornece o áudio do Spotify.
- Busca de músicas e letras com melhorias para japonês, variações de escrita, acentos e correspondência entre nomes.
- Correções dos sliders: valores acompanham o movimento; os efeitos são aplicados ao soltar. O volume é aplicado durante o ajuste.
- Retroceder reinicia a música depois de três segundos; antes disso, volta à faixa anterior.
- Reordenar a fila prepara a nova próxima faixa, preservando a identidade das músicas; correções no arrastar e remover no Android.
- Preparações aproveitam o áudio já carregado e falhas demoradas permitem nova tentativa, sem interromper a faixa atual.
- Abrir um arquivo local mantém o streaming atual até o arquivo ficar pronto; capas das faixas não são substituídas pelo mosaico da playlist.

## Desempenho e estabilidade

- Menos reconstruções de telas e filas, atualizações de capas e notificações e gravações repetidas de sessão.
- Índices de fila e caches reaproveitados; cópias de dados, leituras do histórico e processamento de áudio reduzidos.
- Salvamento da fila em segundo plano no PC, evitando bloquear a interface durante gravações no disco.
- Preparações canceladas interrompem o trabalho nativo e não iniciam a reprodução mais tarde.

## Aparência e ferramentas

- Claro Puro, opções de bordas e cor de destaque personalizada nas duas versões.
- Barra compacta Android acompanha as cores da capa.
- Menu da bandeja do PC com o tema do programa, reinício após mudar o idioma e melhorias de rolagem.
- Reprodução passa para Biblioteca no PC; no Android, permanece na barra inferior.
- Mensagens de operação/cache mais claras e aviso de pesquisa vazia.
- Foto com música em MP4 nos formatos de download de publicações compatíveis.
- Imagens: remoção de fundo opcional, prévia automática, colar arquivos/imagens no PC, comparação com o original, fundo transparente, cor sólida ou imagem, recorte central e rotação.
- Exportação de trecho da música com posições formatadas em minutos e segundos; desfazer remoções da fila.

## Verificações

- Testes automatizados de fila, streaming, efeitos, sessão, metadados e controle remoto no PC.
- Testes unitários Android e testes instrumentados no BlueStacks 5, incluindo reordenação durante preparação, remoção por gesto e transições com sobreposição real de áudio.
- Testes com HTTP local, áudio sintético, saída PCM nativa e falhas de rede simuladas. Não representam uma validação completa em aparelho ARM64 físico nem de todos os provedores externos.
- O relatório de validação que acompanha os pacotes registra os resultados da compilação final, assinaturas e limitações dos testes.
