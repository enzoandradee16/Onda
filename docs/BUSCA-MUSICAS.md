# Busca de músicas — revisão de 15/10/2026

## Escolha de formato no PC — 1.2.0

O botão **Baixar agora** dos resultados abre uma janela com capa, título, artista e álbum, formato e qualidade. O padrão vem das preferências de Álbuns e playlists. MP3 e M4A permitem escolher um bitrate compatível; FLAC e original não exigem essa escolha. **Baixar agora** confirma e inicia; **Adicionar à fila** confirma sem iniciar; **Voltar** ou Esc cancela. A escolha vale para a faixa, sem alterar as preferências salvas. A música é preservada mesmo se novos resultados substituírem a pesquisa. O menu direto Adicionar à fila continua oferecendo os destinos Downloads e Jukebox.

## Uso

- Selecione **Todos** para consultar Deezer e Apple em paralelo. Spotify participa quando a conta ou as credenciais estão disponíveis.
- **Filtros** permite restringir artista, álbum, versão, ano e duração. No PC também há um campo específico de título; no Android o título fica na consulta principal.
- Aspas preservam uma expressão exata. **Exatamente este título** exige igualdade dos termos do título normalizado.
- **Atualizar busca** ignora os resultados armazenados. Cancelar conserva os resultados anteriores e impede a publicação da resposta cancelada.
- **Comparar resultados** mostra os metadados de duas faixas. No Android, toque em Comparar nos dois resultados desejados.
- Na escolha de áudio, confira os motivos, duração e versão. **Lembrar esta escolha** é opcional e não desativa a revalidação. **Versão errada** registra a rejeição; **Desfazer escolhas e rejeições salvas** permite começar novamente. No Android essas alterações são aplicadas ao confirmar a escolha.

Exemplos:

```text
Piero Piccioni Colette
"Colette" artista:"Piero Piccioni" ano:2022 duracao:1:40-1:50
titulo:"Song" artista:"Artist" versao:"Remastered 2022"
Song versao:original
```

Os campos também aceitam `title`, `artist`, `version`, `year`, `duration` e `exact:true`. Sugestões de escrita são apresentadas separadamente; nunca substituem a pesquisa automaticamente.

## Comportamento implementado

| Frente | Comportamento |
|---|---|
| Identidade | Normalização Unicode, acentos, pontuação, caracteres invisíveis, convidados, nomes verificados de artistas, títulos alternativos comprovados e ISRC normalizado. Todos os artistas creditados podem contribuir para a identificação. |
| Edições | Bloqueio de anos de remaster diferentes, remixes identificados, apresentações ao vivo, tipos de edit, regravações e conteúdo explícito/censurado. Rótulos estruturados de versão são preservados. |
| Datas e duração | Datas completas e timestamps do mesmo dia são comparáveis. Ano ou mês isolados não comprovam a mesma edição. Tolerância de duração limitada; valores negativos, booleanos e não finitos não comprovam identidade. |
| Recuperação | Consultas de texto em paralelo, fallback limitado de catálogo/região, paginação Deezer por endpoint fixo e obtenção limitada de detalhes quando um filtro exige data ausente. A busca de áudio mantém tentativas exatas e aliases verificados, com reaproveitamento de consultas e limite de tempo entre tentativas. |
| Classificação | Peso de identidade, penalização de palavras estranhas ao título, agrupamento de duplicatas comprovadas no mesmo álbum e preservação de lançamentos distintos. “Official Visual” e outros rótulos de apresentação não são novas versões. |
| Incerteza | Pontuações próximas pedem confirmação inclusive no modo automático de áudio. Complementação incerta de metadados mantém o registro original em vez de escolher arbitrariamente um álbum. |
| Revalidação | O áudio YouTube é conferido novamente com os dados completos do extrator antes de baixar. Uma escolha manual é comparada com a versão efetivamente escolhida. |
| Interface | Filtros, comparação, prévia existente, abertura da fonte, detalhes da edição, motivos de correspondência/divergência, sugestões e avisos de falha parcial. |
| Desempenho | Até três consultas de catálogo em paralelo, sessões HTTP separadas, cache público de cinco minutos e 128 entradas, cópias defensivas, ausência de cache de falhas e de respostas autenticadas Spotify. |
| Resiliência | Repetição limitada de GETs transitórios, respeito a Retry-After curto e indicação de espera longa; cancelamento entre chamadas e durante backoff; respostas antigas descartadas. Requisições já enviadas encerram pelo timeout da conexão. |
| Escolhas | Até 500 decisões locais, com validade de 90 dias, sem credenciais. Uma escolha salva só é reutilizada entre candidatos novamente compatíveis. |
| Diagnósticos | `music_search.diagnostics()` fornece contadores agregados de consultas, cache, erros, cancelamentos, tempo médio e tipos de seleção. Não contém consultas, URLs, nomes ou tokens. |

## Validação

