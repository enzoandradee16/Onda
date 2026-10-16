# Prioridade dos metadados em links Spotify

Esta prioridade só é aplicada quando a origem é um link Spotify de faixa validado pelo parser, incluindo os links individuais enumerados de um álbum ou playlist Spotify. Links curtos oficiais são resolvidos e validados. Links Deezer, Apple, YouTube e de outros serviços mantêm seu comportamento; mencionar Spotify num título ou descrição não ativa esta regra.

## Origem e preservação

1. Playlists conectadas agora guardam o registro completo normalizado de cada faixa, em vez de reduzir a resposta a título, artistas e duração. Álbum, capa, data, ISRC, número da faixa/disco e indicação de conteúdo explícito são preservados quando fornecidos pela API.
2. Links individuais aproveitam a conta Spotify conectada, inclusive conexões que só existem na sessão do PC. A consulta ocorre fora da interface. O processo de download recebe somente os metadados normalizados, sem tokens OAuth.
3. Registros completos da playlist são reaproveitados. Um registro parcial pode ser completado pela própria API do Spotify antes de consultar outro catálogo. Falha de autorização mantém a alternativa pública existente.
4. Deezer e Apple só preenchem campos ausentes, após as verificações de artista, duração, versão, ISRC e edição disponíveis. Valores existentes, incluindo `explicit=false`, não são substituídos. O ID, link e identificação da plataforma continuam Spotify.
5. Complementação opcional indisponível ou ambígua não impede o download de uma faixa Spotify que já tenha uma identificação utilizável. Se faltar artista e não houver identificação segura, permanece a necessidade de escolha/erro informativo.

Quando falta apenas gênero, a consulta adicional prioriza Apple, que fornece esse campo. O programa não consulta outro catálogo apenas para obter uma URL de prévia. Não há garantia de que todo campo ou playlist esteja disponível nas permissões/região da conta.

## Transparência

O log mostra `Metadados e capa: Spotify` ou, quando existem campos complementados, `Spotify + Deezer`/`Spotify + Apple / iTunes`. O registro de proveniência `.metadata.json` inclui `metadata_sources` por campo e `metadata_supplements` com o catálogo, link e campos adicionados. Esses registros também acompanham os metadados normalizados guardados na fila.

A escolha manual na janela de falhas continua explícita: ela troca a fonte do item pelo link Deezer/Apple escolhido e, portanto, esse item deixa de ter origem Spotify para essa regra.

## Validação

Testes cobrem preservação dos campos, conteúdo explícito falso, origem por campo, reutilização de playlists, conexão OAuth em links individuais, falhas de autorização/complementação, exclusão de tokens dos registros e comportamento inalterado dos links de outros serviços. O fluxo de gravação MP3 é verificado com HTTP local e FFmpeg. A adaptação Android é exercitada por testes Python e seus fontes são compilados sem gerar APK.
