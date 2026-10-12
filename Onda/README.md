# ONDA — uso e desenvolvimento

O [README principal](../README.md) apresenta o aplicativo e os pacotes para Windows.

## Executar o código-fonte

Requisitos: Windows 10/11 x64, Python 3.11 ou superior com Tcl/Tk e acesso à internet. Para conversão e efeitos, instale FFmpeg, ffprobe e ffplay e selecione sua pasta em Configurações, ou coloque-os no PATH. Node.js é usado pelo yt-dlp em desafios JavaScript do YouTube.

Dentro da pasta `Onda` deste repositório, execute `instalar.bat` para criar o ambiente Python e instalar as dependências; depois execute `iniciar.bat`.

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

Os scripts de empacotamento ficam fora do Git por opção de organização. O pacote de fontes da release inclui `empacotamento/Build-Windows.ps1`, `build_package.py`, `Launcher.cs`, `Onda.iss` e instruções. A construção requer CPython com Tcl/Tk, FFmpeg, Node.js, compilador C# do Windows e Inno Setup. As versões efetivamente incluídas estão no manifesto da release; dependências com limites abertos podem mudar em construções futuras.

O launcher inicia o Python privado, e o Inno Setup cria instalação por usuário, atalhos e desinstalador. Preserve o AppId para que atualizações reconheçam a instalação anterior.
