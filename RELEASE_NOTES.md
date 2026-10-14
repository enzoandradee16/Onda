# ONDA 1.1.0

Atualização para Windows 10/11 x64 e Android 8 ou superior (ARM64).

## Novidades desde a versão 1.0.0

- **Atualizações Android:** download da nova versão dentro do ONDA, com progresso, cancelamento e continuidade em segundo plano. A instalação exige confirmação do Android; pacote, versão e assinatura são conferidos antes de abrir o instalador.
- **Menus de contexto no PC:** botão direito, Shift+F10 ou tecla de menu nas listas de pesquisa, fila, histórico, álbuns/playlists, metadados e escolha de versões, incluindo cards. As opções acompanham a seleção e o estado dos controles da aba.
- **Idiomas:** Português (Brasil), Español e English, nessa ordem, com português como padrão. PC e Android compartilham os catálogos de tradução; o nome ONDA e os nomes originais de músicas, artistas, álbuns e arquivos são preservados.
- **Preferências:** lembrar configurações ativado por padrão; visualização e tamanho da fila e do histórico são preservados separadamente ao reabrir o app.
- **Acessibilidade Android:** descrições, estados e ações para leitores de tela nos controles, seleções, ajustes e edição de capa, nos três idiomas.
- **Traduções:** revisão dos textos internos e correção da pergunta de confirmação de atualização no PC em inglês e espanhol.
- **Ícone Android:** o ícone da tela inicial e dos aplicativos recentes acompanha a cor de destaque e os modos claro, escuro, preto puro ou sistema, usando recursos vetoriais leves.
- **Links e fila:** exibição compacta ou em cards completos, com capa, artista, álbum, duração e demais metadados disponíveis. Controles discretos de visualização e tamanho na própria aba, independentes do Histórico. No PC, Ctrl + roda do mouse ajusta os cards.
- **Histórico:** controles de visualização e tamanho na própria aba, ao lado de Limpar histórico, centralizados horizontalmente abaixo da pesquisa.
- **Reinício pendente no PC:** botão Reiniciar abaixo do idioma apenas enquanto a alteração aguarda aplicação. Reverter ao idioma atual remove a pendência; a fila é preservada. No Android, o idioma muda imediatamente.
- **Identificação de links:** correção do artista e do nome da música ao adicionar links à fila, incluindo Spotify no Android. Metadados públicos são preservados mesmo quando uma consulta complementar falha; uma resposta atrasada não sobrescreve títulos escolhidos pelo usuário.
- **Capas e informações:** carregamento em segundo plano, cache limitado e reaproveitamento dos dados da pesquisa, de álbuns e de playlists.
- **Documentação:** READMEs em português, espanhol e inglês, com navegação entre idiomas e novas capturas Android sem barras do sistema.

## Qual arquivo baixar?

- `Onda-1.1.0-Setup-Windows-x64.exe`: instalador por usuário, com atalhos e desinstalador.
- `Onda-1.1.0-Portable-Windows-x64.zip`: extraia tudo e abra `Onda.exe`; mantenha as pastas `Onda` e `_runtime` ao lado do executável. Python e Node incluídos; FFmpeg preparado com internet no primeiro uso.
- `ONDA-Android-1.1.0-arm64-v8a.apk`: Android ARM64, assinado com a mesma chave de produção; versionCode 18.
- `Onda-1.1.0-Fontes.zip`: código-fonte e scripts de construção correspondentes.
- `Onda-1.1.0-Fontes-nativos-Android.zip`: fontes e receitas das ferramentas nativas Android.
- `Onda-1.1.0-Fontes-de-terceiros.zip`: fontes e avisos das dependências Python redistribuídas.

Anexe também `SHA256SUMS.txt`, `MANIFEST.json`, `SOURCE_MANIFEST.json`, `VALIDACAO.md` e os avisos de terceiros.

## Atualização e limites

A identidade Windows e a chave Android foram preservadas para atualização sobre a versão anterior. O APK usa um versionCode maior; os dados existentes são preservados pela atualização normal. A release 1.0.0 permanece intacta.

Os executáveis Windows não possuem assinatura Authenticode. O APK é assinado com a chave de produção ONDA. Consulte `VALIDACAO.md` para resultados, verificações e limites da rodada de preparação.

O acesso às plataformas e a disponibilidade de metadados, capas e FLAC dependem de terceiros e podem exigir autenticação. A atualização não altera as regras de escolha de versões para download. Use conteúdo que você tenha autorização para baixar.
