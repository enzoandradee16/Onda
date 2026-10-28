# Funcionalidades do ONDA para Android

Guia revisado para **1.2.3 (código 30)** em 27/10/2026. Consulte o [inventário completo](../docs/INVENTARIO-FUNCIONALIDADES.md) para referências ao código e o [relatório da release](../docs/VALIDACAO-RELEASE-1.2.3.md) para testes e limites.

## Navegação e aparência

- **Pesquisar:** catálogos de músicas.
- **Downloads:** Em andamento/Concluídos; o botão + abre a entrada de links.
- **Reprodução:** Efeitos e Jukebox infinito na mesma tela, com música, fila e player compartilhados.
- **Mais:** álbuns e playlists, imagens, conversor, editor e outras ferramentas.
- **Cabeçalho:** ícones de Aparência e Configurações.

A ordem das áreas elegíveis é configurável. Instalações novas usam Preto puro + Verde-Água; preferências existentes são preservadas. Há temas Claro, Escuro, Sistema e Alto contraste, 16 destaques, fontes, escala e espaçamento. Português, espanhol e inglês são aplicados imediatamente.

## Pesquisa e links

Pesquisa Deezer, Apple/iTunes e Spotify, com opção Todos conforme os provedores disponíveis. Cards mostram capa, título, artista, álbum, plataforma e data quando disponíveis; informações ausentes podem ser completadas em segundo plano.

Enter do teclado físico ou a ação Pesquisar do teclado virtual inicia a consulta, inclusive na reprodução. O formulário de vários links em Downloads aceita quebras de linha para separar URLs.

As ações dos cards permitem baixar, adicionar à fila, ouvir prévia, abrir origem e copiar link conforme a tela. Áudio MP3/M4A de catálogo procura uma gravação correspondente no YouTube; FLAC consulta Monochrome quando houver correspondência compatível. Metadados de streaming não são exportação do áudio protegido do serviço.

Instagram, TikTok, Kwai e X/Twitter têm caminhos de extração próprios, além dos extratores compartilhados. Fotos, vídeos e carrosséis podem ser selecionados quando acessíveis. Cookies, login, região/IP e disponibilidade ainda podem impedir downloads.

## Downloads e histórico

- Fila persistente e concorrência de 1 a 4 itens, com opções por solicitação.
- Busca, filtros, seleção, pausa/retomada, cancelamento, remoção e nova tentativa conforme o estado.
- Arraste do card inteiro por toque prolongado; marcador compacto sobreposto e deslocamento dos vizinhos antes de soltar.
- Etapa, progresso, velocidade, tamanho e estimativas quando disponíveis.
- Recuperação de interrompidos com progresso aproximado; aproveitar dados parciais depende do servidor.
- Agendamento diário, retomada opcional ao abrir e Somente Wi-Fi, com política ao perder a conexão.
- Serviço em primeiro plano e controles de notificação, sujeitos à bateria e às restrições do sistema.
- Histórico com pesquisa, filtros Todos/Áudio/Vídeo/Imagens, abrir, compartilhar, editar ou usar em Efeitos conforme o arquivo.
- Remoção de registro preserva o arquivo e pode ser desfeita por 8 segundos.
- Falhas apresentam causa provável e ações úteis; isso não contorna restrições da plataforma.

Android 10+ usa Downloads/ONDA por padrão; outra pasta pode ser escolhida nas configurações. Android 8/9 precisa de pasta escolhida para preservar arquivos fora dos dados privados do app.

## Álbuns e playlists

Carregue URLs ou importe TXT, M3U e CSV/Exportify. Há pesquisa, seleção, formatos próprios, exportação TXT/M3U, conferência de correspondências/arquivos locais, inclusão de ausentes e biblioteca de coleções salvas.

Carregar vira Cancelar durante a consulta e Atualizar quando a mesma coleção já está carregada. Ações secundárias ficam em Mais ações. Capas dependem da fonte; a leitura pública do Spotify pode ser parcial.

Para reprodução, cole o link diretamente em Reprodução ou na pesquisa da fila compartilhada. Os botões antigos de enviar a coleção a players separados não são necessários na página de coleções.

## Efeitos e Jukebox

Ambos aceitam arquivos locais, pesquisa e links de música, álbum ou playlist. As filas têm capa, título, artista, duração, busca, reorganização e estado de preparação por faixa. Músicas tocadas permanecem disponíveis para retroceder; adicionar uma faixa não abre automaticamente o painel.

