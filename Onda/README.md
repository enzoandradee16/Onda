# Onda — vídeo e áudio

## Windows: portátil ou instalação completa

- **Onda.exe**: abre sem instalar Python ou ferramentas.
  Mantenha a pasta `_runtime` e a pasta `Onda` junto do executável.
- **Onda-Setup.exe**: abre o assistente de instalação
  para Windows, com atalhos, registro em Aplicativos instalados e desinstalador.
  A instalação usa `%LOCALAPPDATA%\Programs\Onda`, sem exigir administrador.
- **Instalação Silenciosa Onda.bat**: instalação rápida e silenciosa no local padrão,
  com atalhos, sem abrir o assistente nem iniciar o app ao terminar. O BAT e `Onda-Setup.exe` ficam juntos em `Instalador`. Não reinicia o PC. Em caso de falha,
  consulte `%TEMP%\Onda-instalacao.log`.
- Python, FFmpeg/ffprobe/ffplay, Node e bibliotecas já vêm no pacote. Internet
  é necessária para buscar/baixar conteúdo e atualizar o yt-dlp.
- Downloads novos ficam em `Downloads\Onda`, respeitando uma pasta salva nas
  preferências. Desinstalar não remove músicas nem os dados em `%LOCALAPPDATA%\Onda`.

As instruções de ambiente virtual mais abaixo se destinam ao desenvolvimento
a partir do código-fonte. Para gerar novos pacotes, veja `empacotamento`.

Aplicativo Python com interface Tkinter em português, tema escuro, fila de links,
barra de progresso, velocidade, estimativa de tempo, cancelamento, nova tentativa
e seleção de pasta. Usa yt-dlp para obter mídia e FFmpeg para processá-la.

## Revisar, ouvir e organizar

**Revisar metadados antes de baixar** fica em Links e fila e Configurações,
desativado por padrão. A escolha vale para os próximos itens adicionados.
Quando ativado, mostra título, artistas (separados por `;`), álbum, data,
gênero, faixa e disco. É possível trocar a capa por uma URL HTTPS ou JPEG/PNG
local de até 10 MB, com prévia. A imagem inteira é preservada. **Confirmar e
baixar** aplica as mudanças às tags e ao nome do arquivo. O áudio escolhido
continua o mesmo. Funciona com MP3/M4A/FLAC de catálogos e links diretos.

Na escolha de versão do YouTube, use **Ouvir / parar prévia** antes de confirmar.
A revisão de metadados também permite ouvir o áudio escolhido. É um trecho de
até 25 segundos da fonte YouTube, independente da prévia curta do catálogo.
Requer `ffplay`; a prévia pode ficar indisponível se a fonte recusar o acesso.

Em **Configurações → Organizar músicas em**, escolha Catálogo (padrão anterior),
Pasta de destino, Artista, ou Artista / Álbum. O arquivo usa `Artista - Música.ext`.
Quando houver um arquivo com o mesmo nome e extensão na pasta final, o padrão
é perguntar: **Ignorar novo**, **Substituir existente**, ou **Manter ambos**.
Manter ambos cria nomes com `(2)`, `(3)`… Esta detecção é por caminho/nome,
não por reconhecimento de áudio ou busca em todas as pastas do computador.
O aviso aparece depois do processamento, antes de publicar a nova cópia.

## Histórico e fila restaurada

**Histórico** permite pesquisar pelo nome, abrir o arquivo/pasta e enviá-lo
para Slowed + Reverb. Só registra downloads/exportações concluídos nesta versão;
não examina automaticamente os arquivos antigos. Limpar o histórico preserva
os arquivos. Arquivos movidos ou apagados são indicados como indisponíveis.

A fila pendente é salva automaticamente em `%LOCALAPPDATA%\Onda\library.sqlite3`,
junto do histórico. Downloads interrompidos voltam a Na fila; erros/cancelamentos
anteriores continuam disponíveis para Tentar novamente. Ao abrir, a fila fica
pausada: clique em **Baixar fila**. Credenciais não são copiadas para essa base.
O armazenamento da fila/histórico é independente de Lembrar configurações.
Arquivos intermediários ficam em `.onda-work`, na pasta de saída, para permitir
retomada quando a fonte suportar; o cancelamento não apaga partes pendentes.

## Playlists

Na aba **Playlists**, cole uma playlist pública Deezer, Spotify ou YouTube e
clique em **Carregar playlist**. Também aceita TXT/M3U/M3U8 UTF-8 contendo
links individuais, um por linha. O limite atual é 100 itens por importação.
Selecione com Ctrl/Shift ou Selecionar todas. **Conferir correspondências**
consulta o catálogo e YouTube sem baixar o áudio; versões incertas aparecem
como Escolha necessária ao baixar. **Adicionar selecionadas** usa o formato
atual de Links e fila. A versão pode ser confirmada individualmente ao baixar.

No Spotify, a importação usa o embed público e não exige API. Esse embed pode
listar só parte da playlist ou retornar erro; o app mostra a limitação, sem
afirmar que a lista está completa. Playlists privadas, episódios, arquivos locais
e playlists Apple Music não são importados por URL. Como alternativa, use um
TXT com links individuais suportados. A consulta das correspondências é refeita
ao baixar; o resultado prévio não garante disponibilidade futura. Uma playlist
Deezer real foi consultada com sucesso (50 faixas, sem baixar músicas).

## Slowed / Sped Up e Reverb

1. Abra a aba e clique em **Abrir áudio**, ou selecione um arquivo no Histórico
   e clique em **Usar nos efeitos**.
