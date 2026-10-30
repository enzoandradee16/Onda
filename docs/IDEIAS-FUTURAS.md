# Ideias futuras do ONDA

Anotadas em 29/10/2026 a pedido do responsável pelo projeto. Reúnem propostas para avaliação e iniciativas em fase de protótipo, identificadas abaixo.

## Controle entre ONDA PC e Android

Prioridade destacada pelo responsável. Experiência inspirada no Spotify Connect: usar o ONDA no celular para controlar a reprodução do ONDA no computador.

Em 30/10/2026, foi iniciado um [protótipo para testes](CONTROLE-REMOTO.md), com pareamento manual, música atual e controles de pausa, anterior, próxima e volume. Os demais itens abaixo continuam como evolução proposta.

A etapa seguinte integra capa, posição ajustável, fila e controles à barra de reprodução, ao player expandido e à sessão de mídia Android, com notificação e manutenção da conexão em segundo plano. Os efeitos remotos e o pareamento simplificado continuam pendentes.

- Descobrir e conectar os dispositivos, com autorização do usuário.
- Mostrar a música atual, capa, posição e estado da reprodução.
- Controlar pausa, retomada, próxima música, anterior e volume.
- Consultar e gerenciar a fila remotamente.
- Ajustar os efeitos do ONDA pelo celular, mantendo o processamento e a saída de áudio no computador.

O controle remoto é uma integração própria entre as versões do ONDA. Transmitir o áudio entre os dispositivos seria uma possibilidade separada a avaliar.

## Spotify

Ampliar a integração existente para facilitar o acesso à biblioteca e a organização das músicas.

- Exibir as playlists da conta sem precisar copiar links.
- Salvar descobertas em playlists do Spotify mediante ação do usuário.
- Comparar playlists com arquivos locais, indicando correspondências, ausências, duplicatas e versões que precisam de revisão.
- Avaliar controles de reprodução do Spotify dentro do ONDA.

Conferir as permissões e os limites da API antes de definir o escopo. A proposta não inclui contabilizar a reprodução local com efeitos como minutos ouvidos no Spotify.

## MusicBrainz + AcoustID

Ampliar o uso parcial de MusicBrainz existente no ONDA com identificação acústica via AcoustID.

- Identificar arquivos pelo áudio, inclusive quando o nome ou as tags estiverem incompletos.
- Sugerir a gravação e a edição correspondentes, distinguindo versões quando os dados permitirem.
- Auxiliar na revisão de título, artista, álbum e outros metadados.
- Mostrar as correspondências para confirmação antes de alterar arquivos.

Avaliar o uso de Chromaprint para gerar as impressões digitais, as dependências nas duas plataformas e os requisitos de acesso aos serviços.
