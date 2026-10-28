# ONDA — uso e desenvolvimento

## Uso na versão 1.2.3

Revisado em 27/10/2026. Consulte o [inventário de funcionalidades](../docs/INVENTARIO-FUNCIONALIDADES.md) para a lista completa e os limites.

Na pesquisa, **Baixar agora** abre a escolha de MP3, M4A, FLAC ou áudio original e da qualidade compatível. A seleção inicial vem de Configurações → Downloads → Formato de álbuns e playlists e das qualidades MP3/M4A dessa categoria. A escolha é aplicada somente à música; permite iniciar ou adicionar à fila, e Voltar/Esc cancela sem baixar. A opção direta de adicionar à fila continua usando as preferências salvas.

Efeitos e Jukebox compartilham música, fila e miniplayer flutuante, com dados, letras e volume. Os ajustes podem funcionar juntos na tela Reprodução; veja [Reprodução unificada](../docs/REPRODUCAO-UNIFICADA.md). Minimizar a janela principal não minimiza o player. Em Aparência, **Minimizar ONDA ao abrir o miniplayer** controla apenas a janela principal. Arraste pelo cabeçalho, capa ou informações; os botões continuam disponíveis. Fixar mantém o player acima de outras janelas.

O instalador próprio oferece português, espanhol e inglês desde a abertura, além de pasta, atalho e progresso. O idioma escolhido vale também para as confirmações do desinstalador, sem alterar o idioma do app. Veja [o instalador](../docs/INSTALADOR-WINDOWS.md) e [a validação 1.2.3](../docs/VALIDACAO-RELEASE-1.2.3.md). As capturas atualizadas ficam no [README principal](../README.md).

O [README principal](../README.md) apresenta o aplicativo e os pacotes da versão atual para Windows e Android.

## Executar o código-fonte

Requisitos: Windows 10/11 x64, Python 3.11 ou superior com Tcl/Tk e acesso à internet. Para conversão e efeitos, use Configurações → Ferramentas → Preparar FFmpeg, ou selecione uma pasta existente com FFmpeg, ffprobe e ffplay. Nos pacotes Windows, a preparação começa automaticamente na primeira abertura. Node.js é usado pelo yt-dlp em desafios JavaScript do YouTube.

Dentro da pasta `Onda`, `instalar.bat` prepara o ambiente Python básico. A interface atual dos pacotes Windows usa **Qt/QML**; instale também `requirements-qt.txt` e execute `qt_desktop_ui.py`. `iniciar.bat` executa a interface Tk conservada quando não encontra o launcher empacotado; não é o comando de referência para desenvolver a interface Qt.

Se o Python original foi removido ou mudou de pasta, execute `instalar.bat` novamente. Ele detecta o ambiente inválido, preserva a pasta anterior em `.venv-backup-...` e cria um ambiente com o Python instalado atualmente.