Efeitos oferece velocidade, Reverb, presets, manter tom e exportação. O Android renderiza o áudio pelos parâmetros escolhidos e pode preparar a próxima faixa durante a atual. Parâmetros alterados invalidam resultados incompatíveis.

Jukebox analisa conexões entre trechos, com variação, suavidade, grafo, tempo ouvido e saltos. Desligar Jukebox infinito ativa a reprodução normal; repetição e aleatório da fila controlam a ordem entre faixas. Efeitos pode permanecer ligado junto ao Jukebox. O equalizador de dez bandas atua no áudio compartilhado. Veja [Reprodução unificada](../docs/REPRODUCAO-UNIFICADA.md).

### Player compacto, expandido e sessão

A barra compacta acompanha a navegação, com capa, dados da música, letra/microfone, fila, reprodução/pausa e progresso conforme o espaço. A cor vem da capa, com aparência de vidro adaptada ao tema; sem capa válida, usa o tema.

Toque na capa/título para abrir o player expandido com capa do álbum, linha do tempo, transporte, letra, fila e menu. O volume é controlado principalmente pelo sistema e teclas físicas, sem slider na barra.

Navegar entre páginas não encerra o áudio. Efeitos e Jukebox usam a mesma seleção e uma única integração de mídia/notificação. Presets, manter tom e exportação ficam no menu de Efeitos.

Ao reabrir, a sessão recupera música, posição e filas sem iniciar áudio automaticamente. Arquivo apagado ou permissão revogada pode impedir a recuperação.

### Letras

Busca LRCLIB com escolha automática por título, artista, edição, álbum e duração, além de alternativas manuais. Letra simples/sincronizada depende da fonte; sincronização por palavra só existe quando os dados a oferecem.

O microfone abre a letra. O card Letra do player expandido abre tela cheia com título/artista, progresso e reprodução/pausa. Há animações, destaque e navegação por versos sincronizados; voltar não interrompe o áudio. As cores acompanham a capa no player.

Configurações → Áudio controla animação, exibição sincronizada e transição. A duração configurável vale somente para **prévias de músicas nas pesquisas**. Os ajustes antigos de duração de prévia de efeitos e continuidade em outras abas foram removidos.

## Imagens e carrosséis

Cards elegíveis permitem prévia antes de baixar, sem criar download ou histórico até confirmação explícita. Imagens baixadas também abrem em galeria. Há contador, setas, deslize horizontal e compartilhamento conforme a origem. O botão não é uma prévia universal de áudio/vídeo.

A ferramenta Imagens aceita arquivo/link compatível, prévia e exportação Original/JPG/PNG/WebP/SVG, com dimensões e proporção. SVG de foto incorpora raster, não vetoriza a imagem.

## Conversor e editor

Conversor individual/em lote com MP4/MKV/MOV ou MP3/M4A/AAC conforme a entrada, qualidade, bitrate, resolução/FPS, manter/remover áudio, recorte opcional de silêncio nas extremidades, progresso e cancelamento. Preserva o original.

Editar metadados abre arquivos locais ou do histórico, individualmente/em lote. Permite alterar campos selecionados, capa com recorte, letra TXT/LRC e normalização com comparação de prévias. Salva cópia por padrão; substituir exige escolha explícita e permissão de escrita.

## Configurações, ferramentas e acessibilidade

- Pesquisa de configurações indica a categoria; restauração seletiva/total e transferência JSON de preferências compatíveis.
- Nomes/estados acessíveis, ações de mover por leitor de tela e alternativas ao arraste no recorte de capa.
- Spotify opcional com PKCE; importação de cookies e Sessão do YouTube em Mais, sujeitos às regras do serviço.
- Armazenamento privado e proteção de segredos pelo Android; exportação de preferências não inclui contas, cookies ou caminhos.
- Python, FFmpeg, FFprobe e QuickJS incluídos; verificar/atualizar ferramentas dentro do app.
- Limpeza manual de cache e limpeza automática opcional de temporários antigos, com proteção de arquivos recentes e parciais.

## Atualizar o aplicativo

Consultar releases oficiais, mostrar notas/tamanho, selecionar APK da arquitetura e baixar dentro do ONDA. A transferência continua em segundo plano; é possível cancelar/descartar. Instalar atualização pede autorização e confirmação do Android após conferir pacote, versão e assinatura.

APKs separados para ARM64 e x86_64. Emulador não comprova todos os comportamentos de aparelho físico; veja os limites no relatório da release.
