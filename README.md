# ONDA

**Português (Brasil)** | [Español](README.es.md) | [English](README.en.md)

[Site oficial](https://enzoandradee16.github.io/Onda/)

Aplicativo gratuito, de código aberto e **sem anúncios** para Windows e Android. Reúne ferramentas para baixar, organizar e editar músicas, vídeos e imagens, com interface em português e suporte ao espanhol e ao inglês.

O ONDA nasceu como um projeto pessoal, feito inicialmente para meu uso e de amigos. Resolvi disponibilizá-lo para quem também achar útil ter essas ferramentas no mesmo lugar, sem anúncios e com opções para personalizar a experiência.

O projeto continua em desenvolvimento. Sugestões, contribuições e relatos de problemas são bem-vindos.

**Versão 1.2.3 para Windows 10 ou superior (x64) e Android 8 ou superior (ARM64 e x86_64).**

![ONDA Windows 1.2.1](docs/images/pc%20novo/pesquisa-musicas-preto-puro.png)

No Android, novas versões podem ser baixadas dentro do ONDA, com progresso e continuidade em segundo plano. Ao terminar, toque em Instalar atualização; na primeira vez, permita a instalação pelo ONDA nas configurações do Android. O sistema pede confirmação e os dados são preservados.

No PC, clique com o botão direito nas listas ou cards para abrir as ações disponíveis naquela aba. Shift+F10 e a tecla de menu também abrem essas opções; uma seleção múltipla é preservada ao clicar em um dos itens selecionados.

## Novidades da versão 1.2.1

- **Windows:** ao clicar em Baixar agora na pesquisa, escolha MP3, M4A, FLAC ou áudio original e a qualidade disponível. A janela parte das preferências salvas e permite baixar ou adicionar à fila; cancelar não inicia o download. A escolha vale para aquela música.
- **Miniplayers no PC:** Efeitos e Jukebox compartilham o visual, com capa, álbum, controles, volume, letras e fila próprios. Continuam visíveis ao minimizar o ONDA. A opção de minimizar ao abrir fica em Aparência; capa e informações da faixa também permitem arrastar a janela.
- **Android:** navegação por Pesquisar, Downloads, Reprodução e Mais, com os seletores Em andamento / Concluídos e Efeitos / Jukebox no mesmo estilo arredondado de Salvos / Importar. Há player expandido, letras em tela cheia e filas independentes de reprodução.
- **Instalador próprio:** “Sua ONDA começa aqui.”, escolha de pasta e atalho, progresso e conclusão. Português, espanhol e inglês podem ser selecionados desde a abertura, incluindo as mensagens do desinstalador. A seleção não altera o idioma salvo no aplicativo.
- **Desinstalador próprio:** mesmo estilo do instalador, com “Até a próxima ONDA.”, três idiomas e duas opções independentes: apagar configurações/fila/histórico e remover ferramentas baixadas. Ambas começam desativadas. Downloads, cookies externos e ferramentas pessoais são preservados.

## Biblioteca e organização

- Detecta links repetidos na fila, no mesmo formato e com as mesmas opções, e no histórico, no mesmo formato. Reconhece links curtos, idiomas e parâmetros de compartilhamento de Spotify, YouTube e Deezer; pede confirmação antes de adicionar novamente. A detecção pode ser desativada em Configurações → Downloads. Playlists diferentes e formatos ou conversões diferentes continuam independentes.
- Edita metadados em lote a partir de vários arquivos locais ou da seleção múltipla no Histórico. Marque os campos que deseja alterar e, se quiser, aplique uma capa comum. Campos desmarcados são preservados. Por padrão, cria cópias; substituir os originais exige confirmação. Cada arquivo é salvo separadamente e falhas são informadas ao final.
- Oferece pastas por álbum, artista/ano/álbum, gênero/artista/álbum e formato/artista/álbum, além das opções anteriores. Os nomes podem incluir faixa, artista, música e disco. Configurações mostra uma prévia. Pastas de playlists são preservadas e números de faixa ausentes são omitidos.

No Android, a identificação por origem no histórico é registrada nos novos downloads; registros antigos sem link de origem não são identificados apenas pelo nome do arquivo. A detecção não compara o áudio nem considera títulos parecidos como prova de duplicação.

## Baixar e abrir

Baixe os pacotes oficiais em [Releases](https://github.com/enzoandradee16/Onda/releases). Escolha a versão Windows ou Android; o código-fonte e as instruções de construção também estão disponíveis neste repositório.

- **Portátil:** extraia o ZIP inteiro e abra `Onda.exe`. Mantenha as pastas `Onda` e `_runtime` junto dele. Não precisa instalar Python. No primeiro uso, o ONDA baixa o FFmpeg diretamente de gyan.dev, com barra de progresso e verificação SHA-256; é necessário acesso à internet nessa preparação.
- **Instalador:** execute o arquivo `Onda-…-Setup-Windows-x64.exe`. A interface própria do ONDA permite escolher a pasta, criar um atalho e acompanhar a instalação. A instalação é por usuário, com desinstalador e compatibilidade com versões anteriores. O FFmpeg também é preparado automaticamente no primeiro uso.
- **Android:** o APK usa assinatura de produção e requer Android 8 ou superior, em aparelho ARM64. As fontes das ferramentas nativas recompiladas são disponibilizadas no pacote Fontes-nativos-Android da mesma release.
- **Código-fonte:** consulte [as instruções de desenvolvimento](Onda/README.md).

Os executáveis Windows não têm assinatura digital. O Windows pode mostrar um aviso de reputação; confira a origem e os hashes antes de executar.

## Idioma

A versão 1.2.1 inclui **Português (Brasil)**, **Español** e **English**, nessa ordem, em **Configurações → Geral → Idioma**. Português continua como idioma padrão. O nome **ONDA** permanece em todos os idiomas. As duas interfaces usam o mesmo catálogo de tradução. No Android, a alteração é imediata; no Windows, reinicie o aplicativo. A escolha é preservada mesmo com “Lembrar configurações” desativado. Nomes de músicas, artistas, álbuns e arquivos permanecem originais.

No Android, o ícone da tela inicial e dos aplicativos recentes acompanha a cor de destaque e os modos claro, escuro, preto puro ou sistema. Alguns launchers podem demorar a atualizar o ícone ou exigir recriar um atalho antigo.

“Lembrar configurações” vem ativado por padrão no PC e no Android. Se você desativar manualmente, essa escolha será respeitada nas próximas aberturas.

No Android, controles com símbolos, seletores, caixas de seleção e barras de reprodução/efeitos expõem nomes e estados para TalkBack e serviços de acessibilidade. O recorte da capa oferece ações para mover a imagem sem arrastar. As descrições acompanham o idioma escolhido.

## Fila e reinício

Na **Fila** do Windows e em **Downloads** no Android, escolha a exibição compacta ou em cards e ajuste o tamanho pelo controle discreto na própria aba. No Windows, **Ctrl + rolagem do mouse** também altera o tamanho dos cards. O tamanho da fila é independente do histórico. Os cards completos mostram capa, artista, álbum, duração e outros metadados fornecidos pela fonte. No Histórico, “Limpar histórico”, visualização e tamanho ficam alinhados horizontalmente, centralizados abaixo da pesquisa. As opções de exibição ficam também em Aparência. A visualização e o tamanho dos cards da fila e do histórico são salvos ao reabrir, mesmo com “Lembrar configurações” desativado.

No Windows, **Reiniciar** aparece abaixo de Idioma apenas enquanto houver uma alteração de idioma pendente. Voltar ao idioma atual remove a pendência. A fila é preservada ao reiniciar; operações em andamento precisam terminar primeiro. No Android, o idioma e a aparência mudam imediatamente, sem reinício.

## O que faz

- Pesquisa músicas no Deezer, Apple Music e Spotify; obtém metadados e capas. A conexão com Spotify é opcional e amplia os recursos de pesquisa e playlists.
- Para músicas de streaming, MP3/M4A usam uma versão equivalente do YouTube. FLAC usa o acervo Monochrome quando houver uma correspondência compatível, com validação do áudio e seleção de versões.
- Baixa links de vídeo, áudio e imagem, incluindo publicações com múltiplas mídias de redes sociais, quando acessíveis.
- Oferece fila persistente, download imediato, histórico, seleção de mídias e organização por pastas.
- Importa álbuns e playlists, além de TXT, M3U e CSV do Exportify. Permite pesquisar na lista e escolher formato e qualidade próprios.
- Converte imagens e cria versões Slowed, Sped Up e Reverb, com presets, prévia, navegação na reprodução e opção de manter o tom.
- Tem modos claro, escuro, preto puro e do sistema, 16 cores de destaque e abas reorganizáveis.

![Configurações e aparência](docs/images/onda-configuracoes.png)

## ONDA no Windows

Capturas reais da versão 1.2.1 em português. Clique para ampliar.

<table>
  <tr>
    <td align="center" width="50%"><strong>Pesquisar músicas</strong><br><a href="docs/images/pc%20novo/pesquisa-musicas-preto-puro.png"><img src="docs/images/pc%20novo/pesquisa-musicas-preto-puro.png" width="460" alt="ONDA: Pesquisar músicas"></a></td>
    <td align="center" width="50%"><strong>Editar metadados</strong><br><a href="docs/images/pc%20novo/editar-metadados-preto-puro.png"><img src="docs/images/pc%20novo/editar-metadados-preto-puro.png" width="460" alt="ONDA: Editar metadados"></a></td>
  </tr>
  <tr>
    <td align="center" width="50%"><strong>Imagens</strong><br><a href="docs/images/pc%20novo/imagens-claro.png"><img src="docs/images/pc%20novo/imagens-claro.png" width="460" alt="ONDA: Imagens"></a></td>
    <td align="center" width="50%"><strong>Fila de downloads</strong><br><a href="docs/images/pc%20novo/fila-downloads-preto-puro.png"><img src="docs/images/pc%20novo/fila-downloads-preto-puro.png" width="460" alt="ONDA: Fila de downloads"></a></td>
  </tr>
  <tr>
    <td align="center" width="50%"><strong>Efeitos</strong><br><a href="docs/images/pc%20novo/reproducao-efeitos-claro.png"><img src="docs/images/pc%20novo/reproducao-efeitos-claro.png" width="460" alt="ONDA: Efeitos"></a></td>
    <td align="center" width="50%"><strong>Jukebox infinito</strong><br><a href="docs/images/pc%20novo/reproducao-jukebox-claro.png"><img src="docs/images/pc%20novo/reproducao-jukebox-claro.png" width="460" alt="ONDA: Jukebox infinito"></a></td>
  </tr>
</table>

Outras capturas: [Letras sincronizadas](docs/images/pc%20novo/letras-sincronizadas-claro.png) · [Miniplayer com letras](docs/images/pc%20novo/miniplayer-jukebox-letras-preto-puro.png).

## ONDA no Android

Capturas reais da versão 1.2.1 em português. Clique para ampliar.

<table>
  <tr>
    <td align="center" width="33%"><strong>Pesquisar músicas</strong><br><a href="docs/images/android%20novo/pesquisa-musicas-escuro.png"><img src="docs/images/android%20novo/pesquisa-musicas-escuro.png" width="230" alt="ONDA: Pesquisar músicas"></a></td>
    <td align="center" width="33%"><strong>Downloads</strong><br><a href="docs/images/android%20novo/downloads-claro.png"><img src="docs/images/android%20novo/downloads-claro.png" width="230" alt="ONDA: Downloads"></a></td>
    <td align="center" width="33%"><strong>Álbuns e playlists salvos</strong><br><a href="docs/images/android%20novo/albuns-playlists-salvos-claro.png"><img src="docs/images/android%20novo/albuns-playlists-salvos-claro.png" width="230" alt="ONDA: Álbuns e playlists salvos"></a></td>
  </tr>
  <tr>
    <td align="center" width="33%"><strong>Efeitos</strong><br><a href="docs/images/android%20novo/reproducao-efeitos-claro.png"><img src="docs/images/android%20novo/reproducao-efeitos-claro.png" width="230" alt="ONDA: Efeitos"></a></td>
    <td align="center" width="33%"><strong>Jukebox infinito</strong><br><a href="docs/images/android%20novo/reproducao-jukebox-claro.png"><img src="docs/images/android%20novo/reproducao-jukebox-claro.png" width="230" alt="ONDA: Jukebox infinito"></a></td>
    <td align="center" width="33%"><strong>Player expandido</strong><br><a href="docs/images/android%20novo/player-efeitos-claro.png"><img src="docs/images/android%20novo/player-efeitos-claro.png" width="230" alt="ONDA: Player expandido"></a></td>
  </tr>
</table>

Outras capturas: [Álbum e faixas](docs/images/android%20novo/album-discovery-escuro.png) · [Escolha de formato](docs/images/android%20novo/escolha-formato-escuro.png) · [Letras em tela cheia](docs/images/android%20novo/letras-tela-cheia-escuro.png) · [Fila de reprodução](docs/images/android%20novo/fila-reproducao-claro.png).

## Uso rápido

1. Escolha a pasta de destino em **Configurações**.
2. Em **Links** no Windows ou **Downloads** no Android, cole o link, escolha o formato e use **Baixar agora** ou adicione à fila.
3. Em **Álbuns e playlists**, carregue o link ou importe um arquivo, selecione os itens e escolha as opções de download.
4. Use **Imagens** para conversão de fotos e **Efeitos** para editar uma música local.

Álbuns usam uma subpasta `Artista - Álbum`; playlists usam o nome da playlist. A ajuda detalhada está no [manual](Onda/README.md).

## Limitações

- Nem todo link é suportado. Plataformas podem exigir login, cookies ou bloquear o acesso por região/IP; mudanças nos sites podem interromper downloads.
- O ONDA não remove DRM nem obtém o áudio original protegido de Spotify ou Apple Music. Converter áudio com perdas para FLAC não recupera qualidade lossless.
- A correspondência no YouTube pode encontrar outra edição ou versão. Confira título, duração, artista e prévia.
- Playlists públicas do Spotify podem retornar apenas parte da lista. Conecte a conta ou importe um CSV para listas maiores, quando disponível.
- SVG exportado de uma foto contém a imagem incorporada; não faz vetorização.

Use apenas conteúdo que você tenha autorização para baixar. Spotify, Apple Music, YouTube e as demais marcas pertencem aos seus titulares; o ONDA não é afiliado a essas plataformas.

## Dados locais e privacidade

No Windows, nos modos portátil e instalado, configurações e histórico ficam em `%LOCALAPPDATA%\Onda`. O FFmpeg obtido diretamente do fornecedor fica em `tools/ffmpeg/9.0.2` dentro dessa pasta e é reutilizado sem novo download. A versão portátil mantém as preferências no PC, fora da pasta do programa. Credenciais Spotify são protegidas com DPAPI do Windows. Cookies fornecidos pelo usuário devem ser tratados como dados de acesso e nunca enviados ao GitHub.

O aplicativo faz conexões com as plataformas consultadas para pesquisa, metadados, capas, prévias e downloads. Não há servidor próprio do ONDA para receber o histórico. Ao relatar problemas, remova credenciais, cookies e dados pessoais dos logs.

## Problemas e contribuições

Abra uma [issue](https://github.com/enzoandradee16/Onda/issues) com a versão do ONDA, a versão do Windows ou Android, passos para reproduzir e mensagem de erro sem dados pessoais. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) e [SECURITY.md](SECURITY.md).

## Licença

Copyright (c) 2026 Enzo Andrade. O código próprio do ONDA é disponibilizado sob **GPL-2.0-only**, sem garantia. Consulte [LICENSE](LICENSE). Dependências e ferramentas mantêm suas respectivas licenças, descritas em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Na desinstalação do aplicativo Windows, você pode manter os dados ou apagar configurações, fila, histórico, contas salvas e o registro da primeira abertura. A escolha padrão é manter; desinstalação silenciosa também mantém. Uma segunda escolha independente permite remover as ferramentas baixadas pelo ONDA, como o FFmpeg. Por padrão, o cache é mantido; a desinstalação silenciosa também o preserva. Downloads, cookies externos e ferramentas de outras pastas são preservados. Esses dados são compartilhados entre as versões instalada e portátil no mesmo PC.

## Fila e edição de áudio

Downloads simultâneos, retomada, ordem da fila, edição local de tags/capa/letra, normalização com prévia, agendamento e transferência de preferências: consulte [o guia de recursos avançados](RECURSOS-AVANCADOS.md).

## Desempenho medido

Consulte o [relatório de abertura, memória, CPU e downloads](docs/DESEMPENHO.md), com método, limites e dados brutos. Os [diagnósticos reproduzíveis](diagnosticos/README.md) ficam separados do aplicativo.

A otimização posterior de abertura e listas está documentada em [Otimização de interface](docs/OTIMIZACAO.md), com comparação antes/depois.

Melhorias e medições da troca de menus: [Navegação e configurações](docs/NAVEGACAO.md).
