# Aliases de artistas

PC e Android usam o mesmo motor. Os aliases revisados incluídos no programa continuam disponíveis sem rede. Se a busca normal no YouTube não encontra candidato compatível, o motor consulta o MusicBrainz e tenta reconhecer nomes artísticos, nomes legais e nomes em outros alfabetos.

## Confirmação

- Exige título, artista, álbum e duração conhecidos. Nome parecido sozinho não basta.
- A gravação deve ter título e versão compatíveis, duração dentro da tolerância e o mesmo álbum; um ISRC explicitamente retornado pode confirmar a gravação.
- O artista precisa ser o intérprete principal da gravação. O perfil consultado deve confirmar o nome de origem entre o nome principal ou os aliases dos tipos Artist name/Legal name. Search hints e sugestões de grafia não são usados como equivalência.
- Vários IDs de artista compatíveis resultam em recusa da associação automática. Quando a busca da gravação não indexa o nome alternativo, uma busca de artista é seguida da verificação da gravação pelo ID, nunca aceita isoladamente.
- Os filtros de título, duração, conteúdo explícito e versão do download continuam ativos. A busca reutiliza os candidatos YouTube já obtidos e, se necessário, faz no máximo duas buscas adicionais por nomes confirmados.
- Os metadados originais não são renomeados. Quando um alias ajuda a escolher o áudio, nome original, alias e link do MusicBrainz ficam na proveniência `artist_alias`.

## Cache e disponibilidade

No PC, o cache é `%LOCALAPPDATA%/Onda/artist-aliases.sqlite3`; no Android, fica no diretório privado do aplicativo. Equivalências duram até 30 dias; ausência de correspondência é guardada por 24 horas. Há limite de 2000 entradas e os dados vencidos são descartados ao gravar.

Sem identidade estável externa, a confirmação só vale para o contexto da gravação consultada. Reutilização em outras músicas do mesmo artista só ocorre quando o perfil MusicBrainz contém um link para o mesmo ID público de artista Spotify informado pelos metadados. Tokens, credenciais e cookies não são enviados ao MusicBrainz nem entram nesse cache.

Consultas usam User-Agent identificável, intervalo mínimo de 1,1 segundo compartilhado por processos, espera local limitada, timeout, tamanho máximo da resposta e recuo em HTTP 429/503. São no máximo quatro consultas MusicBrainz por tentativa. Falhas transitórias não viram uma associação nem um resultado negativo persistente; a busca existente continua disponível.

O MusicBrainz é uma base comunitária e pode não conter determinada gravação/alias. A consulta online de validação em 2026-10-15 recebeu HTTP 503 (servidor ocupado); por isso a confirmação funcional nesta etapa usa respostas simuladas, além das verificações de cache, concorrência e integração. Não é uma promessa de resolver toda variação de nome.

Documentação do serviço:
- https://musicbrainz.org/doc/MusicBrainz_API
- https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- https://musicbrainz.org/doc/Aliases

Nenhum novo APK foi gerado nesta etapa.
