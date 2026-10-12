# Comparação PC × Android — 12/10/2026

Revisão de código da versão Android 1.0.0-alpha.4 e do PC presente na mesma pasta. Ter o motor Python compartilhado não significa que todos os controles ou fluxos do PC tenham sido portados. Este relatório separa recursos existentes, lacunas de interface e validação pendente.

## Alteração desta versão

Histórico agora oferece **Usar em efeitos** para arquivos de áudio e formatos de vídeo reconhecidos. O app importa o arquivo publicado (inclusive URI de Downloads/SAF) em segundo plano, preserva seus bytes e abre Slowed / Sped Up com o arquivo carregado. Fotos não exibem esse botão. Se o arquivo foi removido ou perdeu permissão, a importação informa o erro. Os cartões ocupam a largura disponível.

## Lacunas identificadas

| Recurso do PC | Situação no Android |
|---|---|
| Janela Metadados: consultar vários links sem baixar, detalhes completos, abrir fonte/capa, exportar JSON | Falta a área independente. Pesquisa e revisão antes de baixar já consultam/alteram metadados; isso não equivale ao fluxo avulso do PC. |
| Pesquisa: janela por música com formato/qualidade próprios, presets MP3 320/128 e estimativa antes de adicionar | Falta. Os botões da pesquisa usam as opções gerais de Links e fila. A estimativa chega durante o processamento do download, não nessa janela prévia. |
| Pesquisa: Ver no catálogo | Falta o atalho. Título/artista/álbum/capa, duração em minutos e prévia já existem. |
| Efeitos: ajustar sliders durante a prévia e regenerar automaticamente o trecho | Implementado na alpha.7: enquanto a prévia de efeitos está habilitada, velocidade, reverb, pitch e posição regeneram o trecho com intervalo de 300 ms, descartando resultados antigos e preservando a posição de origem durante a reprodução. |
| Efeitos: Cancelar exportação na própria área | Não há botão local equivalente. A exportação vira item da fila; é interrompida em Links e fila ou pela notificação. |
| Álbuns/playlists: confirmar versão por coleção e conectar Spotify nessa própria tela | A confirmação e a conexão existem nas configurações; faltam os controles locais da coleção. |
| Histórico: data/hora do download | Falta. A tabela Android guarda título, URI, formato e tamanho; ainda não registra data/hora. |
| Histórico: confirmar antes de limpar registros | Falta a confirmação. Limpar histórico mantém os arquivos, mas apaga registros imediatamente. |
| Configurações de correspondência automática aplicadas a itens já enfileirados | Diferença: o PC consulta a preferência atual ao iniciar; o Android usa a cópia das opções salva no item da fila. |
| Links: formato explícito Fotos · todas do carrossel | A seleção direta desse formato falta em Links; o Android oferece a área Imagens e o modo automático de fotos/vídeos. |
| Redes sociais: impersonação de navegador com curl_cffi | Não incorporada no Android. Motor social e cookies existem, mas essa dependência do PC não acompanha o APK. |
| Ajuda integrada com orientações do PC | Falta área equivalente no Android. Há README e mensagens contextuais. |

## Funções presentes nos dois

| Área | Já implementado no Android | Limites de validação |
|---|---|---|
| Links | Baixar agora/fila, MP3/M4A/FLAC/original, MP4/MKV, bitrate, resolução, FPS e estimativa durante processamento | YouTube continua sujeito à verificação; HTTP local foi validado. |
| Fila | Persistir pendentes, selecionar tudo/ALT+A, remover/limpar, tentar novamente, progresso, parar | Inclusão em lote fora da thread principal. Ensaios prolongados de bateria/segundo plano ainda pendentes. |
| Metadados | Catálogos Deezer/Apple/Spotify, API opcional em links individuais, edição de título/artista/álbum/data/gênero/faixa/disco/capa, correspondência e escolha de versão | Catálogos públicos e links Spotify testados; login de conta depende de validação real. |
| Álbuns/playlists | Links, CSV/Exportify, TXT/M3U, filtro, seleção, somente lista, conferir correspondências, formatos próprios, baixar agora/fila, exportar TXT/M3U | Playlists grandes/OAuth requerem teste real. |
| Organização | Artista - Música, pasta da playlist, Artista - Álbum, artista/álbum, políticas de duplicados | Publicação por MediaStore/SAF substitui caminhos Windows. |
| Redes e mídia mista | Instagram/TikTok/X/Kwai, fotos/vídeos, seleção por item e áudio do vídeo | Testes sintéticos não comprovam acesso a posts reais. |
| Imagens | Original/JPG/PNG/WebP/SVG, tamanho, proporção, prévia e imagem local | SVG incorpora raster; conversões verificadas com fixtures. |
| Efeitos | Slowed/Sped Up/Reverb, presets do PC, pitch, trecho/duração, ouvir original/com efeitos, reprodução, exportar com sufixo e tags/capa preservadas | Tags/capa/renderização verificadas com MP3 sintético. |
| Aparência/configuração | Claro/escuro/sistema, 16 cores, ordem, lembrar, restaurar geral/seletivo, categorias, primeira entrada, duração de prévias/continuar em outra área | Estado preservado entre áreas; configurações e navegação testadas no emulador. |
| Ferramentas | FFmpeg/FFprobe/QuickJS, verificar ferramentas e atualizar yt-dlp com hash | Android aplica atualização após encerramento completo do processo. |

