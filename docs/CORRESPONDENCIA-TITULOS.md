# Correspondência entre títulos de idiomas diferentes

A comparação mantém letras japonesas, cirílicas e de outros alfabetos, além de normalizar acentos e maiúsculas.

Quando a busca normal no YouTube não encontra um candidato compatível, o motor consulta títulos alternativos de catálogos públicos. É necessário confirmar artista e duração e, adicionalmente, um destes vínculos:

- Mesmo ISRC válido, sem conflito de versão.
- Mesmo álbum, número da faixa e disco, sem ISRCs conflitantes.

A posição da música na playlist não é o número da faixa do álbum e não é usada nessa verificação. Número da faixa isolado, artista/duração isolados e um título traduzido por suposição não são aceitos.

As consultas extras têm limites: busca em Deezer e Apple, até 50 resultados por catálogo, até seis consultas de detalhes Deezer e no máximo dois títulos alternativos. Só são feitas após a busca normal não encontrar correspondência; falhas de conexão ou de verificação do YouTube continuam sendo reportadas sem tentar contorná-las por esse caminho.

A busca alternativa no YouTube usa artista, título confirmado e álbum. Seus resultados continuam sujeitos aos filtros de artista, duração e versão (ao vivo, remix, cover etc.) e às opções existentes de escolha automática ou confirmação. Os metadados originais da música selecionada são preservados; o título alternativo e sua origem ficam registrados no arquivo de proveniência .metadata.json.

Exemplo conferido em 2026-10-15:

- Apple: トーキョーレギー — Masayoshi Takanaka — Seychelles — faixa 2 — 260333 ms.
- Deezer: Tokyo Reggie — Masayoshi Takanaka — Seychelles — faixa 2 — 260000 ms.
- Correspondência confirmada por álbum/faixa, artista e duração. Não foi feita uma nova transferência da playlist inteira.

Fontes públicas do exemplo:
- https://music.apple.com/us/song/1443091880
- https://www.deezer.com/track/1548138282

As alterações estão nos fontes. Nenhum novo APK foi empacotado nesta etapa.

## Verificações adicionais

O motor compartilhado por PC e Android também compara apóstrofos retos/curvos, caracteres de largura completa, acentos e créditos `feat.`/`ft.`. Nomes equivalentes de versões (por exemplo, Remaster/Remastered e Live/ao vivo) são normalizados sem misturar gravações originais, remixes, instrumentais ou regravações.

Nomes localizados de artistas são aceitos por um vínculo adicional estrito: ISRC idêntico, título equivalente e duração compatível. Um nome parecido ou uma transliteração presumida não bastam. O nome alternativo e os artistas originais ficam na proveniência da busca.

Edições Deluxe/Expanded/Anniversary podem receber a mesma preferência de álbum na classificação, mas não permitem deduzir uma tradução pelo número da faixa: edições podem mudar a ordem. O ano original recebe preferência; datas diferentes de relançamento não rejeitam sozinhas um título igual. Para traduzir títulos sem ISRC, anos incompatíveis impedem o vínculo por posição.

Indicações conhecidas de conteúdo explícito e versão limpa são comparadas e conflitos são rejeitados. A ausência da indicação não é tratada como prova de versão limpa. Dados estruturados de música em uploads Topic podem ajudar quando disponíveis, mantendo os filtros de duração e versão; descrições livres e selos de canal não são usados como prova.

Não foi adicionada identificação por impressão digital acústica: ela exigiria áudio de referência comparável e um índice/serviço de identificação, ausentes no projeto. Estes filtros também não resolvem bloqueios de rede, autenticação ou músicas indisponíveis na origem.

## Nomes artísticos verificados

O registro `artist_aliases.py` contém grupos explícitos de nomes comprovados em fontes primárias. O primeiro caso é Antônio Carlos Jobim/Tom Jobim, confirmado pelo Instituto Antonio Carlos Jobim: https://www.jobim.org/jobim/handle/2010/15364?show=full. O motor não cria equivalências apenas porque dois nomes têm o mesmo sobrenome.

No caso relatado, Spotify informa “Garota de Ipanema”, álbum “Inédito”, 242760 ms, enquanto a busca retorna “Tom Jobim | Garota de Ipanema | Inédito”, 243 s, no canal Biscoito Fino: https://www.youtube.com/watch?v=8mcsaEqrbfU. A busca real passou a reconhecer esse candidato em 2026-10-15, sem baixar o áudio nesta verificação. O alias não altera os metadados originais do Spotify e fica registrado como `artist_alias` na proveniência quando usado.