2. **Velocidade** vai de 50 a 150%. Em 100%, no centro, não altera tempo/tom;
   abaixo disso fica mais lento e grave (Slowed), acima fica mais rápido e agudo
   (Sped Up). **Reverb** vai de 0 a 100%; zero desativa o efeito.
   Os controles são independentes, inclusive para usar só velocidade ou só reverb.
   O menu **Preset** oferece Original (100%/0%), Slowed leve (90%/0%),
   Slowed intenso (75%/0%), Sped Up leve (115%/0%), Sped Up intenso (130%/0%),
   Sped Up + Reverb (120%/25%), Só Reverb (100%/30%), Clássico (85%/25%) e
   Atmosférico (75%/50%). Ajustar os sliders fora dessas combinações indica
   **Personalizado**. Trocar de preset também funciona durante a prévia.
3. Clique ou arraste a **barra de reprodução** para escolher o trecho e compare
   **Ouvir original** e **Ouvir com efeitos**. O contador mostra a posição atual
   e a duração da música original, acompanhando a velocidade selecionada.
   Ao soltar a barra durante a reprodução, a prévia continua no ponto escolhido;
   quando parada, a barra apenas escolhe o próximo início. As setas esquerda/direita
   avançam ou voltam cinco segundos com a barra selecionada.
   A duração da prévia é configurável; ajustar os efeitos mantém a posição atual.
   **Parar** conserva a posição para continuar ao clicar em Ouvir novamente.
4. **Exportar música inteira** salva uma nova cópia em MP3, M4A, FLAC ou WAV.
   MP3/M4A usam o bitrate escolhido nas configurações atuais. O original não
   pode ser escolhido como saída. Há progresso e cancelamento. Tags e capa são
   copiadas quando o formato suporta; WAV pode ter suporte limitado a metadados.
   O nome sugerido do arquivo e a tag de título recebem ** - Slowed + Reverb**
   quando ambos os efeitos estão ativos, ** - Slowed** com reverb em zero ou
   ** - Reverb** com velocidade em 100%. Acima de 100%, recebem ** - Sped Up**
   ou ** - Sped Up + Reverb**, conforme o reverb esteja desligado ou ativo.
   Com ambos desligados, o título e o nome
   sugerido ficam iguais aos originais. Você precisa escolher outro arquivo para
   salvar a cópia. Artista, álbum, capa e demais tags são mantidos; exportações no
   mesmo formato preservam também as tags nativas personalizadas.

