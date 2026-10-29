# ONDA 1.2.4

## Nas duas versões

- Recuperação precisa da posição da música ao reabrir, mantendo o áudio pausado e preservando a retomada caso o cache precise ser preparado novamente.
- Deslizamento horizontal do conteúdo ao alternar entre Fila e Tocado recentemente, com indicador animado abaixo dos títulos.
- Prévia de imagens e carrosséis integrada à página Imagens; no PC, Visualizar mantém a imagem centralizada na página.
- Removida a ação Prévia do original do Conversor.

- Reprodução unificada: aplique Efeitos e Jukebox à mesma música e fila, com restauração da sessão sem iniciar o áudio automaticamente.
- Exportação com os efeitos ativos, nome no formato **Artista - Música - Slowed + Reverb**, tags e capa da faixa correta. Arquivos locais também preservam os metadados disponíveis.
- Letras escolhidas automaticamente, mantendo a opção de procurar e selecionar outra gravação.
- Transição gradual na reprodução normal, inclusive sem timer; repetição controlada diretamente pelo botão da barra.
- Preparação antecipada configurável para 1, 2, 3 ou 5 próximas músicas, com recuperação do cache e proteção contra estados de preparação travados.
- Proteção ao carregar álbuns e playlists grandes, respeitando o limite configurado e informando cargas parciais.
- Fontes ONDA Modern e ONDA Legacy disponíveis nas configurações. No Android, Modern usa a fonte do sistema e Legacy mantém Inter; no PC, Modern mantém Inter. Cards com álbum e data na mesma linha.
- Situação das ferramentas mais clara, com ícones, detalhes recolhidos e opção de reiniciar após uma verificação bem-sucedida.
- Ordem das categorias Biblioteca e Ferramentas configurável. Inventário de funções e guias revisados.

## Somente PC

- Fila com Tocando agora, próximas músicas e Tocado recentemente; adições manuais têm prioridade e as faixas anteriores continuam acessíveis pelo Retroceder.
- Correções na troca rápida de músicas, avanço, busca por posição e reorganização da fila. Ao desligar a reprodução aleatória, a ordem original é restaurada.
- Troca de faixa na fila com dois cliques, pesquisa recolhível e painel lateral redimensionável. Adicionar músicas pela pesquisa em Tocado recentemente volta à fila sem iniciar a reprodução.
- Indicadores visuais de preparação nas capas das duas filas, sem textos nem porcentagens.
- Miniplayer arredondado, capas de maior resolução, expansão suave para letras e fila e melhorias na rolagem.
- Fundo do miniplayer com desfoque, Swirl, halo e animações integradas à opção Efeitos translúcidos e liquid glass, ativada por padrão.
- Volume do miniplayer passa a atualizar o áudio corretamente. Preparações canceladas ou antigas não sobrescrevem o estado de uma nova operação.
- Menus suspensos padronizados; Exportar histórico como ação direta; Alterar destino com seletor de pasta e edição manual do caminho.
- Preto Puro sem bordas aplicado à Reprodução; opção de bordas disponível na janela de Aparência. Botão Equalizador na barra e remoção do atalho Metadados.
- Removido o componente antigo de miniplayer de Efeitos que ficou sem uso após a unificação.

## Somente Android

- Reprodução com busca compacta, cards de música e efeitos, ajustes do Jukebox e player com cronometragem acima da barra.
- Fila com música atual, próximas faixas e Tocado recentemente; abertura fluida de baixo para cima diretamente sobre a página atual, sem passar por Reprodução. Fechar retorna à página anterior.
- Fila aberta pelo player expandido permanece em uma janela inferior, preservando o player. Deslize fora dos cards para alternar as abas e deslize um card para a esquerda para remover a música.
- Resultados de pesquisa da fila com espaçamento maior e cantos menos arredondados; progresso da faixa atual abaixo da capa.
- Página Imagens com prévia na própria tela, setas, gestos, navegação por pontos, compartilhamento e download. Formato e Tamanho máximo ficam juntos nas opções visíveis da página.
- Conversor organizado em Arquivo de origem, Configurações e Pasta de destino, com Alterar destino e botão Converter; opções de lote e ajustes avançados no menu.
- Abas de Downloads mais compactas; Modern e Legacy trocadas no seletor de fontes do Android.

- Correções na capa da notificação de mídia, incluindo recuperação quando a imagem embutida é inválida ou a consulta falha temporariamente.
- Recuperação das faixas já preparadas ao reabrir, evitando repetir a análise ou manter a fila bloqueada em Preparando.
- Pacotes ARM64 para celulares e x86_64 para emuladores, assinados com a chave original.
