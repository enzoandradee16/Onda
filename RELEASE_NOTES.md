# ONDA 1.2.1

## Downloads e TikTok

Corrige a falha reproduzida no Android em que o TikTok retorna uma página intermediária sem os dados da publicação. O extrator mantém a tentativa normal e, somente para falhas de extração específicas, consulta a página móvel e o player público oficial do mesmo ID. Fotos usam os itens explícitos da publicação, sem tratar a capa do vídeo como uma foto. Conteúdo privado ou que exige login não é liberado por esse fluxo.

O Android inclui yt-dlp 2026.10.21 e gallery-dl 1.32.17. Um extrator antigo salvo no aparelho não substitui o motor mais novo do APK. Os formatos de redes sociais agora compartilham o mesmo worker do PC.

## Reprodução e desempenho no Android

A fila do Jukebox prepara as próximas duas músicas e prioriza a seleção manual, mantendo as músicas anteriores na lista. Modelos distantes saem da memória e podem ser preparados novamente ao voltar; os arquivos de cache continuam disponíveis para reutilização.

Corrige pedidos de reprodução antigos que podiam substituir uma seleção recente ou iniciar depois de Parar, a retomada após recriar a análise e campos vazios da fila de arquivos locais. Metadados com erro podem ser consultados novamente. Letras longas reutilizam o texto e as marcações por palavra já calculados.

## Cancelamento e preparação da release

Corrige uma corrida em que um processo nativo podia continuar executando após o cancelamento por ainda não ter sido registrado. O processo recém-criado agora é encerrado e seus recursos são liberados nesse caso. Avisos e arquivos de fontes de terceiros foram alinhados às versões incluídas nos APKs.

## Validação

Verificação final: 91 testes instrumentados no BlueStacks, mais um download TikTok real; 102 testes do PC e extratores, 34 testes de interface Tkinter e 76 testes JVM aprovados. A pasta local Testes e seus dados não fazem parte dos pacotes.

Testes reais em BlueStacks com Android 11/x86_64 cobriram o TikTok fornecido em MP4, MP3, M4A, original e FLAC, fotos TikTok, Reel e carrossel Instagram. O modo automático também passou. Arquivos foram publicados e lidos pelos provedores Android, com limpeza dos itens de teste ao final. Três verificações instrumentadas de ferramentas nativas, downloads paralelos e limites de vídeo passaram.

O aparelho físico ARM64 ainda precisa confirmar o resultado. BlueStacks não substitui a validação em hardware ARM64.

## Pacotes

Windows x64: portátil e instalador 1.2.1, metadados 1.2.1.0. Android: APKs ARM64 e x86_64, versão 1.2.1/código 28, assinados com a chave original do ONDA.

Release preparada como rascunho no GitHub, sem publicação automática.