- Rodada completa: **185 testes aprovados**, incluindo Tk e FFmpeg; após o último reforço de revalidação, **56 testes direcionados aprovados**.
- Dois testes de instrumentação de busca aprovados (motor e interface); o teste do motor foi repetido com sucesso após a sincronização final. Testes unitários Android e lint concluídos.
- Portátil aberto com perfil temporário; 15 módulos conferidos byte a byte. No APK final, 18 módulos compilados (raízes normal e compartilhada) conferidos contra os fontes finais. Assinatura original do APK confirmada e SHA-256 atualizado.
- Testes de regressão de versões, filtros, Unicode, aliases, datas, durações inválidas, ISRC, paginação, cache, falhas parciais, cancelamento, escolhas e revalidação.
- Testes de interface do PC e fluxo real com servidor local, FFmpeg, conversão, tags e capa.
- Testes do motor compartilhado e do diálogo de filtros no emulador Android API 36, com APK ARM64 sob tradução.
- Busca pública real por Piero Piccioni / Colette: resultados Deezer e Apple; equivalência do remaster confirmada por ISRC.
- Download real de Colette concluído em MP3: 105,77 s, 1.837.144 bytes, título e capa gravados.

## Limites

### Revisão de sessão e carga do YouTube — 15/10/2026

- As consultas alternativas da mesma música reutilizam uma instância do extrator, sua configuração e seus cookies. A sessão obtida durante a busca acompanha a extração e o download, inclusive quando o usuário precisa escolher uma versão.
- Cookies explicitamente configurados no PC também são passados à busca. A separação de sessão do YouTube no Android permanece no adaptador.
- Revisão de desempenho: a fila voltou a respeitar os downloads simultâneos configurados também para YouTube e áudio de Spotify, Deezer e Apple. No PC, aumentar o limite durante a execução abre as novas vagas imediatamente; reduzir aguarda os trabalhos ativos terminarem. Android mantém seu limite configurável de 1 a 4 e PC de 1 a 15.
- Foram removidas as esperas fixas de 1 segundo por requisição e 5 segundos por download, bem como a redução forçada de fragmentos simultâneos. O reaproveitamento de sessão continua aplicado.
- Testes cobrem fila mista, avanço após conclusão, sessão nas buscas alternativas e escolhas manuais. O teste completo com servidor local exige o cookie criado na busca e recusa o download se a sessão for perdida. Os 24 testes unitários Android passaram; APK compilado e assinado com o certificado original.
- Colette (105,77 s), Amore in fiore (127,15 s) e Illusione perfetta (164,57 s) concluíram downloads reais nesta revisão, com capa e tags verificadas. Os vídeos são os mesmos identificadores do log enviado. O erro HTTP 429 havia sido reproduzido antes dela; não há garantia de ausência de limitações futuras do serviço.

Metadados não permitem garantir que todo catálogo ou upload represente a masterização correta. Casos sem evidência suficiente continuam exigindo escolha ou sendo recusados. A disponibilidade regional, a autenticação Spotify e o acesso ao YouTube dependem dos serviços e da conexão. Não houve teste desta revisão em aparelho Android físico. A versão permanece 1.1.2; esta revisão não publica a release 1.1.3.

### Correção das preferências automáticas e custo de consultas — 15/10/2026

- A seleção automática de versão volta a escolher o maior resultado aprovado, inclusive em empates e em FLAC. Sem a opção automática, a confirmação de ambiguidades permanece. Versões incompatíveis continuam recusadas.
- A opção de metadados automáticos é aplicada ao desempate de candidatos compatíveis; sem evidência suficiente, não abre pergunta no meio de uma fila automática.
- Dados completos do Spotify não provocam pesquisas adicionais somente por gênero ausente. Metadados originais e proveniência continuam preservados.
- Títulos equivalentes confirmados por catálogo são comparados aos resultados já recebidos antes de realizar outra busca no YouTube. A evidência de aliases confirmados acompanha a revalidação antes do download.
- Busca limita repetições HTTP e do extrator a uma por tentativa. Recuperação de URL HTTP 403 e teste de formatos alternativos permanecem; bloqueios do serviço não podem ser eliminados por estas correções.
- Validação: suíte completa com 552 testes, dos quais 412 executados com sucesso e 140 ignorados pelas condições dos testes. Teste de concorrência confirmou cinco trabalhadores em paralelo com preferências automáticas transmitidas. Download real isolado de Colette completou em 8,76 s, com MP3, tags e capa; esta medição não é uma comparação controlada com versões anteriores.

Validação final desta correção: 24 testes unitários Android e lint aprovados; teste SearchMatchingTest aprovado no emulador API 36 com o motor empacotado. Portátil validado por autoteste; APK assinado com o certificado original e hashes locais atualizados. Nenhuma release preparada ou publicada.

### Recuperação de HTTP 403 no áudio

O download do YouTube tem no máximo três tentativas no total para áudio. Após a primeira recusa, renova os links e prioriza HLS do mesmo vídeo, excluindo os formatos já recusados. Se o HTTP 403 persistir, aguarda entre um e dois segundos antes da última tentativa. Downloads normais não aguardam e a quantidade de trabalhos simultâneos permanece configurável. Outros erros, falta de formatos ou arquivos já publicados não provocam novas tentativas por essa regra.