## Adaptações específicas do Android

APK e desinstalação pelo sistema substituem portátil/instalador Windows. Ferramentas nativas vêm no APK; não existe seleção de ffmpeg.exe externo. O compartilhamento e os seletores do Android substituem os caminhos do Explorer. Abrir pasta não tem atalho equivalente garantido para todos os provedores SAF; abrir/compartilhar arquivos está disponível. O menu lateral substitui as abas arrastáveis: a ordem pode ser alterada nas configurações. Reaproveitar a Activity substitui o aviso Windows de segunda instância.

## Recursos presentes, mas sem comprovação completa

- YouTube com sessão real: a conexão de teste exigiu verificação; salvar cookies não comprova desbloqueio.
- OAuth Spotify, coleções completas de conta e comportamento em aparelho ARM64 real.
- Acesso atual a posts reais de todas as redes, especialmente login e bloqueio por IP.
- Segundo plano prolongado, fabricantes com restrições de bateria e interrupções do sistema.

Fontes da revisão: `../Onda/history_ui.py`, `catalog_ui.py`, `metadata_ui.py`, `playlist_ui.py`, `images_ui.py`, `effects_ui.py`, `ui.py`, `app.py`; `app/src/main/java/br/com/onda/mobile/` e `app/src/main/python/mobile_backend.py`.

## Alpha.4

Pesquisa ganhou fila filtrada pelos itens criados nessa área, persistente e ligada ao mesmo serviço de download (sem duplicar trabalho), com progresso, estados, iniciar, tentar novamente e limpar. Itens antigos sem identificação de origem continuam na fila geral. Os tempos dos efeitos/player/resultados são exibidos em minutos:segundos. Configurações inclui Spotify Developers e validação local de Client ID. Resultados/erros das operações iniciadas pelas configurações e falhas de prévia/importação em janelas usam aviso modal acima dos painéis; operações da tela principal mantêm o status no topo.


## Alpha.7

Histórico possui Remover por registro, preservando o arquivo publicado e os demais registros. Configurações usa painel com cantos de 28 dp e páginas deslizantes; tocar na categoria ou deslizar o conteúdo sincroniza a categoria selecionada. A prévia dos efeitos regenera automaticamente ao alterar velocidade, reverb, pitch ou posição após Ouvir com efeitos. Há um intervalo de 300 ms, uma renderização por vez, cancelamento das substituídas e arquivos temporários distintos. Parar e Ouvir original desativam essa atualização. Não é processamento de áudio instantâneo: o trecho é renderizado localmente antes da troca.


## Alpha.8

Textos das funções equivalentes padronizados com a interface de PC: navegação, busca/prévia, formatos/resoluções, imagens, histórico, seleção de versões/metadados, revisão e configurações. Configurações agrupa Geral, Aparência, Downloads, Imagens, Áudio, Contas e Ferramentas; Imagens permanece como categoria adicional do Android. As 16 cores têm nomes e tons claros/escuros iguais aos do PC; Menta e outras denominações antigas são migradas para seus nomes atuais. Verde-Água é o padrão em ambas as versões, e Sistema passa a Seguir o sistema. A migração preserva os demais valores.

O portátil de PC recebeu a mesma função callback_page do motor Android, e Onda-Setup.exe foi recompilado. O visual é compartilhado; o retorno Android usa onda://spotify-return, e PC oferece Fechar esta aba. A tentativa de fechamento após três segundos permanece sujeita às permissões do navegador. Os testes locais verificam estado/PKCE e o HTML, sem uma autorização real de conta Spotify.

Instruções exclusivas de armazenamento, permissões, compartilhamento e ferramentas Android são mantidas, pois descrevem comportamentos diferentes do PC. Auditoria de textos e paleta em validation/TEXTOS-PC-ANDROID.json.


## Alpha.9

Escolha Fonte da interface em Aparência, com a mesma legenda e texto de prévia nas duas versões. Android aplica a família a todos os 15 estilos Material, inclusive painéis, menus e avisos, e usa sete opções nativas. PC oferece essas categorias e fontes instaladas no Windows; preserva tamanho, peso e estilo em widgets e texto de canvas, além de atualizar estilos ttk e janelas abertas posteriormente. Padrão do sistema restaura a tipografia original; fontes ausentes no PC usam uma alternativa disponível. Preferência incluída em salvamento e restauração seletiva de Aparência. Não altera metadados nem os arquivos de mídia.


## Alpha.10

Enter na pesquisa inicia a busca no Android (teclado físico/numérico ou ação Pesquisar do teclado virtual) e no PC (Return/KP_Enter). A busca usa o mesmo fluxo do botão. Pressionar Enter durante uma busca não cancela a consulta; Android também ignora repetições de tecla mantida pressionada. Os campos Android são de uma linha, exceto LINKS em Links e fila, que preserva a entrada de várias linhas. A consulta avulsa de metadados do PC também usa Enter para consultar, preservando a possibilidade de colar vários links de uma vez.
