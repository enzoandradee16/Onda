# ONDA — uso e desenvolvimento

O [README principal](../README.md) apresenta o aplicativo e os pacotes para Windows.

## Executar o código-fonte

Requisitos: Windows 10/11 x64, Python 3.11 ou superior com Tcl/Tk e acesso à internet. Para conversão e efeitos, use Configurações → Ferramentas → Preparar FFmpeg, ou selecione uma pasta existente com FFmpeg, ffprobe e ffplay. Nos pacotes Windows, a preparação começa automaticamente na primeira abertura. Node.js é usado pelo yt-dlp em desafios JavaScript do YouTube.

Dentro da pasta `Onda` deste repositório, execute `instalar.bat` para criar o ambiente Python e instalar as dependências; depois execute `iniciar.bat`.

Se o Python original foi removido ou mudou de pasta, execute `instalar.bat` novamente. Ele detecta o ambiente inválido, preserva a pasta anterior em `.venv-backup-...` e cria um ambiente com o Python instalado atualmente.

Alternativa pelo terminal, dentro dessa mesma pasta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## Abas e fluxo

**Pesquisar músicas:** escolha a plataforma, procure artista/título, confira metadados e a versão de áudio encontrada. Spotify requer conexão para alguns recursos; links podem usar dados públicos e correspondências de outras plataformas.

**Links e fila:** cole links, selecione formato, qualidade e, para vídeo, resolução/FPS. Use Baixar agora para os itens atuais ou Adicionar à fila. É possível selecionar/remover itens, limpar a fila e tentar novamente. Downloads concluídos aparecem no histórico.

**Imagens:** escolha formato e tamanho máximo. Manter proporção evita distorção e ampliação. Links de publicações são analisados para identificar as mídias disponíveis.

**Álbuns e playlists:** carregue links, TXT/M3U ou CSV do Exportify; pesquise na lista e selecione os itens. Os controles de qualidade são próprios desta aba. Conferir correspondências procura versões no YouTube antes de baixar. O modo automático usa a maior similaridade encontrada, sem garantir a mesma edição. O limite de itens é configurável, mas depende do que a plataforma disponibiliza. A conexão Spotify permite paginação autenticada; a leitura pública pode ser parcial.

**Histórico:** consulte downloads anteriores e abra arquivos/pastas. As opções de duplicados e organização ficam em Configurações.

**Efeitos:** abra uma música local, ajuste velocidade (50–150%) e reverb de forma independente ou use presets. Manter tom evita que a mudança de velocidade altere o pitch. Gere/ouça a prévia e navegue pela barra de reprodução. O título e o nome exportados indicam apenas os efeitos usados; as demais tags são preservadas quando suportadas pelo formato.

## Preferências e contas

Configurações são separadas por categorias, incluindo Aparência, Downloads, Áudio, Contas e Ferramentas. Lembrar configurações permite restaurar preferências ao abrir. Há restauração seletiva ou completa, duração das prévias e reprodução de efeitos ao trocar de aba. A janela inicial é opcional e aparece uma única vez por perfil.

Dados em `%LOCALAPPDATA%\Onda` (portátil e instalado): `settings.json`, `library.sqlite3`, `spotify.dpapi`, `spotify-account.dpapi` e `welcome-seen.json`. Não compartilhe esses arquivos. A conexão Spotify usa retorno local `http://127.0.0.1:8765/callback`; configure esse endereço quando o app solicitar suas credenciais de desenvolvedor.

## Testes

Na raiz do repositório, com dependências instaladas:

```powershell
$env:ONDA_UI_TESTS = '1'
.\Onda\.venv\Scripts\python.exe -m unittest discover -s Onda -q
```

Testes de interface precisam de uma sessão gráfica do Windows. Não representam teste real de download em todas as plataformas.

## Construir executáveis

Os scripts de empacotamento ficam fora do Git por opção de organização. O pacote de fontes da release inclui `empacotamento/Build-Windows.ps1`, `build_package.py`, `Launcher.cs`, `Onda.iss` e instruções. A construção requer CPython com Tcl/Tk, Node.js, compilador C# do Windows e Inno Setup. O FFmpeg não deve ser incluído no pacote: é baixado diretamente do fornecedor no primeiro uso. As versões efetivamente incluídas estão no manifesto da release; dependências com limites abertos podem mudar em construções futuras.

O launcher inicia o Python privado, e o Inno Setup cria instalação por usuário, atalhos e desinstalador. Preserve o AppId para que atualizações reconheçam a instalação anterior.

Na desinstalação, você pode manter os dados ou apagar configurações, fila, histórico, contas salvas e o registro da primeira abertura. A escolha padrão é manter; desinstalação silenciosa também mantém. Uma segunda escolha independente permite remover as ferramentas baixadas pelo ONDA, como o FFmpeg. Por padrão, o cache é mantido; a desinstalação silenciosa também o preserva. Downloads, cookies externos e ferramentas de outras pastas são preservados. Esses dados são compartilhados entre as versões instalada e portátil no mesmo PC.

## Preparação automática do FFmpeg

O download usa uma versão fixa de gyan.dev, conferida contra um SHA-256 incluído no código antes da extração. Somente FFmpeg, ffprobe, ffplay e seus avisos de licença são extraídos. Os pacotes do ONDA não redistribuem esses executáveis.

O cache fica em `%LOCALAPPDATA%\Onda\tools\ffmpeg\9.0.2` e funciona tanto com o portátil quanto com a instalação. A preparação mostra progresso, permite adiar e oferece nova tentativa após falha. Para repetir depois, use Configurações → Ferramentas → Preparar FFmpeg. Sem as ferramentas, conversões e prévias ficam indisponíveis até concluir a preparação. Uma pasta personalizada completa é respeitada.

Apagar os dados pessoais e remover o cache das ferramentas são escolhas independentes. Se remover o cache, será necessário baixar o FFmpeg novamente, inclusive na versão portátil deste PC. Atualizações do instalador removem somente os três executáveis da antiga pasta `_runtime/ffmpeg`, se presentes.


### FLAC direto no ONDA

Ao escolher FLAC para uma faixa de Spotify, Deezer ou Apple Music, o ONDA consulta o servidor público Monochrome e baixa o arquivo diretamente, sem abrir navegador. A correspondência compara título, artista, versão, duração e ISRC quando disponível. Versões ambíguas pedem confirmação; a opção de maior similaridade automatiza essa escolha. O download mostra progresso, valida o codec e a decodificação completa, aplica metadados/capa e respeita destino, duplicados, playlists e histórico.

O acervo é limitado e a disponibilidade depende do serviço externo. Se não houver FLAC compatível, o ONDA avisa e não converte silenciosamente YouTube em FLAC. MP3/M4A continuam pelo YouTube. A origem anterior dos arquivos no servidor e a masterização não são comprovadas; o registro de origem identifica Monochrome. Links diretos, vídeos e efeitos continuam permitindo conversão para FLAC, que não recupera qualidade perdida.


### Novos downloads durante uma execução

Você pode usar **Baixar agora** enquanto outras mídias estão sendo baixadas. Com vaga no limite de downloads simultâneos, o novo item começa; com todas as vagas ocupadas, aguarda a próxima. Solicitações individuais não iniciam outros itens pendentes que você não pediu para baixar. A fila em execução aceita novos itens sem reiniciar os downloads atuais.