Alternativa pelo terminal, dentro dessa mesma pasta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-qt.txt
.\.venv\Scripts\python.exe qt_desktop_ui.py
```

## Abas e fluxo

**Pesquisar músicas:** escolha a plataforma, procure artista/título, confira metadados e a versão de áudio encontrada. Spotify requer conexão para alguns recursos; links podem usar dados públicos e correspondências de outras plataformas.

**Links e Fila:** no PC são páginas separadas. Em Links, cole URLs e selecione formato, qualidade e, para vídeo, resolução/FPS. Fila reúne os trabalhos; Links também exibe os adicionados por essa página. Use Baixar agora para os itens atuais ou Adicionar à fila. É possível selecionar/remover itens, limpar a fila e tentar novamente. Downloads concluídos aparecem no histórico. O seletor na própria aba alterna entre lista compacta e cards completos, com capas e metadados disponíveis. Ajuste o tamanho pelo controle discreto; no PC, Ctrl + roda do mouse também altera os cards.

**Imagens:** escolha formato e tamanho máximo. Manter proporção evita distorção e ampliação. Links de publicações são analisados para identificar as mídias disponíveis.

**Álbuns e playlists:** carregue links, TXT/M3U ou CSV do Exportify; pesquise na lista e selecione os itens. Os controles de qualidade são próprios desta aba. Conferir correspondências procura versões no YouTube antes de baixar. A seleção automática considera compatibilidade de título, artista, versão e duração; uma correspondência insuficiente pode impedir o download e exigir escolha manual. Não garante a mesma edição. O limite de itens é configurável, mas depende do que a plataforma disponibiliza. A conexão Spotify permite paginação autenticada; a leitura pública pode ser parcial.

**Histórico:** consulte downloads anteriores, abra arquivos/pastas e envie o áudio para o editor ou para os efeitos. Abaixo da pesquisa ficam Limpar histórico, visualização compacta/completa e tamanho dos cards, centralizados na mesma linha. O tamanho é independente da fila; no PC, Ctrl + roda do mouse também o ajusta. As opções de duplicados e organização ficam em Configurações.

**Efeitos:** abra música local, pesquise ou cole link de faixa, álbum ou playlist; ajuste velocidade e reverb independentemente ou use presets. Manter tom preserva o pitch ao mudar a velocidade. Reproduza a música e navegue pela barra; a fila tem busca, preparação por faixa, reorganização e controles de ordem. O título e o nome exportados indicam apenas os efeitos usados; as demais tags são preservadas quando suportadas pelo formato.

## Preferências e contas

Configurações são separadas por categorias, incluindo Aparência, Downloads, Áudio, Contas e Ferramentas. Lembrar configurações permite restaurar preferências ao abrir. Há restauração seletiva ou completa e duração das prévias de pesquisa. Efeitos/Jukebox usam reprodução integral e fila compartilhada; navegar não encerra a música. Letras podem ser buscadas e escolhidas automaticamente pelo LRCLIB. A janela inicial é opcional e aparece uma única vez por perfil.

Em **Configurações → Geral → Idioma**, escolha Português (Brasil), Español ou English, nessa ordem. Português é o padrão. No PC, o botão Reiniciar aparece abaixo do idioma somente enquanto a alteração está pendente; ao reiniciar, a fila é preservada. No Android, a mudança é imediata. O nome ONDA e os dados de músicas/arquivos permanecem originais. O idioma, a visualização e o tamanho dos cards da fila e do histórico são salvos mesmo sem Lembrar configurações.

Dados em `%LOCALAPPDATA%\Onda` (portátil e instalado): `settings.json`, `language.json`, `library.sqlite3`, `spotify.dpapi`, `spotify-account.dpapi` e `welcome-seen.json`. Não compartilhe esses arquivos. A conexão Spotify usa retorno local `http://127.0.0.1:8765/callback`; configure esse endereço quando o app solicitar suas credenciais de desenvolvedor.

## Testes

Na raiz do repositório, com dependências instaladas:

```powershell
$env:ONDA_UI_TESTS = '1'
$env:PYTHONPATH = (Resolve-Path .\Onda).Path
Get-ChildItem .\Onda\test_*.py | ForEach-Object {
    & .\Onda\.venv\Scripts\python.exe -m unittest $_.BaseName -q
    if ($LASTEXITCODE -ne 0) { throw "Falha em $($_.Name)" }
}
```

Os módulos são executados em processos separados para isolar as raízes Tk e as threads. Testes de interface precisam de uma sessão gráfica do Windows. Não representam teste real de download em todas as plataformas.

## Construir executáveis

Os fontes de empacotamento estão rastreados em `empacotamento/`: `prepare_release.py`, `build_package.py`, `build_installer.py`, `Launcher.cs`, `Installer.cs` e `Uninstaller.cs`, entre outros. A construção atual usa runtime Python/Qt, Node.js e as ferramentas de compilação Windows exigidas pelos scripts. Consulte [PUBLICAR_RELEASE.md](../PUBLICAR_RELEASE.md) para o fluxo de preparação; scripts antigos ou `Onda.iss` não substituem o instalador próprio atual. O FFmpeg não deve ser incluído no pacote: é baixado diretamente do fornecedor no primeiro uso. As versões efetivamente incluídas estão no manifesto da release; dependências com limites abertos podem mudar em construções futuras.

O launcher inicia o Python privado e a interface Qt. O instalador próprio prepara a instalação por usuário, atalhos e desinstalador. Preserve a identidade do aplicativo e os contratos de atualização dos scripts.

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
