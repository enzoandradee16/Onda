# Funções e validação Android

**Atualização 1.1.0:** idiomas PT/ES/EN, cards e controles da fila/Histórico e reinício pendente PC. Consulte a [validação 1.1.0](../docs/VALIDACAO-1.1.0.md). O levantamento abaixo é histórico e mantém o contexto da versão em que foi escrito.

Versão: 1.0.0-alpha.1. Este documento distingue implementação de comprovação em aparelho real. A versão Windows permanece independente.

| Área | Implementação Android | Validação atual |
|---|---|---|
| Links | Baixar agora, adicionar à fila, áudio/vídeo, qualidade, resolução, FPS, estimativa de tamanho | Downloads HTTP de foto, MP4 e extração MP3 no emulador |
| Fila | Persistência SQLite, selecionar/remover/limpar, tentar novamente, progresso, cancelar, serviço com notificação | Persistência, serviço de download e publicação verificadas; falta ensaio longo com tela apagada em aparelho real |
| Músicas | Pesquisa Deezer/Apple/Spotify, metadados, capa, escolha de catálogo/versão, correspondência automática, edição antes de baixar | Deezer, Apple/iTunes e link Spotify sem API testados online; confirmação/revisão testadas; login de conta ainda pendente |
| Redes sociais | TikTok, Instagram, Twitter/X e Kwai pelo motor compartilhado; fotos, vídeos e seleção em posts mistos; áudio por vídeo | Foto e extração de áudio de vídeo no mesmo post validadas com fixture; acessos reais sujeitos a cookies e bloqueios da plataforma |
| Playlists e álbuns | Importação por link, CSV/Exportify, TXT/M3U; busca, seleção, conferir correspondências, baixar agora/fila; opções próprias; exportar TXT/M3U; janela somente lista | Importação/exportação testadas com dados sintéticos; playlists grandes e OAuth ainda precisam teste real |
| Organização | Artista - Música; pastas de playlist original e Artista - Álbum; organização por artista/álbum; duplicados | Publicação e política de pular duplicados no MediaStore verificadas no emulador |
| Imagens | Link/arquivo, Original/JPG/PNG/WebP/SVG, dimensões, proporção, prévia | PNG/WebP/SVG e download de JPEG testados no Android; SVG de foto incorpora raster |
| Histórico | Pesquisa, abrir, compartilhar, usar em efeitos, limpar sem apagar os arquivos | Implementado; abrir/compartilhar depende dos aplicativos instalados |
| Efeitos | Slowed, Sped Up, Reverb independentes; presets; manter tom; início/duração da prévia; reprodução com busca; exportação e títulos condicionais | Renderização, prévia e preservação de artista/álbum/capa testadas com MP3 sintético |
| Aparência | Tema claro/escuro/sistema, 16 cores, ordem das abas | Navegação automatizada e inspeção visual em emulador |
| Configuração | Primeira entrada dispensável; lembrar opções; categorias; restauração geral/seletiva; duração de prévias; continuar ao trocar de aba | Implementado; credenciais cifradas e fila sem Client Secret testadas |
| Ferramentas | Python e ferramentas nativas internas; verificar ferramentas; atualização de yt-dlp com SHA-256 | FFmpeg, FFprobe e QuickJS executados no emulador |
| Integração Android | Compartilhar link para ONDA, seletor de arquivos/pasta, MediaStore, notificações, uma Activity reaproveitada | MediaStore e abertura do app testados; demais fluxos requerem aparelho real |

## Diferenças da plataforma

- Não há BAT, EXE, wizard Windows ou pasta portátil: instala-se o APK e o Android gerencia a desinstalação. A exclusão de dados fica nos controles do sistema.
- Android 10+ exporta para Downloads/ONDA por padrão. Escolher outra pasta usa o seletor do sistema. Android 8/9 precisa de pasta escolhida para manter os arquivos fora dos dados do app.
- Downloads em segundo plano usam serviço e notificação. Fabricantes, economia de bateria e limites do Android podem interromper trabalhos; a fila é preservada para tentar novamente.
- O app não transforma uma fonte com perdas em áudio lossless original de streaming. FLAC conserva a qualidade da fonte recebida.
- Cookies são importados por arquivo; não há extração automática dos cookies de outros apps. A biblioteca de impersonação curl_cffi do PC não está incorporada neste APK.
- APIs, plataformas e restrições de login continuam valendo. Não há promessa de acesso a qualquer link ou de contornar bloqueios.

## Roteiro no celular

1. Instalar o APK, abrir, fechar a configuração inicial e abrir novamente: o aviso inicial deve aparecer uma única vez.
2. Permitir notificações e escolher uma pasta em Configurações → Downloads.
3. Testar um link autorizado de vídeo em MP4 e o mesmo link em MP3; conferir o arquivo na pasta e no histórico.
4. Adicionar três itens à fila, remover um, fechar/abrir o app e conferir os pendentes. Testar cancelar e tentar novamente.
5. Pesquisar música, ouvir a prévia e baixar com capa. Conferir título, artista, álbum e arquivo Artista - Música.
6. Testar um post público somente com fotos, somente com vídeo e um misto; na escolha do misto, selecionar uma foto e áudio de um vídeo.
7. Carregar playlist/álbum, filtrar uma música, testar formatos próprios, exportar TXT/M3U e importar CSV. Verificar subpasta da coleção.
8. Em Efeitos, selecionar MP3 com tags/capa, testar velocidade 90%, 120%, reverb isolado e manter tom. Ouvir, buscar na prévia e exportar; conferir os títulos e a capa.
9. Trocar tema/cor/ordem das abas, reiniciar e conferir persistência. Testar restauração seletiva.
10. Testar download com tela apagada e uso prolongado no aparelho real. Relatar modelo, Android e log sem cookies/segredos.

Antes de publicar como release Android, concluir assinatura definitiva, testes ARM64 reais e revisão dos componentes nativos descrita nos avisos de terceiros.

## Auditoria de paridade

Veja [PARIDADE-PC-ANDROID.md](PARIDADE-PC-ANDROID.md) para as lacunas identificadas. A existência de funções nesta tabela não significa equivalência integral com o PC.


### Fonte da interface

Em Configurações → Aparência → Fonte da interface, escolha Padrão do sistema, Sem serifa, Serifada, Monoespaçada, Condensada, Cursiva ou Arredondada. A prévia e a interface mudam imediatamente. Ative Lembrar configurações para manter a escolha ao reabrir; restaurar Aparência também restaura a fonte. Esta versão usa fontes nativas do Android, sem baixar arquivos de fontes.


### Enter nos campos

Em Pesquisar músicas, Enter do teclado físico ou a ação Pesquisar do teclado virtual inicia a busca, sem inserir uma linha. Os demais campos são de uma linha. Somente o campo LINKS em Links e fila aceita Enter para separar os links.