O reverb usa reflexões múltiplas com decaimento, implementadas com `aecho` e
limitador do FFmpeg; Slowed e Sped Up usam mudança da taxa de amostragem. A prévia e a
exportação usam os mesmos filtros. Não é um plugin de reverberação por convolução.
Veja os filtros [asetrate](https://ffmpeg.org/ffmpeg-filters.html#asetrate) e
[aecho](https://ffmpeg.org/ffmpeg-filters.html#aecho).

## Atualizar ferramenta de download

Em **Configurações**, clique em **Atualizar ferramenta de download (yt-dlp)**.
O app atualiza `yt-dlp[default]` pelo pip do mesmo Python que está executando
o Onda, incluindo o componente JavaScript compatível. Não atualiza FFmpeg,
Node ou Deno. Aguarde downloads/exportações/consultas terminarem antes de
atualizar e aguarde a atualização terminar antes de fechar o app. As mensagens
ficam em Ver detalhes. Os próximos workers usarão a versão instalada.

## Pesquisar → escolher a música → baixar

A aba inicial **Pesquisar músicas** segue o fluxo analisado em
[Flac Downloader](https://flacdownloader.com/pt): pesquisar artista/música,
conferir as versões nos resultados, ouvir uma prévia e escolher o formato.

1. Digite o nome da música ou artista e clique em **Pesquisar** (ou Enter).
   Escolha **Deezer** ou **Apple / iTunes** para a busca de catálogo. Não é
   necessário informar credenciais para esses dois catálogos.
2. Selecione um resultado. Aparecem título, artista, álbum, duração e capa.
   **Ouvir prévia** usa a duração escolhida nas configurações, quando o catálogo fornece uma
   amostra HTTPS e o FFmpeg inclui `ffplay`. A prévia para ao mudar de faixa,
   abrir a escolha de formato, trocar de aba ou fechar o app.
3. Clique em **Baixar…** (ou dê dois cliques na linha). Escolha **MP3 320**,
   **MP3 128**, **FLAC**, ou **Personalizar** para outros bitrates MP3/M4A.
   A janela mostra uma estimativa para MP3/M4A antes de adicionar à fila.
4. Use **Baixar agora** ou **Adicionar à fila**. Se houver uma fila em execução,
   a nova música aguarda sua vez. Acompanhe os downloads na aba **Links e fila**.

O campo de pesquisa também aceita links individuais do Deezer, Spotify e Apple.
Links de vídeo são encaminhados à aba de links, que mantém formato, resolução,
FPS e playlist. O botão de pesquisa vira **Cancelar** durante a consulta;
resultados de consultas canceladas são descartados.

A busca não usa o servidor do site de referência: consulta os catálogos públicos.
O áudio completo continua vindo do YouTube, com seleção de versão e aplicação
dos metadados/capa. **FLAC é conversão da fonte disponível, sem garantia de
lossless original.** Qobuz e Tidal não foram integrados. Em catálogos indisponíveis,
o erro aparece na tela; use o outro catálogo ou tente novamente.

## Automático: link de streaming → YouTube → áudio com tags

Na aba **Links e fila**, cole o link de uma **música** do Deezer, Spotify ou Apple Music,
escolha MP3, M4A ou FLAC, clique em **Adicionar à fila** e em **Baixar fila**.
O programa consulta os metadados, busca até oito candidatos no YouTube, seleciona
uma versão compatível, obtém a capa, baixa o áudio e grava as tags antes de
marcar o item como concluído. Não abre mais a janela Metadados ao adicionar.

**A API Spotify é opcional para baixar por link.** Sem Client ID/Client Secret,
o Onda usa a página pública do Spotify para identificar título, artista e duração,
procura a faixa correspondente no Deezer e, se não houver correspondência ou o
serviço estiver indisponível, tenta Apple/iTunes. Os metadados e a capa vêm
inteiramente da faixa selecionada nesse catálogo, sem combinar campos de álbuns
ou plataformas diferentes. O áudio completo continua vindo do YouTube.

A correspondência compara título, artista, versão e duração; ISRC tem prioridade
quando está disponível nas duas fontes. Resultados semelhantes, lançamentos
diferentes ou dados públicos insuficientes abrem **Confirme os metadados**:
confira título, artista, álbum e duração e clique em **Usar estes metadados**.
Essa escolha acontece antes da eventual escolha de versão no YouTube.
Se só for possível obter o título pelo oEmbed, o Onda exige escolha manual do
catálogo. Se não houver candidato compatível, orienta a pesquisar pelo nome.
A estrutura da página pública Spotify pode mudar ou ficar indisponível.

Com credenciais Spotify válidas, o Onda continua usando os metadados diretamente
da API Spotify. Credenciais incompletas ou recusadas não impedem a tentativa
pública nos fluxos de pesquisa e download; a origem efetiva aparece no resultado
e nos detalhes da fila. A consulta avulsa **Metadados** mantém a consulta direta
ao provedor e mostra erros de autenticação dessa consulta.

Para usar a API opcional, abra **Metadados**, preencha **Client ID/Client Secret**
e clique em **Salvar neste computador**. Os campos voltam preenchidos ao reabrir;
sem Salvar, alterações ficam apenas na sessão. Apple usa o catálogo público
iTunes da região do link, sem credenciais.

A seleção compara palavras do título/artista e duração, quando fornecida.
Rejeita diferenças reconhecidas de versão (live, cover, remix, instrumental,
karaokê, sped/slowed etc.) e duração incompatível. Quando há resultados semelhantes,
a fila aguarda a escolha em uma janela com título, canal, duração e similaridade.
Selecione uma linha e clique em **Baixar esta versão**; **Abrir no YouTube** permite
conferir antes. Fechar ou cancelar essa janela cancela o item e para a fila.
A escolha manual também fica registrada nos metadados de origem. Isso é
uma **heurística**, não reconhecimento de áudio nem garantia da mesma gravação
ou masterização. Quando não encontra correspondência confiável, o item falha
com uma explicação; outros links da fila continuam normalmente.

Grava os campos disponíveis em tags ID3 (MP3), MP4 (M4A) ou Vorbis (FLAC), incluindo
título, artistas, álbum, artista do álbum, data, faixa/disco, gênero, ISRC e capa
quando o provedor os fornece. A indicação de explícita e a origem também são
registradas. Campos ausentes não são inventados. O registro completo do catálogo
e a origem do áudio ficam em uma tag própria `ONDA_METADATA` e no arquivo
`*.metadata.json` ao lado do áudio. A duração real continua sendo a do áudio.
Quando o link de entrada é Spotify e os metadados vêm de outro catálogo, o
registro preserva `requested_source_url`, a faixa efetivamente usada e o modo
de correspondência (automático ou escolhido pelo usuário). Uma escolha feita
na pesquisa acompanha o item na fila e é conferida novamente ao baixar.

Os arquivos ficam em subpastas `deezer-ID`, `spotify-ID` ou `apple-ID` no destino escolhido,
evitando misturar lançamentos que apontem para o mesmo vídeo. A edição das tags
usa cópia temporária e substitui o arquivo só depois da gravação bem-sucedida.
Se falhar a capa ou a gravação, o item não aparece como concluído.

Se estiver selecionado **Vídeo**, links de streaming usam **MP3**; se estiver
selecionado **Original**, usam **M4A** para comportar tags/capa. O formato efetivo
aparece na fila. Essa automação aceita faixas individuais, não álbuns/playlists
de streaming. Links diretos do YouTube mantêm o comportamento anterior.
O áudio vem do YouTube e não é Apple/Spotify Lossless; exportar FLAC não recupera
qualidade perdida. Use o download para conteúdo que você tenha autorização de baixar.

## Consulta avulsa de metadados

Clique em **Metadados** no topo da janela, cole links de músicas (um por linha)
e use **Consultar metadados**. Essa janela permite inspecionar informações
separadamente da automação da fila.
Selecione um resultado para ver seus detalhes, abrir a página oficial ou abrir
o link da capa. **Exportar JSON** salva todos os resultados válidos da consulta,
incluindo a origem dos dados e o link para a plataforma.

| Fonte | Campos disponíveis |
| --- | --- |
| Deezer público, sem credenciais | Título, artistas, álbum, duração, data, faixa/disco, ISRC, indicação de explícita e capa, quando disponíveis; prévia nos resultados de busca |
| Spotify público, sem credenciais | Título e URL da capa, pelo oEmbed |
| Spotify Web API, com credenciais | Título, artistas, álbum, artistas do álbum, lançamento, duração, número da faixa/disco, indicação de explícita, ISRC e URL da capa, quando fornecidos |
| Apple Music/iTunes, sem credenciais | Título, artista, álbum, lançamento, duração, gênero, número da faixa/disco, indicação de explícita e URL da capa, quando presentes no catálogo iTunes da região |

Para os campos adicionais do Spotify, crie/configure seu aplicativo no
[Spotify Developer Dashboard](https://developer.spotify.com/dashboard) e informe
**Client ID** e **Client Secret** na janela. Essas credenciais são do seu app,
não sua senha do Spotify. Também são aceitas as variáveis `SPOTIFY_CLIENT_ID` e
`SPOTIFY_CLIENT_SECRET`. O fluxo Client Credentials obtém o token automaticamente;
o token fica somente na sessão e nenhum segredo entra no JSON exportado.
O acesso depende da disponibilidade e das regras da API para o aplicativo.
Na consulta avulsa, um erro de autenticação é mostrado. Na pesquisa e no download,
o Onda pode usar identificação pública e Deezer/Apple, indicando a fonte usada.

### Lembrar as credenciais

No Windows, **Salvar neste computador** protege Client ID e Client Secret com
DPAPI, vinculada à conta do Windows, e grava apenas o conteúdo criptografado em
`%LOCALAPPDATA%\Onda\spotify.dpapi`. Não grava o segredo em texto puro, no código,
no ZIP ou nos metadados de áudio. Não requer uma dependência Python adicional.
O salvamento local não valida o acesso à API; a validação ocorre ao consultar.

Use **Esquecer credenciais** para excluir o arquivo salvo e limpar os campos
da sessão. Downloads já iniciados podem concluir usando a cópia que receberam
ao iniciar. Variáveis de ambiente têm prioridade sobre o arquivo salvo; se
estiverem configuradas, precisam ser removidas separadamente para não voltarem
a preencher os campos na próxima abertura.

As credenciais não são portáteis para outra conta do Windows. Se a leitura falhar,
o Onda continua abrindo e pede para informar/salvar novamente. Em outros sistemas,
os campos continuam disponíveis por sessão, mas não há fallback para armazenamento
em texto puro. Informações sobre DPAPI:
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

São aceitos links `open.spotify.com/track/ID`, links regionais `intl-...`,
URIs `spotify:track:ID` e links curtos `spotify.link` resolvidos para uma faixa.
Na Apple, use o link individual `/song/.../ID` ou o link de álbum com `?i=ID` da
música. Links apenas de álbuns, artistas e playlists não são expandidos nesta
consulta. Cada lote aceita até 100 links e continua após erros individuais.
Deezer aceita `deezer.com/track/ID` e `deezer.com/br/track/ID`, com ou sem `www`.
Links curtos são resolvidos somente entre domínios Deezer permitidos; se não
resolverem, copie o link completo da faixa.

Os IDs de streaming são consultados diretamente para os metadados; não há
mistura de campos de catálogo entre plataformas. A API pública da Apple consulta o iTunes:
algumas músicas exclusivas do catálogo Apple Music podem não aparecer. Campos
ausentes são `null` ou listas vazias no JSON e “Não informado” na interface.
Não são inferidos ISRC, artista, qualidade lossless ou outros campos ausentes.
A consulta roda em segundo plano e não precisa de FFmpeg/Deno; cancelar impede
as próximas requisições e aguarda a chamada em curso encerrar (timeout de rede).
Nessa janela avulsa, consultar/exportar não modifica arquivos de áudio existentes.

## Interface simplificada

Em **Configurações**, marque **Lembrar configurações** para salvar automaticamente
formato, resolução, FPS, catálogo de pesquisa, qualidade de MP3/M4A, pasta de destino, opção de playlist, caminho do FFmpeg, revisão, organização de pastas e política de duplicados.
As escolhas são restauradas na próxima abertura. Ao desmarcar, as preferências
salvas são removidas; as escolhas atuais continuam valendo nesta sessão e a próxima
abertura usa os padrões. A opção começa desmarcada na primeira utilização.
Os dados ficam em `%LOCALAPPDATA%\Onda\settings.json` no Windows. Esse arquivo
não inclui links nem credenciais Spotify. Fila/histórico usam `library.sqlite3`;
credenciais continuam no armazenamento protegido separado. Desmarcar não apaga
a fila, o histórico nem as credenciais do Spotify.

A tela principal reúne links, formato, fila e progresso. Use **Adicionar à fila**
e depois **Baixar fila**. **Configurações** contém pasta de destino, playlist e FFmpeg.
A resolução e a qualidade ficam na tela principal, ao lado do formato. A ajuda também fica nessa janela. **Ver detalhes** abre o
registro completo dos downloads; **Parar** cancela o item atual e interrompe a fila.
Os estados concluído, erro e cancelado têm cores distintas. **Metadados** continua
no topo para consulta avulsa e configuração das credenciais Spotify.

O layout foi verificado em 980×780 e 840×720, incluindo os controles inferiores,
a fila vazia e as janelas de configurações e detalhes.

## Instalar no Windows

1. Instale **Python 3.10 ou superior**, com Tcl/Tk e o launcher `py`.
   Download: https://www.python.org/downloads/
2. Extraia esta pasta e execute **instalar.bat**. Ele cria um ambiente `.venv`
   nesta pasta e instala os pacotes de `requirements.txt`. Precisa de internet.
3. Instale **FFmpeg**, incluindo **ffprobe**, usando os links de Windows em
   https://ffmpeg.org/download.html . Extraia o pacote e, no Onda, selecione a
   pasta `bin` que contém os dois executáveis. Também pode adicioná-la ao PATH.
4. Para o YouTube, instale **Deno**, seguindo
   https://docs.deno.com/runtime/getting_started/installation/ .
   Node.js compatível com yt-dlp também é aceito se já estiver no PATH.
   Feche e reabra o aplicativo depois de alterar o PATH.
5. Execute **iniciar.bat**.

O pacote contém o código-fonte; não é um executável autônomo. As ferramentas
FFmpeg/Deno não estão incluídas. Nenhuma configuração do sistema é alterada
pelos scripts de instalação deste projeto.

Instalação manual (terminal nesta pasta):

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -U -r requirements.txt
.venv\Scripts\python.exe app.py
```

Linux/macOS: use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r
requirements.txt` e `.venv/bin/python app.py`. Instale Tkinter, FFmpeg e Deno pelo
seu sistema. O desenvolvimento e a validação deste projeto foram no Windows.

## Como usar

Cole links HTTP/HTTPS, um por linha. Escolha o formato na tela principal. Ao selecionar vídeo, aparece somente
**Resolução**; ao selecionar MP3/M4A, aparece **Qualidade** (bitrate). FLAC e áudio
original mostram qualidade fixa, sem bitrate artificial. Em **Configurações**,
defina a pasta e se deseja baixar a playlist. Clique em **Adicionar à fila**, depois em **Baixar fila**.
Formato, qualidade, resolução, destino e opção de playlist ficam associados ao item ao
adicioná-lo; mudanças posteriores se aplicam aos novos itens. A pasta do FFmpeg
é consultada ao iniciar cada item.

| Opção | Resultado |
| --- | --- |
| Vídeo | Melhor vídeo e áudio disponíveis dentro do limite escolhido, em MKV, sem recodificação |
| Áudio original | Fluxo de áudio disponível, sem converter nem alterar seus bytes; exige uma faixa só de áudio |
| MP3 | 96, 128, 192, 256 ou 320 kbps; padrão 320 kbps |
| M4A | AAC a 96, 128, 192 ou 256 kbps; padrão 256 kbps |
| FLAC | Arquivo FLAC; a qualidade continua limitada à fonte |

MP3/M4A são codificados na taxa escolhida, mesmo se a fonte já usar esse codec.
AAC usa taxa média, que pode variar com o conteúdo. Os nomes incluem o bitrate
para não confundir downloads feitos em qualidades diferentes. Aumentar o bitrate
não recupera detalhes ausentes na fonte.

MKV foi escolhido para acomodar os codecs modernos sem perda por recodificação.
A resolução é um teto, não uma promessa: pode ser inferior quando a fonte não
oferece a qualidade selecionada. Fontes que não informam altura também são aceitas.

**FLAC não transforma uma fonte com perdas em lossless de estúdio.** Para
preservar um FLAC/WAV já disponível por link direto, escolha Áudio original.
Se não houver faixa separada, escolha um formato de conversão.

A barra mede a transferência atual. Vídeo e áudio podem ser baixados separados,
reiniciando a barra em cada etapa. Na conversão e quando o tamanho é desconhecido,
a barra fica animada. O estado **Concluído** só aparece depois do processamento.

**Parar** interrompe o processo e seus subprocessos. Os
próximos itens aguardam. Selecione um item cancelado/com erro, clique em **Tentar
novamente** e inicie a fila. Arquivos `.part` são mantidos para retomada quando a
fonte permite; conversões interrompidas podem precisar reiniciar. Não existe
pausa garantida nem retomada de todos os protocolos.

Links duplicados pendentes com as mesmas opções são ignorados. A fila é apenas
da sessão, não persiste ao fechar. Fechar a janela cancela o trabalho em curso.
Downloads concluídos continuam na pasta. **Abrir pasta** usa o destino do item
selecionado; sem seleção, usa o campo Salvar em.

## Plataformas e limites

- **YouTube e demais extratores yt-dlp:** depende de disponibilidade pública,
  região, alterações do site e dos formatos oferecidos. Não há garantia de
  funcionamento em todos os sites listados pelo yt-dlp.
- **Spotify e Apple Music:** este aplicativo consulta e exporta metadados, mas
  não baixa/exporta o áudio do catálogo desses serviços. Links de músicas na fila
  acionam a busca correspondente no YouTube. O modo offline do serviço não equivale a exportar MP3/FLAC.
  Não há descriptografia de DRM, captura de stream protegido, login nesses
  serviços. A origem YouTube é mostrada no registro e gravada nos metadados do arquivo.
- Apple Music Lossless deve ser configurado e usado no aplicativo oficial.
- Playlists precisam ser habilitadas e têm limite de **100 entradas por link**.
  Sem essa opção, links de vídeo com playlist baixam só o vídeo; uma URL que seja
  apenas playlist pode baixar a primeira entrada. Uma falha interrompe esse link;
  arquivos já concluídos permanecem salvos. Outros links da fila continuam.
- Lives e estreias futuras não são suportadas. Não há interface de cookies ou
  autenticação para conteúdo privado, premium ou com verificação de idade.
- Use para conteúdo seu ou cujo download você tenha autorização.

## Se algo falhar

- **FFmpeg não encontrado:** selecione a pasta que contém tanto `ffmpeg.exe`
  quanto `ffprobe.exe`. Instalar o pacote Python chamado ffmpeg não substitui os
  executáveis.
- **YouTube sem formatos / erro de extração:** execute novamente `instalar.bat`
  para atualizar yt-dlp e confira Deno no PATH. Restrições do serviço podem
  impedir o download mesmo com tudo instalado.
- **Sem áudio original:** a fonte pode não expor uma faixa exclusivamente de
  áudio. MP3/M4A/FLAC também conseguem extrair áudio de um arquivo de vídeo.
- **Erro de acesso à pasta:** escolha um destino gravável.
- **Erro de rede:** verifique conexão/proxy e use Tentar novamente.
- **Instalação:** confira as mensagens do terminal; não feche a janela antes de
  lê-las. `py -m tkinter` deve abrir uma janela de teste do Tk.

## Estrutura e testes

- `app.py`: fila e supervisão dos processos.
- `ui.py`: aparência, layout, configurações e janela de detalhes.
- `catalog_ui.py`: aba de busca, capa, player de prévia e escolha de formato.
- `test_catalog.py`: links Deezer, busca, versões, campos de catálogo e respostas inválidas.
- `engine.py`: validação, formatos e worker yt-dlp; envia eventos JSON por stdout.
- `test_engine.py`: validação, cancelamento e integração com servidor HTTP local.
- `metadata.py`: consultas públicas e autenticação opcional na API Spotify.
- `metadata_ui.py`: consulta em lote, detalhes e exportação JSON.
- `test_metadata.py`: links, respostas dos provedores, autenticação e erros.
- `matching.py`: seleção da versão YouTube por título, artista e duração.
- `tagging.py`: gravação de tags, capa e registro da origem do áudio.
- `test_automation.py`: seleção de versões, tags reais, capa e fluxo integrado.
- `credentials.py`: armazenamento protegido com DPAPI e carregamento na abertura.
- `test_credentials.py`: persistência entre processos, atualização, exclusão e falhas.
- `library.py` / `history_ui.py`: fila persistida, histórico e acesso aos arquivos.
- `file_output.py`: organização de pastas, publicação e tratamento de duplicados.
- `review.py` / `review_ui.py`: edição validada de tags, capa e confirmação.
- `playlist_import.py` / `playlist_ui.py`: importação e conferência de playlists.
- `audio_tools.py` / `effects_ui.py` / `effects_worker.py`: prévias e exportação dos efeitos.
- `test_library_features.py`: persistência, duplicados, playlists, edição e áudio real.

```powershell
.venv\Scripts\python.exe -m unittest -v
```

Para incluir os testes reais de áudio/vídeo, configure `ONDA_FFMPEG` com a pasta
dos executáveis. Os testes geram mídia sintética temporária e não acessam YouTube:

```powershell
$env:ONDA_FFMPEG = 'C:\caminho\ffmpeg\bin'
.venv\Scripts\python.exe -m unittest -v
```

## Referências

Credenciais: quatro testes adicionais aprovados com valores fictícios, incluindo
leitura em outro processo e ausência dos valores em texto puro no arquivo.
Também foram verificados salvar, reabrir o aplicativo, preencher automaticamente
e esquecer credenciais pela lógica da interface, sem usar credenciais reais.

Validação realizada: 86 testes aprovados no Windows com Python 3.14, yt-dlp
2026.8.19 e FFmpeg 9.0.2, usando mídia sintética em servidor HTTP local. Inclui
os cinco formatos, preservação dos bytes no modo original, erro HTTP e
cancelamento da árvore de processos com FFmpeg. A interface também foi
exercitada com uma fila real local, continuação após falha e nova tentativa.
Os testes adicionais cobrem metadados, links regionais, campos ausentes,
credenciais, limites de requisição e erros dos provedores. A janela de metadados
foi validada com consulta assíncrona e exportação JSON. Consultas públicas reais foram confirmadas no Spotify oEmbed e na
Apple Lookup. A API Spotify autenticada foi testada com respostas simuladas;
não foram fornecidas credenciais reais para validá-la contra o serviço.
Uma busca real Apple → YouTube confirmou a seleção por título, artista e duração.
O fluxo de download e tags foi testado com mídia sintética local e respostas de
catálogo/busca simuladas. Tags, ISRC, capa e registro completo foram lidos de volta
de MP3/M4A/FLAC; todos os arquivos resultantes continuaram decodificáveis pelo FFmpeg.
Downloads de YouTube e de outros serviços externos não foram testados nesta
validação; podem depender de restrições e mudanças de cada plataforma.

- yt-dlp e dependências: https://github.com/yt-dlp/yt-dlp#dependencies
- Integração Python: https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp
- Spotify offline: https://support.spotify.com/br-pt/article/listen-offline/
- Apple Music Lossless: https://support.apple.com/118295
- FFmpeg: https://ffmpeg.org/download.html
- Spotify oEmbed: https://developer.spotify.com/documentation/embeds/reference/oembed
- Spotify Client Credentials: https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
- Spotify Track API: https://developer.spotify.com/documentation/web-api/reference/get-track
- Apple Lookup: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/LookupExamples.html

A janela de versões foi verificada com um worker de teste real: escolha da segunda
opção, continuação e cancelamento enquanto aguarda. A alternância de qualidade/resolução
foi conferida na janela mínima. Bitrates de MP3 e M4A foram medidos com ffprobe.
As novas abas foram exercitadas pela interface: revisão/duplicados com worker
aguardando respostas, exportação real com efeitos, envio do histórico para o
editor, importação de itens selecionados, comando de atualização simulado e
restauração de preferências/fila após reabrir. Testes mediram duração, frequência
e cauda de reverberação, além da preservação do original, tags e capa. MP3, M4A,
FLAC e WAV foram exportados; as quatro combinações de prévia foram decodificadas
pelo ffplay com volume zero. A atualização pela interface foi validada com
processo simulado, sem reinstalar dependências durante esse teste.
A barra de reprodução foi conferida com ffplay real e áudio local silencioso:
leitura da duração, busca parada e durante a prévia original/com efeitos,
avanço a 50% de velocidade, ajustes durante a reprodução, parada, teclado,
descarte de leituras antigas e controles visíveis na janela mínima de 840 × 720.
Busca Deezer real retornou as versões de Stardust; capa real renderizada e
um segundo da prévia pública decodificado pelo ffplay sem áudio audível.
O fluxo de catálogo → formato → fila foi exercitado pela interface com resultados
simulados, incluindo duplicatas, troca de bitrate e descarte de respostas antigas.
O fluxo Deezer → tags foi testado com catálogo simulado e áudio sintético local.
Um link Spotify real sem credenciais foi identificado publicamente e resolvido
para a faixa Deezer com capa e ISRC. Testes cobrem credenciais inválidas/parciais,
fallback Apple, versões incompatíveis, ausência de artista, confirmação manual,
validação da escolha e preservação da origem. A janela de catálogo foi testada
com um worker real aguardando a escolha e retomando/cancelando pela interface.

## FPS, tamanho e escolha de versões

Na tela inicial, o formato de vídeo mostra **Resolução** e **FPS máximo**:
Original, 24, 30, 60 ou 120 fps. O limite seleciona uma versão disponível até
esse FPS; não cria quadros nem transforma um vídeo de 30 em 60 fps. Fontes que
não informam FPS continuam aceitas. Formatos de áudio mostram apenas qualidade.
O FPS também é salvo ao marcar **Lembrar configurações**.

A coluna **Tamanho** começa em “A consultar”. Ao iniciar a fila, depois de
consultar a fonte e antes da transferência, aparece a estimativa com “≈”.
MP3/M4A usam duração e bitrate escolhido, incluindo margem para tags e capa;
vídeo e áudio original usam os tamanhos ou bitrates das faixas selecionadas.
Se faltarem dados, ou no FLAC (cuja compressão depende do conteúdo), aparece
“Indisponível”. Ao concluir, aparece o tamanho real do arquivo com as tags.
Em playlists, a estimativa é do item em andamento e o valor concluído soma
os arquivos salvos naquela execução.

Na janela de versões, selecione uma linha e clique em **Baixar esta versão**,
dê dois cliques na linha ou pressione Enter. Os botões permanecem visíveis
ao reduzir a janela; a lista de versões possui rolagem.

## Recuperação de erro 403 no YouTube

Se o YouTube recusar o arquivo com HTTP 403, o Onda consulta o mesmo vídeo
novamente uma vez e testa pequenos trechos dos formatos candidatos antes de
selecionar um formato acessível. A versão escolhida, o formato de saída e os
limites de resolução/FPS continuam os mesmos. A fonte alternativa pode ter
qualidade inferior; a conversão não recupera qualidade perdida.

A recuperação não reinicia playlists que já concluíram arquivos nessa execução.
Se todos os formatos estiverem bloqueados, confira o erro e tente mais tarde.
Para atualizar o extrator em uma instalação própria, execute
`python -m pip install --upgrade "yt-dlp[default]"` no ambiente do aplicativo.
Os testes simulam uma fonte melhor bloqueada por 403 e uma alternativa acessível
em um servidor local, além de verificar o limite de tentativas e as configurações.

## Créditos e qualidade da capa

Os novos arquivos usam `Artista - Música.ext`, sem ID do YouTube, bitrate ou
FPS no nome. Downloads de catálogo usam o artista principal e o título do
catálogo. Links diretos usam artista/título informados pela fonte; sem artista,
o nome do canal é utilizado. Arquivos anteriores não são renomeados.

Créditos “feat.”, “ft.” e “featuring” podem estar no título ou no campo artista.
A comparação com o YouTube considera o título principal e o artista principal,
mantendo os filtros de versão e duração na seleção automática. Quando apenas
versões com duração/edição incerta forem encontradas, a janela mostra “Conferir”
e exige sua escolha. Resultados sem título/artista compatíveis continuam rejeitados.

As capas Apple/iTunes são solicitadas ao CDN em até 1200 × 1200, em vez da
miniatura de 100 × 100. A resolução efetiva depende da imagem original: uma
capa real de Make Luv retornou 710 × 600. O arquivo incorpora a imagem inteira,
sem corte nem deformação; capas retangulares podem deixar margens em players
que reservam um espaço quadrado. A mudança vale para novas consultas/downloads.
Os arquivos já baixados não são alterados automaticamente.

## Fotos, vídeos e redes sociais

Na aba **Links e fila**, cole o link direto de uma publicação (um por linha):

- **Vídeo (MKV)**: vídeos do TikTok, Instagram e outros sites compatíveis com yt-dlp; resolução e FPS máximos selecionáveis. Kwai usa um extrator próprio para o estado público da publicação.
- **Fotos / carrossel**: todas as imagens disponíveis, preservando formato e ordem, com suporte pelo gallery-dl a Instagram, TikTok e outros sites de galerias compatíveis. Não baixa a capa de um vídeo como se fosse uma foto.
- **Post completo**: fotos e vídeos originais de uma publicação, inclusive carrosséis mistos. Resolução/FPS não são alterados neste modo.
- **MP3 / M4A / FLAC / Áudio original**: continuam disponíveis para extrair áudio dos vídeos compatíveis.

Kwai: fotos só podem ser identificadas quando a página pública contém um atlas de imagens com o ID da publicação; não há garantia de suporte a todos os formatos ou regiões. Não é feito download de perfis inteiros. Publicações inacessíveis, removidas, bloqueadas ou que exigem login podem falhar. Em **Configurações → Redes sociais**, é possível selecionar um arquivo `cookies.txt` no formato Netscape da própria sessão. Esse caminho não é salvo na fila ou nas preferências. Trate esse arquivo como uma senha.

Os arquivos entram no histórico, mostram progresso e usam a política de duplicados. O tamanho aparece quando o servidor o informa. Em caso de falha parcial, os arquivos já concluídos permanecem no histórico e o item pode ser tentado novamente.

Para remover músicas ou outros itens, selecione na fila e clique em **Remover selecionados**, ou pressione **Delete**. Use Ctrl/Shift para selecionar vários. Remover o item em andamento pede confirmação e interrompe só esse download; a fila continua com os próximos. Os arquivos já baixados são preservados.

### Vídeo em MP4

Em Links e fila, escolha **Vídeo (MP4)**, a resolução e o FPS máximo. O Onda prioriza fontes MP4/M4A e converte para MP4 quando necessário. O arquivo final tem extensão .mp4; resolução, FPS, estimativa de tamanho, fila e histórico seguem disponíveis.


### Detecção de publicações e seleção de mídias

Instagram e Twitter/X: cole o link de uma publicação em Vídeo (MKV), MP4 ou Post completo. O app identifica fotos e vídeos na ordem original. Com até duas mídias, baixa todas; com mais de duas, abre uma janela com miniaturas, seleção individual e botão Baixar selecionados. Fotos / carrossel filtra somente as fotos. Vídeos respeitam resolução/FPS e formato selecionados; Post completo mantém os arquivos originais. Links de perfis inteiros não são aceitos.

Twitter/X usa a consulta de publicações do yt-dlp, com alternativa pública de syndication quando necessário, e aceita cookies da sessão própria; a plataforma pode limitar os dados públicos ou exigir login. Kwai ganhou extrator de publicações públicas com estado Nuxt e seleção de qualidade.

O runtime inclui curl-cffi para a simulação de navegador e Pillow para miniaturas. O bloqueio de IP do TikTok pode continuar mesmo com a dependência instalada; o app informa esse caso explicitamente.


### Tipo automático em publicações

Em Instagram, Twitter/X, TikTok e Kwai, os modos de vídeo e publicação reconhecem o conteúdo disponível. Posts somente com fotos salvam imagens. Se Fotos / carrossel estiver selecionado mas o post só tiver vídeos, o app usa MP4 automaticamente, mantendo os limites de resolução/FPS. Em posts mistos, Fotos / carrossel continua filtrando as imagens; Vídeo e Post completo incluem fotos e vídeos. A seleção de mais de duas mídias continua funcionando. Formatos de áudio permanecem uma escolha explícita.

O TikTok pode bloquear a conexão mesmo com o runtime completo. A mensagem informa essa restrição e não promete que cookies resolvam.

### Baixar agora e prévia entre abas

Em Links e fila, cole um único link e clique em **Baixar agora**. O download começa com as opções atuais, sem clicar em Adicionar à fila ou Baixar fila. A playlist de vídeo fica desativada nessa ação. O item aparece em Seus downloads para acompanhar progresso, escolhas e cancelamento; os outros itens pendentes ficam aguardando. Se um item igual já estiver pendente, ele é reutilizado. Com um download ativo, aguarde terminar ou cancele antes de usar Baixar agora.

Em Configurações, marque **Continuar a prévia dos efeitos ao trocar de aba**. Desmarcada, a prévia para ao sair da aba. Marcada, continua tocando nas outras abas; volte à aba Slowed / Sped Up para usar os controles. Desmarcar a opção enquanto estiver em outra aba também para a prévia. Ela sempre é encerrada ao fechar o app. A opção é salva quando Lembrar configurações estiver ativado.

### Fotos do TikTok e mensagens de acesso

Fotos e vídeos do TikTok agora usam o suporte de sessão/página do yt-dlp. O Onda lê o tipo real da publicação, preserva as imagens na ordem original e usa o seletor quando há mais de duas. Não confunde a capa ou o áudio do carrossel com uma foto. Os formatos de vídeo e a troca automática de Fotos para MP4 continuam disponíveis.

Foi corrigida a integração de log do gallery-dl: o adaptador implementa traceback e conserva a causa de falhas. Erros internos ou de leitura de metadados não são mais apresentados automaticamente como se exigissem cookies. A orientação sobre autenticação aparece quando a resposta indica recusa de acesso/login; bloqueios reais da plataforma ainda podem ocorrer.

### Duração das prévias

Em Configurações → Duração das prévias, escolha separadamente o tempo para
Slowed / Sped Up e Reverb e para músicas nas pesquisas (10 a 180 segundos).
Os padrões são 25 e 30 segundos, respectivamente. A duração é do áudio ouvido,
mesmo com velocidade alterada, e vale para a próxima prévia. Nas pesquisas,
o trecho fornecido pelo catálogo pode ser menor. As opções são salvas quando
Lembrar configurações estiver ativado. Exportar continua salvando a música inteira.

### Categorias das configurações

A janela usa abas: Geral (lembrar configurações), Downloads (destino, playlists,
revisão de metadados, organização e duplicados), Áudio (prévias), Contas
(Spotify e cookies de redes sociais) e Ferramentas (FFmpeg e atualizações).
Ajuda e Pronto ficam sempre visíveis na parte inferior.

### Limite de playlists

Em Configurações → Downloads → Máximo de itens por playlist, escolha 100, 250,
500, 1000, 2000 ou 5000 (padrão: 1000). Vale para playlists de vídeo adicionadas
à fila e novas importações na aba Playlists, inclusive TXT/M3U. No Deezer,
o app carrega as páginas seguintes automaticamente. No Spotify sem API,
o embed público pode retornar apenas uma parte da lista; aumentar o limite
não libera itens que o serviço não fornece. A importação de playlists Apple
Music ainda não é suportada. O limite é salvo com Lembrar configurações e
capturado ao adicionar cada playlist à fila.
