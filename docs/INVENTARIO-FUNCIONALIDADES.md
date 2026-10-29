# Inventário de funcionalidades do ONDA

Referência de recursos existentes, diferenças entre plataformas e localização das implementações.

> **Atualização de reprodução:** Efeitos e Jukebox agora compartilham a tela, a música, a fila e o player nas duas plataformas. Os ajustes podem funcionar juntos. Consulte [Reprodução unificada](REPRODUCAO-UNIFICADA.md) para o comportamento e a migração atualizados; as referências antigas a duas abas/sessões independentes abaixo descrevem a estrutura anterior.

| Revisão | Aplicativo | Windows | Android |
| --- | --- | --- | --- |
| 27/10/2026 | 1.2.4 | 1.2.4.0 | Código 31 |

**Consulta rápida:** [Funcionalidades](#sec-02) · [Diferenças entre plataformas](#sec-17) · [Limitações](#sec-20) · [Configurações](#sec-22) · [Índice técnico](#sec-23)

> Antes de propor uma adição, confira o recurso e a implementação citada. Este documento registra uma revisão estática do código; não substitui testes de funcionamento.

<details>
<summary><strong>Sumário completo</strong></summary>


**Contexto**

- [1. Base e alcance da revisão](#sec-01)

**Funcionalidades do aplicativo**

- [2. Navegação e organização](#sec-02)
- [3. Pesquisa de músicas e identidade da gravação](#sec-03)
- [4. Links, plataformas e extração](#sec-04)
- [5. Formatos, qualidade e publicação de arquivos](#sec-05)
- [6. Fila de downloads](#sec-06)
- [7. Histórico e arquivos baixados](#sec-07)
- [8. Álbuns e playlists](#sec-08)
- [9. Reprodução compartilhada: Efeitos e Jukebox](#sec-09)
- [10. Letras](#sec-10)
- [11. Imagens, carrosséis e prévias](#sec-11)
- [12. Conversor local](#sec-12)
- [13. Editor de áudio e metadados](#sec-13)

**Personalização e operação**

- [14. Aparência, idioma e acessibilidade](#sec-14)
- [15. Configurações, dados e privacidade](#sec-15)
- [16. Preparação, cache e desempenho](#sec-16)
- [17. Integrações específicas e atualização](#sec-17)

**Site e distribuição**

- [18. Site](#sec-18)
- [19. Testes, construção e distribuição](#sec-19)

**Manutenção e referência técnica**

- [20. Limitações e pontos que exigem conferência futura](#sec-20)
- [21. Como manter este documento](#sec-21)
- [22. Catálogo de configurações do código atual](#sec-22)
- [23. Índice técnico de módulos, classes e funções](#sec-23)
- [24. Site e infraestrutura de construção](#sec-24)
- [25. Cobertura e evidências de teste existentes](#sec-25)

</details>

---

<a id="sec-01"></a>

## 1. Base e alcance da revisão

**Base Git:** `5402863` — `540286310731d00de60ed275d8ba3deb66590031`.
- **Método:** revisão estática das interfaces Qt/QML e Compose, controladores, motores Python compartilhados, preferências, testes e documentação; inventário técnico extraído dos fontes. Não representa uma nova execução de todos os testes nem comprova disponibilidade atual de serviços externos.
- **Escopo:** aplicativo Windows, aplicativo Android, site, persistência, integrações, construção e distribuição. Dependências vendorizadas, binários, anexos, caches e cópias do aplicativo empacotado não são novas funcionalidades.
- **Leitura dos estados:** “implementado” significa que há código correspondente; “condicional” depende de origem, permissões, metadados, formato ou sistema. Um método interno ou opção antiga persistida não significa que existe um botão disponível.
- **Interface de PC de referência:** Qt/QML (`qt_desktop_ui.py`, `qt_workspace_ui.py`, `qml/`). O repositório também conserva a implementação Tk e módulos reutilizados por ela; seus controles não devem ser presumidos como presentes no Qt.
- **Sem alterações no funcionamento:** esta revisão acrescenta documentação; não recompila, publica ou modifica preferências do usuário.

---

<a id="sec-02"></a>

## 2. Navegação e organização

| Área | PC | Android | Implementação principal |
| --- | --- | --- | --- |
| Pesquisa de músicas | Página própria | Pesquisar na barra inferior | `Onda/qml/LibraryView.qml`; `Android/.../MainActivity.kt` |
| Entrada de links | Página Links | Adicionar links pelo + de Downloads | `Onda/qml/DownloadsView.qml`; `Android/.../DownloadsHome.kt` |
| Fila de downloads | Página Fila | Downloads, Em andamento | Mesmos componentes acima |
| Histórico | Página Histórico | Downloads/Concluídos e ferramentas relacionadas | `LibraryView.qml`; `HistoryPage.kt`; `DownloadsHome.kt` |
| Álbuns e playlists | Página própria | Menu Mais, Salvos/Importar | `LibraryView.qml`; `CollectionsPage.kt` |
| Reprodução | Efeitos/Jukebox dentro de Reprodução e efeitos | Reprodução com Efeitos/Jukebox | `ToolView.qml`; `JukeboxView.qml`; `MainActivity.kt`; `Jukebox.kt` |
| Imagens, Conversor, Editar metadados | Páginas próprias | Menu Mais | `ToolView.qml`; `ImagesPage.kt`; `VideoConverterPage.kt`; `MetadataPage.kt` |
| Configurações e Aparência | Janelas próprias | Ícones de configurações e aparência | `SettingsPopup.qml`; `SettingsWindow.kt`; `AppearanceWindow.kt` |

Nos caminhos abreviados `Android/.../`, o diretório é `Android/app/src/main/java/br/com/onda/mobile/`. O índice técnico ao final oferece links completos.

- Ordem e visibilidade configuráveis das abas elegíveis; restauração da ordem padrão.
- Android permite ordenar a barra inferior e o menu Mais; Mais permanece no final. Navegação por gestos respeita a ordem.
- PC possui barra lateral, atalhos, menus de contexto e persistência de posição/tamanho da janela.
- Estados vazios orientam o próximo passo; menus Mais ações concentram ações secundárias.

---

<a id="sec-03"></a>

## 3. Pesquisa de músicas e identidade da gravação

**Implementado nas duas versões, com acesso ao Spotify condicionado à configuração/conexão.**

### Consulta e filtros

- Busca nos catálogos Deezer, Apple/iTunes e Spotify; opção Todos reúne provedores disponíveis.
- Pesquisa por texto ou link compatível; Enter usa o mesmo fluxo do botão de pesquisa.
- Filtros de consulta: `artista:`, `album:`, `titulo:`, `versao:`, `ano:`, `duracao:` e `exata:`; equivalentes em inglês e frases entre aspas. Exemplos: `ano:2020-2022`, `duracao:3:00-4:00`, `exata:sim`.
- Validação de consulta, ordenação por relevância, normalização de nomes, aliases de artistas, cache limitado e cancelamento.

### Resultados e ações

- Comparação de versões e detalhes de edição para reduzir confusão entre original, rádio, ao vivo, remix, acústica e outras gravações.
- Cards com capa, título, artista, álbum, plataforma e data de lançamento quando fornecidos ou recuperados; preenchimento de dados ausentes em segundo plano.
- Ações de baixar, adicionar à fila, ouvir prévia, abrir no catálogo, copiar link e comparar resultados conforme a tela/plataforma.
- Destinos distintos: fila de downloads, fila de Efeitos e fila do Jukebox; adicionar uma faixa não precisa abrir o painel da fila.

### Correspondência e origem do áudio

- Janela de formato/qualidade por faixa no PC; seleção explícita vale para aquela solicitação. O Android também possui diálogo de download por faixa.
- Escolha manual, automática ou lembrada de metadados/versão. Correspondências lembradas são revalidadas; relevância de busca não equivale a autorização para baixar outra gravação.
- Spotify/Apple/Deezer fornecem metadados; não há exportação do áudio protegido desses catálogos. MP3/M4A usam correspondência no YouTube; FLAC possui rota própria de fonte lossless.

<details>
<summary>Referências de implementação</summary>

[music_search.py](../Onda/music_search.py), [metadata.py](../Onda/metadata.py), [matching.py](../Onda/matching.py), [record_identity.py](../Onda/record_identity.py), [edition_evidence.py](../Onda/edition_evidence.py), [search_choices.py](../Onda/search_choices.py), [artist_aliases.py](../Onda/artist_aliases.py), [catalog_details.py](../Onda/catalog_details.py), [LibraryView.qml](../Onda/qml/LibraryView.qml), [TrackDownloadDialog.kt](../Android/app/src/main/java/br/com/onda/mobile/TrackDownloadDialog.kt), [TrackMatches.kt](../Android/app/src/main/java/br/com/onda/mobile/TrackMatches.kt).

</details>

---

<a id="sec-04"></a>

## 4. Links, plataformas e extração

### Entrada e identificação

- Entrada de vários links; adição sem iniciar ou download imediato.
- Validação HTTP/HTTPS, endereço e porta, rejeição de credenciais embutidas e tratamento de redirecionamentos Google compatíveis.
- Reconhecimento de links copiados, sujeito às restrições da área de transferência do sistema; não implica download automático de qualquer conteúdo copiado.
- Identificação visual por domínio e ícones de plataformas nos cards; domínio desconhecido recebe identidade genérica de link. Imagens possuem identificação própria.

### Extração de publicações

- Tratamento dedicado para Instagram, TikTok, Kwai e X/Twitter, combinado aos extratores yt-dlp/gallery-dl e caminhos genéricos de mídia.
- Links curtos e domínios alternativos são tratados pelos resolutores apropriados; Kwai inclui `kwai.com` e `kwai-video.com`.
- Publicações com fotos, vídeos ou carrosséis permitem seleção dos itens; seleção inicial de todos e maior qualidade social são configuráveis.
- Modos de baixar fotos do carrossel ou publicação com fotos e vídeos originais; preservação da ordem e informações disponíveis.

### Acesso e disponibilidade

- Cookies importados e sessão do YouTube ajudam em origens que exigem acesso; não removem DRM ou restrições da conta/servidor.
- Links indisponíveis devem resultar em erro, sem substituir o vídeo solicitado por uma recomendação aleatória.

**Atenção:** possuir ícone de uma plataforma não garante extração de todos os seus links. TIDAL, Qobuz, Bandcamp, MusicBrainz, Facebook, SoundCloud, Vimeo, Dailymotion, Twitch, Reddit, Pinterest e Telegram constam no registro de identidades; a capacidade real depende da rota de extração e do conteúdo.

<details>
<summary>Referências de implementação</summary>

[engine.py](../Onda/engine.py), [media_links.py](../Onda/media_links.py), [media_picker.py](../Onda/media_picker.py), [media_selection.py](../Onda/media_selection.py), [social_media.py](../Onda/social_media.py), [instagram_media.py](../Onda/instagram_media.py), [tiktok_media.py](../Onda/tiktok_media.py), [kwai.py](../Onda/kwai.py), [twitter_media.py](../Onda/twitter_media.py), [clipboard_links.py](../Onda/clipboard_links.py), [platform_info.py](../Onda/platform_info.py), `settings_schema/platforms.json`, [mobile_backend.py](../Android/app/src/main/python/mobile_backend.py).

</details>

---

<a id="sec-05"></a>

## 5. Formatos, qualidade e publicação de arquivos

### Formatos e qualidade

- Vídeo em melhor qualidade/MKV ou MP4; limites de resolução e FPS conforme disponibilidade.
- Áudio original sem recodificar, MP3, M4A/AAC e FLAC; bitrate apenas onde aplicável.
- Motor oferece resoluções até 2160p/4K e FPS original, 24, 30, 60 e 120 como limites de download; não inventa quadros ou resolução ausentes na origem.
- MP3: 320, 256, 192, 128 e 96 kbps; M4A: 256, 192, 128 e 96 kbps no contrato compartilhado.
- FLAC por catálogo Monochrome quando houver correspondência compatível, seleção de versões, tentativas com espera progressiva e validação antes da publicação.

### Organização e gravação

- Normalização opcional de próximos downloads de áudio: duas passagens, alvo de −16 LUFS e pico verdadeiro de −1,5 dBTP; silêncio é tratado separadamente.
- Pasta de destino, nomes e organização configuráveis, incluindo estruturas por álbum, artista/ano/álbum, gênero/artista/álbum e formato/artista/álbum.
- Modelos de nomes com faixa/disco/artista/título conforme os dados presentes; subpastas de coleções.
- Política para arquivo existente: perguntar, ignorar/substituir/manter cópia conforme o fluxo e as opções oferecidas.
- Arquivos temporários de trabalho e publicação final separados; validações de tamanho, mídia ou duração dependem do caminho. Não há garantia genérica de “qualquer arquivo validado por qualquer método”.

<details>
<summary>Referências de implementação</summary>

[engine.py](../Onda/engine.py), [audio_quality.py](../Onda/audio_quality.py), [lossless_source.py](../Onda/lossless_source.py), [output_rules.py](../Onda/output_rules.py), [file_output.py](../Onda/file_output.py), [tagging.py](../Onda/tagging.py), [audio_library.py](../Onda/audio_library.py), [image_output.py](../Onda/image_output.py).

</details>

---

<a id="sec-06"></a>

## 6. Fila de downloads

### Gerenciamento e reorganização

- Fila persistente com opções por item e identificação estável do trabalho.
- Iniciar, parar, pausar/retomar, cancelar, remover, limpar e tentar novamente conforme o estado do item.
- Selecionar itens/visíveis, ordenar pendentes, mover acima/abaixo ou priorizar; operações ativas são protegidas durante reorganização.
- Arraste do card inteiro, com elevação e deslocamento dos vizinhos antes de soltar; rolagem automática nas bordas.
- PC: gesto de mouse sem a página tomar o arraste e movimento por teclado. Android: toque prolongado no card e marcador compacto sobreposto, sem reservar uma coluna larga.
- Ações de desfazer alterações da fila onde oferecidas, com preservação de trabalhos ativos.

### Informações e execução

- Busca, filtros por estado, informações e ações individuais/coletivas; visualização compacta/completa e tamanho dos cards.
- Etapa atual, progresso, velocidade, bytes/tamanho, estimativas de espaço, tempo decorrido/restante e contagens quando disponíveis.
- Execução simultânea: PC de 1 a 15, Android de 1 a 4; confirmações de escolhas são serializadas.

### Retomada e agendamento

- Recuperação de trabalhos interrompidos e progresso aproximado; ação para retomar interrompidos. Retomar arquivos e retomar a fila ao abrir são preferências diferentes.
- Reutilização de arquivos parciais quando a origem permite; transferência direta usa Range/If-Range e validadores disponíveis para não unir versões diferentes de um arquivo.
- Agendamento diário por janela HH:MM, inclusive atravessando a meia-noite. PC precisa permanecer ligado e aberto; Android usa WorkManager e está sujeito ao sistema.
- Detecção de links duplicados na fila/histórico considera identidade, formato e opções; confirmação pode ser desativada. Não compara o áudio por semelhança sonora.

### Duplicados, conclusão e falhas

- Ação ao terminar: nenhuma, som, notificação ou ambos; desligar PC é exclusivo do Windows e exige confirmação/contagem.
- Relato de falhas com causa provável e ações úteis, como tentar novamente, atualizar link ou verificar acesso; exportação de lista de falhas conforme o fluxo.

**PC:** Links mostra também os trabalhos adicionados por essa aba, sincronizados com a fila completa, sem duplicar os downloads.

**Android:** Downloads usa Em andamento/Concluídos e botão + para links. Serviço em primeiro plano e controles de notificação; opção Somente Wi-Fi com política de pausar ou concluir ativos ao perder Wi-Fi.

<details>
<summary>Referências de implementação</summary>

[qt_workspace_ui.py](../Onda/qt_workspace_ui.py), [queue_control.py](../Onda/queue_control.py), [queue_filter.py](../Onda/queue_filter.py), [queue_undo.py](../Onda/queue_undo.py), [queue_timing.py](../Onda/queue_timing.py), [parallel_queue.py](../Onda/parallel_queue.py), [size_estimate.py](../Onda/size_estimate.py), [download_feedback.py](../Onda/download_feedback.py), [failure_report.py](../Onda/failure_report.py), [DownloadsView.qml](../Onda/qml/DownloadsView.qml), [QueueDragHandle.qml](../Onda/qml/QueueDragHandle.qml), [DownloadsHome.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadsHome.kt), [QueueRunner.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt), [QueueControls.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt), [QueueDragHandle.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt), [DownloadService.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt), [DailyUse.kt](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt), [DownloadSchedule.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt).

</details>

---

<a id="sec-07"></a>

## 7. Histórico e arquivos baixados

### Consulta do histórico

- Registro de downloads e resultados locais compatíveis, com data, formato, caminho, origem/plataforma e detalhes disponíveis.
- Pesquisa e filtros Todos, Áudio, Vídeo e Imagens; cards/lista e tamanhos próprios.
- Abrir arquivo, abrir pasta quando disponível, baixar novamente a partir da origem, enviar áudio para Efeitos ou editar metadados.

### Ações e remoção

- Seleção de vários áudios para edição em lote; ações secundárias em menu.
- Remover somente um registro, sem apagar o arquivo; limpar histórico também preserva os arquivos.
- Desfazer remoção individual por 8 segundos; não confundir com desfazer reorganização da fila.

### Prévias e informações locais

- Prévias de imagens locais e grupos/carrosséis vinculados ao download, com navegação e compartilhamento.
- Dados/capas de áudio podem ser completados lendo tags e arquivos de capa vizinhos.
- Android usa URIs/permissões do sistema; itens antigos sem origem não ganham plataforma inferida apenas pelo nome.

<details>
<summary>Referências de implementação</summary>

[library.py](../Onda/library.py), [history_details.py](../Onda/history_details.py), [history_origin.py](../Onda/history_origin.py), [qt_workspace_ui.py](../Onda/qt_workspace_ui.py), [LibraryView.qml](../Onda/qml/LibraryView.qml), [HistoryPage.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryPage.kt), [HistoryRows.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryRows.kt), [HistoryFolders.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt), [HistoryImageGallery.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryImageGallery.kt), [OndaStore.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt).

</details>

---

<a id="sec-08"></a>

## 8. Álbuns e playlists

### Carregamento e seleção

- Carregar coleções suportadas por URL e importar TXT, M3U e CSV/Exportify; exportar listas em TXT/M3U.
- Cards com capa e metadados; completar capa/data ausente quando a fonte permite.
- Carregar vira Cancelar durante a consulta e Atualizar quando a mesma coleção já está carregada.
- Buscar na lista, selecionar todas/visíveis, desmarcar e baixar/adicionar selecionadas à fila de downloads.
- Formato e qualidade próprios de coleções; limite de itens configurável.

### Conferência e organização

- Conferir correspondências/versões e comparar com arquivos locais; identificar e adicionar ausentes.
- Exibir carregadas/total quando conhecido ou total não confirmado; conferir os links com TXT/M3U/CSV sem substituir a coleção.
- Ações secundárias em Mais ações e ações por faixa.
- Android oferece biblioteca local de coleções salvas, abrir/remover coleção salva e visualização de lista.
- Efeitos/Jukebox recebem links de coleções nos seus próprios campos e nas pesquisas das filas. Os antigos botões de enviar uma coleção a esses players na página Álbuns e playlists não são o fluxo principal atual.

### Integração com reprodução e limites

- Coleção pública Spotify pode vir incompleta; autenticação e importação de CSV são alternativas condicionadas às permissões e dados disponíveis.

<details>
<summary>Referências de implementação</summary>

[playlist_import.py](../Onda/playlist_import.py), [playlist_files.py](../Onda/playlist_files.py), [playlist_sync.py](../Onda/playlist_sync.py), [playlist_options.py](../Onda/playlist_options.py), [album_import.py](../Onda/album_import.py), [spotify_public.py](../Onda/spotify_public.py), [LibraryView.qml](../Onda/qml/LibraryView.qml), [CollectionsPage.kt](../Android/app/src/main/java/br/com/onda/mobile/CollectionsPage.kt), [CollectionsLibrary.kt](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt), [PlaylistLocalFiles.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaylistLocalFiles.kt), [playback_input.py](../Onda/playback_input.py).

</details>

---

<a id="sec-09"></a>

## 9. Reprodução compartilhada: Efeitos e Jukebox

### Controles e independência dos modos

- Música local, busca de música e links de faixa/álbum/playlist; filas separadas por modo.
- Selecionar música em uma aba não deve substituir a seleção da outra; iniciar um player pausa o concorrente, preservando a posição aplicável.
- Reproduzir/pausar, avançar, retroceder, buscar posição, letra/microfone e acesso à fila.
- Painéis de fila com capa, título, artista, duração e estado de preparação por música; falhas com motivo, orientação e nova tentativa sem iniciar áudio.

### Filas de reprodução

- Busca dentro da fila aceita texto e os mesmos links de reprodução; adicionar sem abrir automaticamente o painel.
- Remover, limpar, reorganizar, selecionar e reproduzir uma faixa; faixas já tocadas permanecem para permitir retroceder.
- Repetição e aleatório por fila; reprodução normal e modo infinito têm regras diferentes. Não tratar saltos internos do Jukebox como troca de faixa da fila.
- Transição gradual e tempo de sobreposição configurável entre faixas nos caminhos compatíveis.

### Transições e preparação

- Preparação antecipada de próximas músicas; resultado/cache depende do modo, parâmetros e disponibilidade de áudio.
- Timer de sono e controles de tempo/troca oferecidos pelo player.
- Restaurar música, posição e filas ao reabrir sem iniciar áudio automaticamente; referências inválidas podem não ser recuperáveis.

### Sessão e integração

- Capas e metadados reaproveitados; letras acompanham a gravação e posição do player correspondente.
- Integração com controles de mídia do sistema: Windows em ambos os modos; Android com sessões/serviços próprios.

**PC:** barras na janela principal, miniplayers de Efeitos/Jukebox com capa, letras, fila e volume; podem permanecer visíveis com a principal minimizada. Preferência para minimizar ao abrir miniplayer, fixar/restaurar/fechar e arraste da janela conforme os controles.

**Android:** barra compacta persistente, cor derivada da capa com aparência de vidro, player expandido com capa e tela de letra. Volume principalmente pelo sistema; não presumir os botões do miniplayer Windows nessa barra.

<details>
<summary>Referências de implementação</summary>

[playback_input.py](../Onda/playback_input.py), [playback_session.py](../Onda/playback_session.py), [playback_controls.py](../Onda/playback_controls.py), [qt_workspace_ui.py](../Onda/qt_workspace_ui.py), [qt_jukebox_ui.py](../Onda/qt_jukebox_ui.py), [windows_media.py](../Onda/windows_media.py), [EffectsQueueDrawer.qml](../Onda/qml/EffectsQueueDrawer.qml), [MiniPlayer.qml](../Onda/qml/MiniPlayer.qml), [PlaybackSessions.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt), [AndroidPlaybackSurface.kt](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt), [EffectsPlaybackBar.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt), [EffectsQueuePanel.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt), [EffectsPlaybackService.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt), [JukeboxService.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt), [AlbumGlass.kt](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt).

</details>

### 9.1 Efeitos

- Slowed/Sped Up por velocidade, Reverb, presets e opção de manter o tom ao alterar a velocidade.
- Reprodução integral com navegação, estados de preparação e exportação da música processada nos formatos oferecidos.
- PC processa áudio em tempo real no player; Android usa renderização e pré-processamento/cache dos parâmetros correspondentes. Não descrever os dois mecanismos como idênticos.
- Mudança de velocidade/reverb/pitch invalida a preparação que não corresponde aos novos parâmetros.
- Cancelamento e prevenção de resposta antiga substituir a faixa/solicitação mais recente.

<details>
<summary>Referências de implementação</summary>

[audio_tools.py](../Onda/audio_tools.py), [effects_worker.py](../Onda/effects_worker.py), [qt_workspace_ui.py](../Onda/qt_workspace_ui.py), [ToolView.qml](../Onda/qml/ToolView.qml), [OndaViewModel.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt).

</details>

### 9.2 Jukebox infinito

- Análise musical para saltos entre trechos compatíveis, visualização circular de conexões e trajetória reproduzida.
- Ajuste de variação e suavidade da transição; contagem de saltos e tempo ouvido.
- Reprodução normal opcional, distinta do modo infinito.
- Preparação da próxima música, navegação da fila e limites/timer por faixa conforme os controles.
- Equalizador de dez bandas, frequência/ganho/Q, pré-amplificação, ativar/desativar, presets e restauração. É próprio do caminho PCM do Jukebox.
- Análise reaproveitada quando compatível, progresso e cancelamento.

<details>
<summary>Referências de implementação</summary>

[jukebox.py](../Onda/jukebox.py), [jukebox_audio.py](../Onda/jukebox_audio.py), [jukebox_stream.py](../Onda/jukebox_stream.py), [jukebox_equalizer.py](../Onda/jukebox_equalizer.py), `settings_schema/equalizer_presets.json`, [qt_jukebox_ui.py](../Onda/qt_jukebox_ui.py), [JukeboxView.qml](../Onda/qml/JukeboxView.qml), [EqualizerPopup.qml](../Onda/qml/EqualizerPopup.qml), [Jukebox.kt](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt), [JukeboxTimer.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt), [JukeboxEqualizerDialog.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxEqualizerDialog.kt).

</details>

---

<a id="sec-10"></a>

## 10. Letras

### Busca e escolha da letra

- Consulta online LRCLIB usando título, artista, álbum e duração; leitura das informações locais para completar a consulta.
- Consulta exata e fallback de pesquisa; seleção automática compatível, com rejeição de títulos/artistas distantes e versões diferentes.
- Preferência por duração próxima e sincronização; não escolher indiscriminadamente o primeiro resultado.
- Alternativas manuais quando solicitadas, tratamento de letra ausente ou gravação instrumental.

### Formatos e sincronização

- Letra simples, LRC sincronizado e suporte a marcação por palavra quando fornecida/validada; ausência de sincronização não é inventada.
- Importação de TXT/LRC e associação à gravação; incorporação de letra no editor de áudio, com limites de tamanho.
- Janela/tela de letras, destaque da linha atual, rolagem e animações configuráveis; cores da capa no player Android.

### Exibição e controles

- Letra no player expandido e tela cheia no Android; acesso pelo ícone de microfone nas barras.
- Mudanças de posição/velocidade refletem no tempo de letra correspondente.

<details>
<summary>Referências de implementação</summary>

[lyrics_service.py](../Onda/lyrics_service.py), [synced_lyrics.py](../Onda/synced_lyrics.py), [LyricsWindow.qml](../Onda/qml/LyricsWindow.qml), [AnimatedLyric.qml](../Onda/qml/AnimatedLyric.qml), [MicrophoneButton.qml](../Onda/qml/MicrophoneButton.qml), [LyricsPreviewCard.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricsPreviewCard.kt), [LyricTimeline.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt), [LyricAnimation.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricAnimation.kt), [LyricsButton.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricsButton.kt), [JukeboxLyricsButton.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxLyricsButton.kt).

</details>

---

<a id="sec-11"></a>

## 11. Imagens, carrosséis e prévias

### Galerias e navegação

- Abrir imagem local ou endereço compatível; obter imagens de publicação por rotas de extração.
- Prévia antes de baixar, sem adicionar à fila/histórico até a ação explícita de download.
- Galeria de arquivos já baixados, incluindo grupos de publicações mistas com imagens.
- Anterior/próxima, contador e setas na janela; deslize no Android, arraste com mouse e setas do teclado no PC.
- Carregamento sob demanda com cache limitado, cancelar, repetir thumbnail com falha e compartilhar link/arquivo conforme a origem.

### Transformação e exportação

- Botão de prévia de imagens condicionado ao tipo/modo elegível; não é um botão universal de prévia de vídeo/áudio.
- Exportar Original, JPG, PNG, WebP ou SVG; dimensões originais, presets e tamanho personalizado.
- Manter proporção, respeitar orientação EXIF, mostrar dimensões/formato original e resultado; prévia antes de exportar.
- SVG gerado de foto incorpora o raster: não vetoriza o conteúdo. Formatos animados/original dependem da operação de transformação.

<details>
<summary>Referências de implementação</summary>

[online_image_preview.py](../Onda/online_image_preview.py), [image_output.py](../Onda/image_output.py), [media_links.py](../Onda/media_links.py), [ImageGalleryPopup.qml](../Onda/qml/ImageGalleryPopup.qml), [ToolView.qml](../Onda/qml/ToolView.qml), [ImagesPage.kt](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt), [OnlineImageGallery.kt](../Android/app/src/main/java/br/com/onda/mobile/OnlineImageGallery.kt), [HistoryImageGallery.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryImageGallery.kt), [GalleryGestures.kt](../Android/app/src/main/java/br/com/onda/mobile/GalleryGestures.kt), [ImageSourcePicker.kt](../Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt).

</details>

---

<a id="sec-12"></a>

## 12. Conversor local

### Entrada e opções de conversão

- Um ou vários arquivos de áudio/vídeo; processamento em lote, progresso, cancelamento e falhas por arquivo.
- Vídeo MP4/MKV/MOV; áudio MP3/M4A/AAC conforme a entrada e seleção.
- Qualidade equilibrada/alta/arquivo menor; resolução original/1080p/720p/480p, bitrate de vídeo automático ou fixo, bitrate de áudio e FPS.
- Manter ou remover áudio do vídeo; exportação da primeira faixa de áudio e vídeo compatíveis, não de todas as faixas/legendas.
- H.264/AAC no caminho de vídeo; preserva proporção e não amplia o vídeo.

### Silêncio, prévia e saída

- Detectar/remover silêncio no início e fim opcionalmente; preserva pausas internas. Arquivo inteiramente silencioso requer desativar recorte para converter.
- Abrir prévia do original, consultar duração/dimensões e salvar cópia convertida sem substituir o original.
- Verificar saída e duração antes de publicação; cópias convertidas registradas no histórico conforme o fluxo.

<details>
<summary>Referências de implementação</summary>

[video_converter.py](../Onda/video_converter.py), [silence.py](../Onda/silence.py), [ToolView.qml](../Onda/qml/ToolView.qml), [VideoConverterPage.kt](../Android/app/src/main/java/br/com/onda/mobile/VideoConverterPage.kt), [mobile_backend.py](../Android/app/src/main/python/mobile_backend.py).

</details>

---

<a id="sec-13"></a>

## 13. Editor de áudio e metadados

### Arquivos, campos e capa

- Abrir arquivo local diretamente ou a partir do histórico; edição individual e em lote.
- Campos de título, artistas, álbum, artista do álbum, gênero, data, faixa/disco e demais campos oferecidos pelo formulário.
- Escolher, recortar/ajustar e desfazer capa; prévia da capa e controles de posição/zoom.
- Aplicar somente campos marcados no lote; dados não selecionados são preservados.

### Letra e normalização

- Importar letra TXT/LRC; gravar tags/letra/capa compatíveis com o contêiner.
- Normalizar volume independentemente de editar tags; ouvir original e normalizado antes de salvar.

### Salvamento e acessibilidade

- Salvar cópia por padrão ou substituir o original explicitamente; substituição possui proteção contra alterações/permissão e arquivo de trabalho/segurança conforme a plataforma.
- MP3, M4A, FLAC, WAV, OGG e OPUS no editor compartilhado. Recodificação em formato com perdas não recupera qualidade.
- Recorte de capa possui alternativas acessíveis a arrastar no Android.

<details>
<summary>Referências de implementação</summary>

[audio_library.py](../Onda/audio_library.py), [batch_metadata.py](../Onda/batch_metadata.py), [cover_crop.py](../Onda/cover_crop.py), [ToolView.qml](../Onda/qml/ToolView.qml), [CoverCropPopup.qml](../Onda/qml/CoverCropPopup.qml), [MetadataPage.kt](../Android/app/src/main/java/br/com/onda/mobile/MetadataPage.kt), [BatchMetadataEditor.kt](../Android/app/src/main/java/br/com/onda/mobile/BatchMetadataEditor.kt), [AdvancedControls.kt](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt), [CoverCropper.kt](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt), [AudioReplacement.kt](../Android/app/src/main/java/br/com/onda/mobile/AudioReplacement.kt).

</details>

---

<a id="sec-14"></a>

## 14. Aparência, idioma e acessibilidade

### Tema e interface

- Tema padrão em instalação limpa: **Preto puro + Verde-Água** nas duas versões; preferências existentes são preservadas.
- Claro, Escuro, Preto puro, Seguir o sistema e Alto contraste; 16 cores de destaque.
- Bordas/separações opcionais no Preto puro; escala de fonte, família e espaçamento.
- PC oferece fontes instaladas; Android usa as famílias/categorias disponíveis na interface nativa.
- Aparência em janela rápida e configurações completas; abas segmentadas, escalas e tamanhos de cards.

### Idioma e configurações

- Português do Brasil, espanhol e inglês; traduções de interface, avisos e erros técnicos reconhecidos.
- PC pede reinício para aplicar mudança de idioma quando necessário; Android aplica imediatamente. Nome do ONDA, títulos e arquivos permanecem originais.
- Pesquisa de configurações com indicação da categoria/aba de origem; não apenas opção isolada.
- Foco visível e teclado no PC; nomes/estados semânticos, TalkBack, ações de mover faixas e alternativas a gestos no Android.

### Acessibilidade e atalhos

- Ícone Android acompanha tema/destaque; atualização do launcher depende do próprio launcher.
- Atalhos PC configuráveis, detecção de conflitos/combinações reservadas e restauração por ação ou total.

<details>
<summary>Referências de implementação</summary>

[appearance.py](../Onda/appearance.py), [interface_fonts.py](../Onda/interface_fonts.py), [interface_spacing.py](../Onda/interface_spacing.py), [i18n.py](../Onda/i18n.py), [error_localization.py](../Onda/error_localization.py), `locales/technical_errors.json`, [shortcut_options.py](../Onda/shortcut_options.py), [SettingsPopup.qml](../Onda/qml/SettingsPopup.qml), [ActionButton.qml](../Onda/qml/ActionButton.qml), [Accessibility.kt](../Android/app/src/main/java/br/com/onda/mobile/Accessibility.kt), [Localization.kt](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt), [TechnicalErrors.kt](../Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt), [LauncherIcons.kt](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt), [AppearanceWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/AppearanceWindow.kt), [SettingsSearch.kt](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt).

</details>

---

<a id="sec-15"></a>

## 15. Configurações, dados e privacidade

### Preferências e persistência

- Categorias atuais incluem Geral, Aparência, Downloads, Imagens, Áudio, Contas, Ferramentas e Desempenho; layout/controles específicos diferem por plataforma.
- Lembrar configurações, restauração seletiva ou total e importação/exportação de preferências compatíveis em JSON.
- Exportação de preferências não transfere contas, tokens, cookies, caminhos, mídia, histórico ou filas.
- Fila/histórico e sessão de reprodução possuem persistência própria; não presumir que desligar Lembrar configurações apaga esses dados.
- PC instalado/portátil usa dados por usuário em `%LOCALAPPDATA%/Onda`, incluindo biblioteca SQLite; o portátil não significa preferências guardadas junto ao executável.

### Armazenamento e credenciais

- Android usa armazenamento privado, MediaStore/pasta escolhida e URIs de documentos conforme a versão do sistema; importação usa permissões concedidas pelo usuário.
- Spotify opcional com OAuth/PKCE e acesso da conta; Client ID/secret opcionais conforme a rota, desconectar/remover credenciais.
- Windows protege credenciais com DPAPI; Android usa cofre protegido pelo sistema. Cookies exigem tratamento de dados de acesso.
- Dados de busca/metadados/mídia são enviados aos provedores consultados; não há serviço próprio de histórico do ONDA.
- Controles de notificação não eliminam confirmações necessárias ou erros.

<details>
<summary>Referências de implementação</summary>

[preferences.py](../Onda/preferences.py), [library.py](../Onda/library.py), [advanced_options.py](../Onda/advanced_options.py), [spotify_account.py](../Onda/spotify_account.py), `credentials.py`, `settings_schema/desktop.json`, [OndaStore.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt), [PlaybackSessions.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt), [DownloadRequests.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt), [Android/app/src/main/python/credentials.py](../Android/app/src/main/python/credentials.py).

</details>

---

<a id="sec-16"></a>

## 16. Preparação, cache e desempenho

### Preparação e carregamento

- Trabalho de rede/extração/conversão fora da thread principal; carregamento incremental de informações e listas.
- Caches de busca, capas, prévias, análise Jukebox e efeitos; cancelamento de solicitações obsoletas.
- Preparação antecipada de próximas faixas e estados de leitura/preparação/pronta/falha; parâmetros definem se um resultado pode ser reaproveitado.

### Cache e uso de recursos

- Limpar cache manualmente, consultar/atualizar tamanho; proteção quando operações estão usando os arquivos.
- Limpeza automática opcional: caches descartáveis antigos após 7 dias e limite suave de 512 MiB, preservando arquivos recentes, parciais interrompidos e áudio de reprodução protegido pelo fluxo.
- No PC, número de threads por conversão, prioridade e reserva mínima de memória livre para aguardar novos trabalhos.
- Ferramentas externas são executadas com limites, cancelamento e logs nos caminhos aplicáveis; não existe promessa de consumo fixo de memória/CPU.
- Situação local das ferramentas com ícones, versões resumidas, disponibilidade, datas legíveis e detalhes técnicos expansíveis. O PC adapta a grade à largura/fonte e o Android usa linhas compactas. A verificação e o resultado da atualização são persistentes.
- Após uma verificação sem ferramentas indisponíveis, Reiniciar ONDA aparece nas duas versões. Troca o processo inteiro, salva o estado antes de sair e bloqueia operações conflitantes. Referências: `Onda/app_restart.py`, `qt_workspace_ui.py`, `RestartActivity.kt`, `OndaViewModel.kt` e `PlaybackSessions.kt`.

<details>
<summary>Referências de implementação</summary>

[cache_cleanup.py](../Onda/cache_cleanup.py), [performance.py](../Onda/performance.py), [parallel_queue.py](../Onda/parallel_queue.py), [qt_workspace_ui.py](../Onda/qt_workspace_ui.py), [qt_jukebox_ui.py](../Onda/qt_jukebox_ui.py), [OndaViewModel.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt), [CacheControls.kt](../Android/app/src/main/java/br/com/onda/mobile/CacheControls.kt), [QueueRunner.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt), [YouTubeWorkload.kt](../Android/app/src/main/java/br/com/onda/mobile/YouTubeWorkload.kt).

</details>

---

<a id="sec-17"></a>

## 17. Integrações específicas e atualização

### Somente PC

- Menus de botão direito/tecla de menu e atalhos de navegação, pesquisa, download, fila, histórico, configurações e ferramentas.
- Miniplayers independentes, volume no aplicativo, integração de mídia do Windows e bandeja.
- Progresso na barra de tarefas, comportamento ao fechar e ação opcional de desligar ao concluir a fila.
- Abrir arquivos/pastas com o sistema; arraste de arquivos/links nos destinos compatíveis.
- FFmpeg preparado no primeiro uso, com progresso e verificação de hash; caminho manual, verificar/preparar/atualizar ferramentas.
- Consulta de nova versão estável com notas/tamanho e abertura do download oficial. Não instala silenciosamente.
- Instalador/desinstalador próprios, três idiomas, instalação por usuário, atalho e escolha de pasta.
- Desinstalação oferece apagar dados e remover ferramentas separadamente, ambas desativadas por padrão; não apaga downloads por padrão.

### Somente Android

- APK ARM64 para aparelhos e x86_64 para emuladores; serviços de downloads e reprodução em segundo plano com notificações e controle de mídia.
- Somente Wi-Fi, política ao perder conexão, intents de compartilhamento/abertura e seletores nativos de documentos.
- Barra compacta e player expandido, gestos de touch e controle de volume pelo sistema.
- Ferramentas Python/FFmpeg/FFprobe/QuickJS incluídas no APK; atualização das ferramentas e autoverificação no app.
- Atualização interna: escolher APK da arquitetura, baixar com progresso em segundo plano, cancelar/descartar, conferir assinatura e pedir instalação ao Android.
- Permissão para instalar pelo ONDA, confirmação de instalação e manutenção dos dados; restrições de bateria e notificações continuam pertencendo ao Android.

**Comum:** consulta às releases oficiais, comparação de versão, filtragem de rascunhos/pré-releases para instalações estáveis; notas e tamanho quando disponíveis.

<details>
<summary>Referências de implementação</summary>

[windows_shell.py](../Onda/windows_shell.py), [windows_media.py](../Onda/windows_media.py), [windows_drop.py](../Onda/windows_drop.py), [ffmpeg_runtime.py](../Onda/ffmpeg_runtime.py), [advanced_options.py](../Onda/advanced_options.py), [qt_desktop_ui.py](../Onda/qt_desktop_ui.py), [InAppUpdate.kt](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt), [DownloadService.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt), [EffectsPlaybackService.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt), [JukeboxService.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt), `AndroidManifest.xml`, `empacotamento/`.

</details>

---

<a id="sec-18"></a>

## 18. Site

- Site estático em `docs/onda-site/`, com navegação por início, downloads, recursos, guia, novidades, sobre e privacidade.
- Português, espanhol e inglês; tema claro/escuro e persistência local das escolhas.
- Capturas de PC/Android, galeria ampliável, texto alternativo, foco restaurado ao fechar e suporte à preferência por movimento reduzido.
- Downloads separados: instalador Windows, portátil Windows, APK ARM64 e APK x86_64 para emulador.
- Consulta da última release pública estável na API GitHub, seleção de assets e tratamento de indisponibilidade/fallback conforme o script.
- Links para documentação, histórico de versões, contribuição, licença e privacidade.
- O site apresenta/distribui o aplicativo; não executa os downloads/conversões de mídia do aplicativo no navegador.

<details>
<summary>Referências de implementação</summary>

[docs/onda-site/index.html](../docs/onda-site/index.html), [docs/onda-site/app.js](../docs/onda-site/app.js), [docs/onda-site/style.css](../docs/onda-site/style.css), [docs/onda-site/README.md](../docs/onda-site/README.md).

</details>

---

<a id="sec-19"></a>

## 19. Testes, construção e distribuição

- Testes Python unitários/integração e Qt, testes JVM e instrumentados Android; cenários de diagnóstico separados.
- `ONDA_UI_TESTS`/ambientes isolados permitem validar sem usar dados cotidianos; não é uma função de produção.
- Windows: launcher/runtime portátil, instalador e desinstalador, autoverificações e geração de metadados de versão.
- Android: Gradle, variantes de arquitetura, backend Python, ferramentas nativas, assinatura de produção e verificações de alinhamento/arquitetura.
- Preparação de release com binários, fontes próprias e de terceiros, proveniência, manifestos, hashes, notas e validação.
- Rascunho no GitHub é diferente de release publicada; app/site consultam a versão pública compatível.
- `Testes/` contém ambiente local ignorado pelo Git, não documentação canônica nem requisito para usuários finais.

<details>
<summary>Referências de implementação</summary>

[empacotamento/prepare_release.py](../empacotamento/prepare_release.py), `Android/build/`, [Android/app/build.gradle.kts](../Android/app/build.gradle.kts), `Android/nativebuild/`, `Android/native-provenance/`, `.github/`, `diagnosticos/`, [docs/VALIDACAO-RELEASE-1.2.3.md](../docs/VALIDACAO-RELEASE-1.2.3.md), [PUBLICAR_RELEASE.md](../PUBLICAR_RELEASE.md).

</details>

---

<a id="sec-20"></a>

## 20. Limitações e pontos que exigem conferência futura

1. **Disponibilidade externa:** links, login, região/IP e mudanças das plataformas podem impedir downloads. A revisão de código não substitui testar um link real.
2. **Qualidade original:** transcodificar para FLAC não recupera áudio perdido; fonte equivalente pode representar outra edição se a correspondência não for conferida.
3. **Letras/capas/datas:** dependem dos dados locais e dos provedores; ter implementação automática não garante resultado para toda música.
4. **Retomada:** depende de servidor, URLs e validadores; pode reiniciar com segurança em vez de continuar bytes antigos.
5. **Sessão:** restaura referências locais, não recupera arquivo que foi apagado ou permissão revogada.
6. **Agendamento/segundo plano:** limitado por estado do PC e políticas do Android; não é execução exata garantida.
7. **Guias revisados em 27/10/2026:** recursos avançados, configurações, Jukebox, navegação e manuais PC/Android foram atualizados para a 1.2.3. Relatórios de paridade/testes continuam históricos. `settings_schema/layout.json` e o índice de busca Android ainda contêm referências legadas; esta revisão documental não altera contratos ou código da aplicação.
8. **Defaults legados:** chaves como duração antiga de efeitos/continuidade podem permanecer em arquivos de defaults sem controle visível atual. O apêndice de configurações diferencia schema, índice e exibição; não tratar cada chave como adição ativa.
9. **Qt e Tk:** ambos os conjuntos de arquivos existem. Funções presentes somente no Tk não comprovam paridade no Qt; o índice técnico preserva os dois para investigação.
10. **Paridade:** biblioteca de coleções salvas, Wi-Fi, player expandido Android, miniplayer Windows e projeção de Links PC têm diferenças intencionais. Recursos comuns também podem ter limites distintos.

---

<a id="sec-21"></a>

## 21. Como manter este documento

Atualização de implementação posterior à base Git: [ferramentas, estados e preparação por faixa](CLAREZA-DE-ESTADOS.md). O índice técnico foi atualizado para incluir os novos módulos: `collection_coverage.py`, `tool_status.py`, `workflow_status.py`, `ToolStatusControls.kt` e `WorkflowStatus.kt`.

- Ao alterar recurso, atualizar sua seção, plataforma, limitações e referências; marcar remoções explicitamente.
- Antes de sugerir melhoria, procurar o termo e sinônimos aqui, conferir os módulos citados e distinguir implementação ausente de bug em implementação existente.
- Usar código/interface atuais como evidência principal; changelogs e relatos são contexto histórico.
- Atualizar versão/data/commit da base após uma nova revisão; os números de linha do índice técnico são desta fotografia e mudam com o código.
- Não inserir senhas, tokens, cookies, dados de usuário ou chaves de assinatura no inventário.
- Abaixo, “funções” no sentido técnico são símbolos de código. As seções anteriores descrevem as funcionalidades de produto; os dois índices se complementam.

<!-- INVENTARIO_TECNICO:INICIO -->

---

<a id="sec-22"></a>

## 22. Catálogo de configurações do código atual

Extraído dos contratos de interface. As opções abaixo não contêm preferências pessoais. Valores dinâmicos (por exemplo, fontes instaladas) são resumidos. O índice de busca Android inclui títulos e textos de ajuda; sua presença isolada não comprova um controle visível.

### 22.1 PC: campos publicados pelo schema Qt

<details>
<summary><strong>Geral</strong> — 7 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Lembrar configurações | `remember_settings` | bool | Ativado |
| Ativar notificações | `notifications_enabled` | bool | Ativado |
| Idioma | `language` | Português (Brasil), Español, English | pt-BR |
| Ao fechar o ONDA | `close_behavior` | Encerrar, Minimizar para a bandeja | Encerrar |
| Reconhecer links copiados automaticamente | `clipboard_links` | bool | Ativado |
| Duração dos avisos | `notice_duration` | Fechar manualmente, Após 3 segundos, Após 5 segundos, Após 10 segundos, Após 15 segundos, Após 30 segundos, Após 60 segundos | Após 3 segundos |
| Animar avisos | `notice_animation` | bool | Ativado |

</details>

<details>
<summary><strong>Aparência</strong> — 17 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Modo de aparência | `theme_mode` | Seguir o sistema, Escuro, Preto puro, Claro, Alto contraste | Preto puro |
| Cor de destaque | `theme_accent` | Verde-Água, Azul, Roxo, Rosa, Laranja, Vermelho, Verde, Verde-limão, Amarelo, Dourado, Ciano, Turquesa, Índigo, Lilás, Coral, Cinza | Verde-Água |
| Mostrar bordas e separações no Preto puro | `pure_black_separators` | bool | Desativado |
| Alterar tamanho da fonte | `interface_font_size` | 85%, 100%, 115%, 130% | 100% |
| Fonte da interface | `interface_font` | Categorias tipográficas e fontes disponíveis no Windows | Padrão do sistema |
| Espaçamento da interface | `interface_spacing` | Compacto, Padrão, Confortável | Padrão |
| Simplificar controles de download | `simple_download_ui` | bool | Desativado |
| Mostrar ações antes das listas | `queue_actions_at_top` | bool | Ativado |
| Mostrar itens na fila | `queue_view` | Compacto, Completa | Compacto |
| Tamanho dos cards da pesquisa | `catalog_card_size` | Pequeno, Médio, Grande | Grande |
| Tamanho dos cards de álbuns e playlists | `playlist_card_size` | Pequeno, Médio, Grande | Grande |
| Tamanho dos cards da fila | `queue_card_size` | Pequeno, Médio, Grande | Grande |
| Mostrar músicas no histórico | `history_view` | Compacto, Completa | Compacto |
| Tamanho dos cards do histórico | `history_card_size` | Pequeno, Médio, Grande | Grande |
| Ordem das abas de reprodução | `playback_tab_order` | Efeitos primeiro, Jukebox infinito primeiro | Efeitos primeiro |
| Animações da interface | `qt_animations` | bool | Ativado |
| Minimizar ONDA ao abrir o miniplayer | `minimize_on_miniplayer` | bool | Ativado |

</details>

<details>
<summary><strong>Downloads</strong> — 30 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Pasta de destino | `folder` | text | Vazio/local |
| Formato | `mode` | Vídeo · melhor qualidade (MKV), Vídeo · MP4, Áudio · original, sem recodificar, Áudio · MP3, Áudio · M4A (AAC), Áudio · FLAC, Fotos · todas do carrossel, Publicação · fotos e vídeos originais | Vídeo · melhor qualidade (MKV) |
| Resolução máxima | `height` | Melhor disponível, 2160p / 4K, 1440p, 1080p, 720p, 480p | 1080p |
| FPS máximo | `fps` | Original, 24 fps, 30 fps, 60 fps, 120 fps | Original |
| Downloads simultâneos | `concurrent_downloads` | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 | 1 |
| Escolher automaticamente os metadados mais semelhantes | `auto_metadata` | bool | Desativado |
| Escolher automaticamente a versão mais semelhante no YouTube | `auto_match` | bool | Desativado |
| Revisar metadados antes de baixar | `review_metadata` | bool | Desativado |
| Organizar músicas em | `organization` | Catálogo, Pasta de destino, Artista, Artista / Álbum, Álbum, Artista / Ano - Álbum, Gênero / Artista / Álbum, Formato / Artista / Álbum | Catálogo |
| Nome dos arquivos | `filename_template` | Original, Artista - Música, Faixa - Música, Faixa - Artista - Música, Disco-Faixa - Música | Original |
| Quando o arquivo já existir | `duplicates` | Perguntar, Manter ambos, Substituir, Ignorar | Perguntar |
| Baixar mídias sociais automaticamente na maior qualidade | `social_best_quality` | bool | Ativado |
| Selecionar todas as mídias ao abrir a publicação | `auto_select_media` | bool | Ativado |
| Baixar playlist de vídeo | `playlist` | bool | Desativado |
| Máximo de itens por playlist | `playlist_limit` | text | 1000 |
| Detectar duplicatas na fila e no histórico | `detect_duplicates` | bool | Ativado |
| Retomar arquivos interrompidos quando possível | `resume_downloads` | bool | Ativado |
| Retomar fila ao abrir o ONDA | `resume_queue` | bool | Desativado |
| Normalizar volume dos próximos downloads | `normalize_volume` | bool | Desativado |
| Ação ao terminar a fila | `finish_action` | Nenhuma, Som, Notificação, Som e notificação, Desligar PC | Notificação |
| Mostrar progresso na barra de tarefas | `taskbar_progress` | bool | Ativado |
| Agendar downloads | `schedule_enabled` | bool | Desativado |
| Começar · HH:MM | `schedule_start` | text | 22:00 |
| Parar · HH:MM | `schedule_stop` | text | 07:00 |
| Qualidade MP3 | `mp3_quality` | 320 kbps, 256 kbps, 192 kbps, 128 kbps, 96 kbps | 320 kbps |
| Qualidade M4A | `m4a_quality` | 256 kbps, 192 kbps, 128 kbps, 96 kbps | 256 kbps |
| Plataforma de pesquisa | `catalog_provider` | Deezer, Apple / iTunes, Spotify, Todos | Deezer |
| Formato de álbuns e playlists | `playlist_mode` | Áudio · MP3 (320 kbps), Áudio · M4A (AAC), Áudio · FLAC, Áudio · original, sem recodificar | Áudio · MP3 (320 kbps) |
| Qualidade MP3 de playlists | `playlist_mp3_quality` | 320 kbps, 256 kbps, 192 kbps, 128 kbps, 96 kbps | 320 kbps |
| Qualidade M4A de playlists | `playlist_m4a_quality` | 256 kbps, 192 kbps, 128 kbps, 96 kbps | 256 kbps |

</details>

<details>
<summary><strong>Imagens</strong> — 5 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Formato | `image_format` | Original, JPG, PNG, WebP, SVG | Original |
| Tamanho máximo | `image_size` | Original, Até 1920 × 1080, Até 1280 × 720, Até 1080 × 1080, Personalizado | Original |
| Largura | `image_width` | text | 1920 |
| Altura | `image_height` | text | 1080 |
| Manter proporção (sem ampliar ou distorcer) | `image_keep_ratio` | bool | Ativado |

</details>

<details>
<summary><strong>Áudio</strong> — 4 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Mostrar letra sincronizada (LRC) | `synced_lyrics` | bool | Desativado |
| Duração da transição entre músicas (segundos) | `jukebox_transition_seconds` | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | 2 |
| Músicas nas pesquisas | `search_preview_duration` | 10 segundos, 15 segundos, 25 segundos, 30 segundos, 45 segundos, 60 segundos, 90 segundos, 120 segundos, 180 segundos | 30 segundos |
| Animação da letra | `lyrics_animation` | Desativada, Suave, Deslizar, Zoom | Suave |

</details>

<details>
<summary><strong>Contas</strong> — 2 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Client ID | `spotify_client_id` | text | Vazio/local |
| Client Secret · opcional | `spotify_client_secret` | text | Vazio/local |

</details>

<details>
<summary><strong>Ferramentas</strong> — 2 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Verificar atualizações do ONDA ao abrir | `check_updates` | bool | Ativado |
| Pasta do FFmpeg · opcional quando já configurado | `ffmpeg` | text | Vazio/local |

</details>

<details>
<summary><strong>Desempenho</strong> — 4 opções</summary>

| Opção | Chave | Tipo / valores | Padrão |
| --- | --- | --- | --- |
| Threads por conversão | `conversion_threads` | Automático, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 | Automático |
| Aguardar quando a RAM livre ficar abaixo de | `memory_reserve` | Desativado, 512 MB, 1 GB, 2 GB, 4 GB | Desativado |
| Prioridade das tarefas | `worker_priority` | Normal, Baixa, Acima do normal | Normal |
| Limpar temporários automaticamente | `automatic_cache_cleanup` | bool | Ativado |

</details>

Ações adicionais ficam nos componentes de configurações: restaurar/exportar/importar, ordem/visibilidade de abas, Spotify/cookies, cache e ferramentas. Consultar `SettingsPopup.qml`; este schema não enumera sozinho todos os botões.

### 22.2 Android: entradas do índice de configurações

<details>
<summary>Geral — 13 entradas</summary>

- Preferências
- Idioma
- Lembrar configurações
- Ative para recuperar suas opções ao abrir o aplicativo novamente.
- Animar avisos
- Duração dos avisos
- Restaurar configurações
- Restaurar TODAS as configurações ao padrão
- Escolher quais configurações restaurar…
- Exportar configurações…
- Importar configurações…
- A transferência não inclui contas, cookies nem caminhos de pastas.
- Reconhecer links copiados automaticamente

</details>

<details>
<summary>Aparência — 15 entradas</summary>

- Tema e cores
- Modo de aparência
- Mostrar bordas e separações no Preto puro
- Cor de destaque
- Espaçamento da interface
- Alterar tamanho da fonte
- Fonte da interface
- A fonte muda na hora. Ative Lembrar configurações para manter sua escolha ao reabrir.
- Tamanho dos cards da fila
- Mostrar músicas no histórico
- Tamanho dos cards do histórico
- Ordem das abas
- Restaurar ordem das abas
- Mostrar ou ocultar abas
- Simplificar controles de download

</details>

<details>
<summary>Downloads — 31 entradas</summary>

- Downloads e arquivos
- As opções são aplicadas aos próximos links adicionados.
- Pasta de destino
- Usar pasta padrão
- Quando o arquivo já existir
- Baixar playlist de vídeo
- Máximo de itens por playlist
- Escolher automaticamente os metadados mais semelhantes
- Escolher automaticamente a versão mais semelhante no YouTube
- Revisar metadados antes de baixar
- Fila e agendamento
- Downloads simultâneos
- No Android, escolha de 1 a 4 downloads simultâneos.
- Detectar duplicatas na fila e no histórico
- Retomar arquivos interrompidos quando possível
- Retomar fila ao abrir o ONDA
- Normalizar volume dos próximos downloads
- Agendar downloads
- Começar · HH:MM
- Parar · HH:MM
- Informe horários diferentes no formato HH:MM.
- Organizar músicas em
- Nome dos arquivos
- Prévia de organização
- As pastas de playlists são preservadas. Números de faixa ausentes são omitidos.
- Formato
- Qualidade de áudio
- Resolução máxima
- FPS máximo
- Baixar mídias sociais automaticamente na maior qualidade
- Selecionar todas as mídias ao abrir a publicação

</details>

<details>
<summary>Áudio — 7 entradas</summary>

- Reprodução e prévias
- Duração das prévias
- Vale para a próxima prévia. Nas pesquisas, o catálogo pode fornecer um trecho menor.
- Continuar prévia dos efeitos em outras abas
- Músicas nas pesquisas
- Slowed / Sped Up e Reverb
- Continuar Jukebox em outras abas e em segundo plano

</details>

<details>
<summary>Contas — 11 entradas</summary>

- Contas e acesso
- Spotify · opcional
- Client ID
- Client Secret · opcional
- Abrir Spotify Developers
- Importar cookies do YouTube
- Importar cookies.txt
- Remover cookies
- Remover sessão do YouTube
- Conectar
- Desconectar

</details>

<details>
<summary>Ferramentas — 15 entradas</summary>

- Ferramentas e atualizações
- Atualizar ferramentas
- Verificar ferramentas
- Verificar atualizações do ONDA ao abrir
- Verificar atualização do ONDA
- Baixando atualização do ONDA
- Cancelar download da atualização
- Instalar atualização
- Descartar atualização baixada
- Não foi possível baixar a atualização. Tente novamente.
- Baixar nova versão
- Cache
- Limpar cache
- Atualizar tamanho
- Aguarde as operações em andamento antes de limpar o cache.

</details>

<details>
<summary>Imagens — 6 entradas</summary>

- Formato
- Tamanho máximo
- Largura × altura (px)
- Largura
- Altura
- Manter proporção (sem ampliar ou distorcer)

</details>

Conferir exibição/condições em `SettingsWindow.kt`, `AdvancedControls.kt`, `CacheControls.kt` e `DailyUse.kt`. Diferenças relevantes: Wi-Fi/notificações/URIs no Android; bandeja, FFmpeg manual e recursos de processo no PC.

---

<a id="sec-23"></a>

## 23. Índice técnico de módulos, classes e funções

Atualizado a partir dos fontes locais em 27/10/2026. Python usa AST; Kotlin e QML usam declarações nomeadas por leitura lexical. Funções importadas, lambdas e métodos gerados não são enumerados. Os links de linha correspondem a esta revisão.

### 23.1 Python compartilhado e PC (inclui implementação Tk conservada)

<details>
<summary><code>advanced_options.py</code> — 7 declarações</summary>

[Onda/advanced_options.py](../Onda/advanced_options.py)

Descrição do módulo no fonte: Portable non-secret preferences, schedule windows and release discovery.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `valid_time` | [13](../Onda/advanced_options.py#L13) | função/método |
| `schedule_allowed` | [15](../Onda/advanced_options.py#L15) | função/método |
| `clean_advanced` | [22](../Onda/advanced_options.py#L22) | função/método |
| `export_settings` | [35](../Onda/advanced_options.py#L35) | função/método |
| `import_settings` | [46](../Onda/advanced_options.py#L46) | função/método |
| `version_key` | [85](../Onda/advanced_options.py#L85) | função/método |
| `release_update` | [90](../Onda/advanced_options.py#L90) | função/método |

</details>

<details>
<summary><code>advanced_ui.py</code> — 24 declarações</summary>

[Onda/advanced_ui.py](../Onda/advanced_ui.py)

Descrição do módulo no fonte: Desktop controls for queue policy, schedules and local library tools.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `move_queue` | [11](../Onda/advanced_ui.py#L11) | função/método |
| `concurrency_controls` | [22](../Onda/advanced_ui.py#L22) | função/método |
| `download_policy_controls` | [28](../Onda/advanced_ui.py#L28) | função/método |
| `preference_transfer_controls` | [41](../Onda/advanced_ui.py#L41) | função/método |
| `app_update_controls` | [47](../Onda/advanced_ui.py#L47) | função/método |
| `transfer` | [54](../Onda/advanced_ui.py#L54) | função/método |
| `check_update` | [73](../Onda/advanced_ui.py#L73) | função/método |
| `check_update.worker` | [75](../Onda/advanced_ui.py#L75) | função/método |
| `tick` | [82](../Onda/advanced_ui.py#L82) | função/método |
| `AudioEditor` | [94](../Onda/advanced_ui.py#L94) | classe |
| `AudioEditor.__init__` | [95](../Onda/advanced_ui.py#L95) | função/método |
| `AudioEditor.save_mode` | [142](../Onda/advanced_ui.py#L142) | função/método |
| `AudioEditor.toggle` | [145](../Onda/advanced_ui.py#L145) | função/método |
| `AudioEditor.show_cover` | [147](../Onda/advanced_ui.py#L147) | função/método |
| `AudioEditor.undo_cover` | [155](../Onda/advanced_ui.py#L155) | função/método |
| `AudioEditor.pick_cover` | [159](../Onda/advanced_ui.py#L159) | função/método |
| `AudioEditor.adjust_cover` | [174](../Onda/advanced_ui.py#L174) | função/método |
| `AudioEditor.adjust_cover.accepted` | [180](../Onda/advanced_ui.py#L180) | função/método |
| `AudioEditor.pick_lyrics` | [187](../Onda/advanced_ui.py#L187) | função/método |
| `AudioEditor.run` | [190](../Onda/advanced_ui.py#L190) | função/método |
| `AudioEditor.run.worker` | [196](../Onda/advanced_ui.py#L196) | função/método |
| `AudioEditor.poll` | [203](../Onda/advanced_ui.py#L203) | função/método |
| `AudioEditor.stop_preview` | [221](../Onda/advanced_ui.py#L221) | função/método |
| `AudioEditor.shutdown` | [223](../Onda/advanced_ui.py#L223) | função/método |

</details>

<details>
<summary><code>album_import.py</code> — 3 declarações</summary>

[Onda/album_import.py](../Onda/album_import.py)

Descrição do módulo no fonte: Album track enumeration; all audio uses the existing YouTube workflow.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `finish` | [8](../Onda/album_import.py#L8) | função/método |
| `spotify_public_album` | [21](../Onda/album_import.py#L21) | função/método |
| `load_album` | [48](../Onda/album_import.py#L48) | função/método |

</details>

<details>
<summary><code>app.py</code> — 57 declarações</summary>

[Onda/app.py](../Onda/app.py)

Descrição do módulo no fonte: Onda — desktop media downloader. Run with Python 3.10+.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `readable_bytes` | [27](../Onda/app.py#L27) | função/método |
| `App` | [39](../Onda/app.py#L39) | classe |
| `App.__init__` | [40](../Onda/app.py#L40) | função/método |
| `App._first_map` | [219](../Onda/app.py#L219) | função/método |
| `App.show_first_run` | [224](../Onda/app.py#L224) | função/método |
| `App.language_changed` | [235](../Onda/app.py#L235) | função/método |
| `App.refresh_restart_button` | [246](../Onda/app.py#L246) | função/método |
| `App.restart_app` | [251](../Onda/app.py#L251) | função/método |
| `App.mode_changed` | [259](../Onda/app.py#L259) | função/método |
| `App.downloads_limit_changed` | [262](../Onda/app.py#L262) | função/método |
| `App.refresh_parallel_queue` | [268](../Onda/app.py#L268) | função/método |
| `App.schedule_preferences` | [272](../Onda/app.py#L272) | função/método |
| `App.persist_preferences` | [277](../Onda/app.py#L277) | função/método |
| `App.toggle_remember_settings` | [294](../Onda/app.py#L294) | função/método |
| `App.choose_folder` | [308](../Onda/app.py#L308) | função/método |
| `App.choose_ffmpeg` | [313](../Onda/app.py#L313) | função/método |
| `App.prepare_ffmpeg` | [318](../Onda/app.py#L318) | função/método |
| `App.download_cookies` | [325](../Onda/app.py#L325) | função/método |
| `App.choose_social_cookies` | [329](../Onda/app.py#L329) | função/método |
| `App.add` | [334](../Onda/app.py#L334) | função/método |
| `App.show_shortcuts` | [448](../Onda/app.py#L448) | função/método |
| `App.show_queue` | [451](../Onda/app.py#L451) | função/método |
| `App.download_clipboard_link` | [454](../Onda/app.py#L454) | função/método |
| `App.download_now` | [463](../Onda/app.py#L463) | função/método |
| `App.queue_catalog` | [478](../Onda/app.py#L478) | função/método |
| `App.open_metadata` | [502](../Onda/app.py#L502) | função/método |
| `App.save_spotify_credentials` | [510](../Onda/app.py#L510) | função/método |
| `App.spotify_credentials_edited` | [520](../Onda/app.py#L520) | função/método |
| `App.forget_spotify_credentials` | [527](../Onda/app.py#L527) | função/método |
| `App.set_state` | [538](../Onda/app.py#L538) | função/método |
| `App.start` | [549](../Onda/app.py#L549) | função/método |
| `App.next_job` | [572](../Onda/app.py#L572) | função/método |
| `App.supervise` | [609](../Onda/app.py#L609) | função/método |
| `App.set_progress` | [662](../Onda/app.py#L662) | função/método |
| `App.poll_events` | [673](../Onda/app.py#L673) | função/método |
| `App.write_log` | [845](../Onda/app.py#L845) | função/método |
| `App.cancel` | [855](../Onda/app.py#L855) | função/método |
| `App.cancel.stop` | [863](../Onda/app.py#L863) | função/método |
| `App.dismiss_version_picker` | [869](../Onda/app.py#L869) | função/método |
| `App.send_version` | [876](../Onda/app.py#L876) | função/método |
| `App.send_reply` | [879](../Onda/app.py#L879) | função/método |
| `App.show_failures` | [901](../Onda/app.py#L901) | função/método |
| `App.retry` | [905](../Onda/app.py#L905) | função/método |
| `App.select_all_items` | [910](../Onda/app.py#L910) | função/método |
| `App.clear_queue` | [924](../Onda/app.py#L924) | função/método |
| `App.remove` | [939](../Onda/app.py#L939) | função/método |
| `App.open_folder` | [966](../Onda/app.py#L966) | função/método |
| `App.help` | [979](../Onda/app.py#L979) | função/método |
| `App.open_readme` | [1010](../Onda/app.py#L1010) | função/método |
| `App.destroy` | [1016](../Onda/app.py#L1016) | função/método |
| `App.close` | [1045](../Onda/app.py#L1045) | função/método |
| `App.persist_queue` | [1072](../Onda/app.py#L1072) | função/método |
| `App.restore_queue` | [1089](../Onda/app.py#L1089) | função/método |
| `App.record_history` | [1098](../Onda/app.py#L1098) | função/método |
| `App.tab_changed` | [1105](../Onda/app.py#L1105) | função/método |
| `App.update_downloader` | [1120](../Onda/app.py#L1120) | função/método |
| `App.update_downloader.worker` | [1131](../Onda/app.py#L1131) | função/método |

</details>

<details>
<summary><code>app_version.py</code> — 0 declarações</summary>

[Onda/app_version.py](../Onda/app_version.py)

Descrição do módulo no fonte: Canonical Windows application version; packaging metadata is generated from here.

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>appearance.py</code> — 15 declarações</summary>

[Onda/appearance.py](../Onda/appearance.py)

Descrição do módulo no fonte: Live light/dark palettes, accents and Windows app-theme following.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `system_mode` | [29](../Onda/appearance.py#L29) | função/método |
| `blend` | [41](../Onda/appearance.py#L41) | função/método |
| `palette` | [46](../Onda/appearance.py#L46) | função/método |
| `ThemeManager` | [82](../Onda/appearance.py#L82) | classe |
| `ThemeManager.__init__` | [83](../Onda/appearance.py#L83) | função/método |
| `ThemeManager.changed` | [97](../Onda/appearance.py#L97) | função/método |
| `ThemeManager.apply` | [100](../Onda/appearance.py#L100) | função/método |
| `ThemeManager.check_system` | [116](../Onda/appearance.py#L116) | função/método |
| `ThemeManager.mapped` | [124](../Onda/appearance.py#L124) | função/método |
| `ThemeManager.walk` | [133](../Onda/appearance.py#L133) | função/método |
| `ThemeManager.widget` | [138](../Onda/appearance.py#L138) | função/método |
| `ThemeManager.apply_widget_font` | [196](../Onda/appearance.py#L196) | função/método |
| `ThemeManager.apply_canvas_font` | [207](../Onda/appearance.py#L207) | função/método |
| `ThemeManager.titlebar` | [218](../Onda/appearance.py#L218) | função/método |
| `ThemeManager.shutdown` | [239](../Onda/appearance.py#L239) | função/método |

</details>

<details>
<summary><code>artist_alias_lookup.py</code> — 17 declarações</summary>

[Onda/artist_alias_lookup.py](../Onda/artist_alias_lookup.py)

Descrição do módulo no fonte: Bounded MusicBrainz aliases, verified against a recording and cached locally.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LookupUnavailable` | [17](../Onda/artist_alias_lookup.py#L17) | classe |
| `cache_path` | [19](../Onda/artist_alias_lookup.py#L19) | função/método |
| `context_key` | [24](../Onda/artist_alias_lookup.py#L24) | função/método |
| `spotify_artist_key` | [28](../Onda/artist_alias_lookup.py#L28) | função/método |
| `valid_groups` | [32](../Onda/artist_alias_lookup.py#L32) | função/método |
| `AliasCache` | [42](../Onda/artist_alias_lookup.py#L42) | classe |
| `AliasCache.__init__` | [43](../Onda/artist_alias_lookup.py#L43) | função/método |
| `AliasCache.connect` | [49](../Onda/artist_alias_lookup.py#L49) | função/método |
| `AliasCache.read` | [54](../Onda/artist_alias_lookup.py#L54) | função/método |
| `AliasCache.write` | [59](../Onda/artist_alias_lookup.py#L59) | função/método |
| `AliasCache.request_slot` | [64](../Onda/artist_alias_lookup.py#L64) | função/método |
| `AliasCache.cool_down` | [72](../Onda/artist_alias_lookup.py#L72) | função/método |
| `get_json` | [76](../Onda/artist_alias_lookup.py#L76) | função/método |
| `quoted` | [94](../Onda/artist_alias_lookup.py#L94) | função/método |
| `compatible_recording` | [97](../Onda/artist_alias_lookup.py#L97) | função/método |
| `discover_aliases` | [109](../Onda/artist_alias_lookup.py#L109) | função/método |
| `discover_aliases.primary_id` | [155](../Onda/artist_alias_lookup.py#L155) | função/método |

</details>

<details>
<summary><code>artist_aliases.py</code> — 3 declarações</summary>

[Onda/artist_aliases.py](../Onda/artist_aliases.py)

Descrição do módulo no fonte: Reviewed artist names with primary-source provenance; no surname guessing.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `artist_names` | [8](../Onda/artist_aliases.py#L8) | função/método |
| `artist_overlap` | [24](../Onda/artist_aliases.py#L24) | função/método |
| `alias_evidence` | [27](../Onda/artist_aliases.py#L27) | função/método |

</details>

<details>
<summary><code>audio_editor_ui.py</code> — 8 declarações</summary>

[Onda/audio_editor_ui.py](../Onda/audio_editor_ui.py)

Descrição do módulo no fonte: Inline local audio editor, shared by the tab and history.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MetadataPane` | [5](../Onda/audio_editor_ui.py#L5) | classe |
| `MetadataPane.__init__` | [6](../Onda/audio_editor_ui.py#L6) | função/método |
| `MetadataPane.open_batch` | [16](../Onda/audio_editor_ui.py#L16) | função/método |
| `MetadataPane.busy` | [23](../Onda/audio_editor_ui.py#L23) | função/método |
| `MetadataPane.choose` | [24](../Onda/audio_editor_ui.py#L24) | função/método |
| `MetadataPane.open_file` | [31](../Onda/audio_editor_ui.py#L31) | função/método |
| `MetadataPane.stop_preview` | [43](../Onda/audio_editor_ui.py#L43) | função/método |
| `MetadataPane.shutdown` | [45](../Onda/audio_editor_ui.py#L45) | função/método |

</details>

<details>
<summary><code>audio_library.py</code> — 6 declarações</summary>

[Onda/audio_library.py](../Onda/audio_library.py)

Descrição do módulo no fonte: Local audio editing and measured two-pass loudness normalization.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `read_audio` | [13](../Onda/audio_library.py#L13) | função/método |
| `cover_preview` | [30](../Onda/audio_library.py#L30) | função/método |
| `lyrics_text` | [59](../Onda/audio_library.py#L59) | função/método |
| `write_audio` | [68](../Onda/audio_library.py#L68) | função/método |
| `normalize_audio` | [115](../Onda/audio_library.py#L115) | função/método |
| `edit_copy` | [164](../Onda/audio_library.py#L164) | função/método |

</details>

<details>
<summary><code>audio_quality.py</code> — 3 declarações</summary>

[Onda/audio_quality.py](../Onda/audio_quality.py)

Descrição do módulo no fonte: Encode audio at the requested bitrate, even when source and target codecs match.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `AudioQualityPP` | [8](../Onda/audio_quality.py#L8) | classe |
| `AudioQualityPP.__init__` | [9](../Onda/audio_quality.py#L9) | função/método |
| `AudioQualityPP.run` | [14](../Onda/audio_quality.py#L14) | função/método |

</details>

<details>
<summary><code>audio_tools.py</code> — 14 declarações</summary>

[Onda/audio_tools.py](../Onda/audio_tools.py)

Descrição do módulo no fonte: Shared playback and deterministic independent slow/reverb filters.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `executable` | [13](../Onda/audio_tools.py#L13) | função/método |
| `process_options` | [21](../Onda/audio_tools.py#L21) | função/método |
| `effects_filter` | [25](../Onda/audio_tools.py#L25) | função/método |
| `effect_name` | [55](../Onda/audio_tools.py#L55) | função/método |
| `source_position` | [61](../Onda/audio_tools.py#L61) | função/método |
| `PreviewPlayer` | [69](../Onda/audio_tools.py#L69) | classe |
| `PreviewPlayer.__init__` | [71](../Onda/audio_tools.py#L71) | função/método |
| `PreviewPlayer.position_snapshot` | [80](../Onda/audio_tools.py#L80) | função/método |
| `PreviewPlayer.stop` | [84](../Onda/audio_tools.py#L84) | função/método |
| `PreviewPlayer.stop.reap` | [90](../Onda/audio_tools.py#L90) | função/método |
| `PreviewPlayer.play` | [100](../Onda/audio_tools.py#L100) | função/método |
| `PreviewPlayer.play.worker` | [109](../Onda/audio_tools.py#L109) | função/método |
| `PreviewPlayer.messages` | [171](../Onda/audio_tools.py#L171) | função/método |
| `PreviewPlayer.close` | [182](../Onda/audio_tools.py#L182) | função/método |

</details>

<details>
<summary><code>batch_metadata.py</code> — 1 declarações</summary>

[Onda/batch_metadata.py](../Onda/batch_metadata.py)

Descrição do módulo no fonte: Apply only explicitly selected metadata fields, using atomic per-file saves.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `edit_batch` | [6](../Onda/batch_metadata.py#L6) | função/método |

</details>

<details>
<summary><code>batch_metadata_ui.py</code> — 11 declarações</summary>

[Onda/batch_metadata_ui.py](../Onda/batch_metadata_ui.py)

Descrição do módulo no fonte: Selective multi-file metadata editor; originals are preserved by default.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `BatchMetadataEditor` | [11](../Onda/batch_metadata_ui.py#L11) | classe |
| `BatchMetadataEditor.__init__` | [12](../Onda/batch_metadata_ui.py#L12) | função/método |
| `BatchMetadataEditor.__init__.button` | [35](../Onda/batch_metadata_ui.py#L35) | função/método |
| `BatchMetadataEditor.refresh_files` | [72](../Onda/batch_metadata_ui.py#L72) | função/método |
| `BatchMetadataEditor.choose` | [79](../Onda/batch_metadata_ui.py#L79) | função/método |
| `BatchMetadataEditor.choose_cover` | [85](../Onda/batch_metadata_ui.py#L85) | função/método |
| `BatchMetadataEditor.remove_cover` | [91](../Onda/batch_metadata_ui.py#L91) | função/método |
| `BatchMetadataEditor.run` | [95](../Onda/batch_metadata_ui.py#L95) | função/método |
| `BatchMetadataEditor.run.worker` | [111](../Onda/batch_metadata_ui.py#L111) | função/método |
| `BatchMetadataEditor.poll` | [120](../Onda/batch_metadata_ui.py#L120) | função/método |
| `BatchMetadataEditor.close` | [144](../Onda/batch_metadata_ui.py#L144) | função/método |

</details>

<details>
<summary><code>brand_mark.py</code> — 2 declarações</summary>

[Onda/brand_mark.py](../Onda/brand_mark.py)

Descrição do módulo no fonte: ONDA's continuous wave, shared by native icons and generated vector resources.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `points` | [15](../Onda/brand_mark.py#L15) | função/método |
| `icon` | [28](../Onda/brand_mark.py#L28) | função/método |

</details>

<details>
<summary><code>cache_cleanup.py</code> — 6 declarações</summary>

[Onda/cache_cleanup.py](../Onda/cache_cleanup.py)

Descrição do módulo no fonte: Explicitly scoped reconstructible caches. Never traverse links or application data.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `root_path` | [6](../Onda/cache_cleanup.py#L6) | função/método |
| `linked` | [10](../Onda/cache_cleanup.py#L10) | função/método |
| `cache_files` | [16](../Onda/cache_cleanup.py#L16) | função/método |
| `cache_info` | [32](../Onda/cache_cleanup.py#L32) | função/método |
| `clear_cache` | [44](../Onda/cache_cleanup.py#L44) | função/método |
| `automatic_cleanup` | [67](../Onda/cache_cleanup.py#L67) | função/método |

</details>

<details>
<summary><code>cache_ui.py</code> — 6 declarações</summary>

[Onda/cache_ui.py](../Onda/cache_ui.py)

Descrição do módulo no fonte: Settings cache controls: disk work stays off Tk's event thread.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CacheControls` | [8](../Onda/cache_ui.py#L8) | classe |
| `CacheControls.__init__` | [9](../Onda/cache_ui.py#L9) | função/método |
| `CacheControls.run` | [20](../Onda/cache_ui.py#L20) | função/método |
| `CacheControls.run.worker` | [33](../Onda/cache_ui.py#L33) | função/método |
| `CacheControls.poll` | [37](../Onda/cache_ui.py#L37) | função/método |
| `CacheControls.on_destroy` | [48](../Onda/cache_ui.py#L48) | função/método |

</details>

<details>
<summary><code>catalog_aliases.py</code> — 2 declarações</summary>

[Onda/catalog_aliases.py](../Onda/catalog_aliases.py)

Descrição do módulo no fonte: Find localized titles using public catalog evidence, with bounded requests.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `alternate_records` | [8](../Onda/catalog_aliases.py#L8) | função/método |
| `alternate_records.add` | [10](../Onda/catalog_aliases.py#L10) | função/método |

</details>

<details>
<summary><code>catalog_details.py</code> — 2 declarações</summary>

[Onda/catalog_details.py](../Onda/catalog_details.py)

Descrição do módulo no fonte: Bounded metadata completion; a failed lookup never replaces the selected track.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `complete_record` | [7](../Onda/catalog_details.py#L7) | função/método |
| `collection_artwork` | [28](../Onda/catalog_details.py#L28) | função/método |

</details>

<details>
<summary><code>catalog_match.py</code> — 5 declarações</summary>

[Onda/catalog_match.py](../Onda/catalog_match.py)

Descrição do módulo no fonte: Conservative catalog matching, with explicit selection for uncertain releases.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CatalogChoiceRequired` | [9](../Onda/catalog_match.py#L9) | classe |
| `CatalogChoiceRequired.__init__` | [10](../Onda/catalog_match.py#L10) | função/método |
| `picker_event` | [15](../Onda/catalog_match.py#L15) | função/método |
| `rank_catalog` | [21](../Onda/catalog_match.py#L21) | função/método |
| `automatic_catalog` | [74](../Onda/catalog_match.py#L74) | função/método |

</details>

<details>
<summary><code>catalog_picker.py</code> — 3 declarações</summary>

[Onda/catalog_picker.py](../Onda/catalog_picker.py)

Descrição do módulo no fonte: Reuse the working selection controls for a catalog match, before YouTube.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CatalogPicker` | [7](../Onda/catalog_picker.py#L7) | classe |
| `CatalogPicker.__init__` | [8](../Onda/catalog_picker.py#L8) | função/método |
| `CatalogPicker.open_video` | [25](../Onda/catalog_picker.py#L25) | função/método |

</details>

<details>
<summary><code>catalog_recovery.py</code> — 1 declarações</summary>

[Onda/catalog_recovery.py](../Onda/catalog_recovery.py)

Descrição do módulo no fonte: Bounded alternate-video recovery; all normal matching checks remain active.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `download_recording` | [3](../Onda/catalog_recovery.py#L3) | função/método |

</details>

<details>
<summary><code>catalog_ui.py</code> — 37 declarações</summary>

[Onda/catalog_ui.py](../Onda/catalog_ui.py)

Descrição do módulo no fonte: Search → catalog result → preview and format → existing download queue.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `executable` | [24](../Onda/catalog_ui.py#L24) | função/método |
| `media_args` | [29](../Onda/catalog_ui.py#L29) | função/método |
| `cover_png` | [33](../Onda/catalog_ui.py#L33) | função/método |
| `cached_cover_png` | [39](../Onda/catalog_ui.py#L39) | função/método |
| `CatalogPane` | [52](../Onda/catalog_ui.py#L52) | classe |
| `CatalogPane.__init__` | [53](../Onda/catalog_ui.py#L53) | função/método |
| `CatalogPane.__init__.provider_changed` | [85](../Onda/catalog_ui.py#L85) | função/método |
| `CatalogPane.resize` | [148](../Onda/catalog_ui.py#L148) | função/método |
| `CatalogPane.enter_search` | [157](../Onda/catalog_ui.py#L157) | função/método |
| `CatalogPane.search` | [164](../Onda/catalog_ui.py#L164) | função/método |
| `CatalogPane.search.worker` | [195](../Onda/catalog_ui.py#L195) | função/método |
| `CatalogPane.refresh_search` | [212](../Onda/catalog_ui.py#L212) | função/método |
| `CatalogPane.compare_results` | [220](../Onda/catalog_ui.py#L220) | função/método |
| `CatalogPane.compare_results.update` | [231](../Onda/catalog_ui.py#L231) | função/método |
| `CatalogPane.search_filters` | [249](../Onda/catalog_ui.py#L249) | função/método |
| `CatalogPane.search_filters.apply` | [262](../Onda/catalog_ui.py#L262) | função/método |
| `CatalogPane.current` | [273](../Onda/catalog_ui.py#L273) | função/método |
| `CatalogPane.selected` | [277](../Onda/catalog_ui.py#L277) | função/método |
| `CatalogPane.selected.load_date` | [302](../Onda/catalog_ui.py#L302) | função/método |
| `CatalogPane.selected.worker` | [315](../Onda/catalog_ui.py#L315) | função/método |
| `CatalogPane.open_clicked` | [322](../Onda/catalog_ui.py#L322) | função/método |
| `CatalogPane.open_track` | [329](../Onda/catalog_ui.py#L329) | função/método |
| `CatalogPane.open_source` | [338](../Onda/catalog_ui.py#L338) | função/método |
| `CatalogPane.preview` | [343](../Onda/catalog_ui.py#L343) | função/método |
| `CatalogPane.stop_preview` | [366](../Onda/catalog_ui.py#L366) | função/método |
| `CatalogPane.stop_preview.reap` | [369](../Onda/catalog_ui.py#L369) | função/método |
| `CatalogPane.poll` | [380](../Onda/catalog_ui.py#L380) | função/método |
| `CatalogPane.cancel_catalog` | [446](../Onda/catalog_ui.py#L446) | função/método |
| `CatalogPane.confirm_catalog` | [453](../Onda/catalog_ui.py#L453) | função/método |
| `CatalogPane.confirm_catalog.worker` | [465](../Onda/catalog_ui.py#L465) | função/método |
| `CatalogPane.shutdown` | [476](../Onda/catalog_ui.py#L476) | função/método |
| `TrackDialog` | [486](../Onda/catalog_ui.py#L486) | classe |
| `TrackDialog.__init__` | [487](../Onda/catalog_ui.py#L487) | função/método |
| `TrackDialog.choice` | [541](../Onda/catalog_ui.py#L541) | função/método |
| `TrackDialog.update_format` | [548](../Onda/catalog_ui.py#L548) | função/método |
| `TrackDialog.update_estimate` | [558](../Onda/catalog_ui.py#L558) | função/método |
| `TrackDialog.submit` | [564](../Onda/catalog_ui.py#L564) | função/método |

</details>

<details>
<summary><code>clipboard_links.py</code> — 1 declarações</summary>

[Onda/clipboard_links.py](../Onda/clipboard_links.py)

Descrição do módulo no fonte: Offline clipboard URL recognition using the application's existing validators.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `recognize_link` | [8](../Onda/clipboard_links.py#L8) | função/método |

</details>

<details>
<summary><code>clipboard_watch.py</code> — 4 declarações</summary>

[Onda/clipboard_watch.py](../Onda/clipboard_watch.py)

Descrição do módulo no fonte: One lightweight clipboard timer, stopped with the desktop window.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ClipboardWatch` | [8](../Onda/clipboard_watch.py#L8) | classe |
| `ClipboardWatch.__init__` | [9](../Onda/clipboard_watch.py#L9) | função/método |
| `ClipboardWatch.poll` | [12](../Onda/clipboard_watch.py#L12) | função/método |
| `ClipboardWatch.shutdown` | [29](../Onda/clipboard_watch.py#L29) | função/método |

</details>

<details>
<summary><code>collection_coverage.py</code> — 4 declarações</summary>

[Onda/collection_coverage.py](../Onda/collection_coverage.py)

Descrição do módulo no fonte: Explicit collection coverage; unknown totals never imply completeness.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `annotate` | [7](../Onda/collection_coverage.py#L7) | função/método |
| `compare` | [27](../Onda/collection_coverage.py#L27) | função/método |
| `compare.keys` | [29](../Onda/collection_coverage.py#L29) | função/método |
| `compare_file` | [37](../Onda/collection_coverage.py#L37) | função/método |

</details>

<details>
<summary><code>converter_ui.py</code> — 12 declarações</summary>

[Onda/converter_ui.py](../Onda/converter_ui.py)

Descrição do módulo no fonte: Video conversion runs off Tk's thread with bounded process cancellation.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ConverterPane` | [12](../Onda/converter_ui.py#L12) | classe |
| `ConverterPane.__init__` | [13](../Onda/converter_ui.py#L13) | função/método |
| `ConverterPane.layout_options` | [52](../Onda/converter_ui.py#L52) | função/método |
| `ConverterPane.choose` | [67](../Onda/converter_ui.py#L67) | função/método |
| `ConverterPane.set_sources` | [70](../Onda/converter_ui.py#L70) | função/método |
| `ConverterPane.choose_batch` | [83](../Onda/converter_ui.py#L83) | função/método |
| `ConverterPane.preview` | [87](../Onda/converter_ui.py#L87) | função/método |
| `ConverterPane.start` | [91](../Onda/converter_ui.py#L91) | função/método |
| `ConverterPane.start.work` | [104](../Onda/converter_ui.py#L104) | função/método |
| `ConverterPane.poll` | [113](../Onda/converter_ui.py#L113) | função/método |
| `ConverterPane.cancel` | [124](../Onda/converter_ui.py#L124) | função/método |
| `ConverterPane.shutdown` | [125](../Onda/converter_ui.py#L125) | função/método |

</details>

<details>
<summary><code>cover_crop.py</code> — 1 declarações</summary>

[Onda/cover_crop.py](../Onda/cover_crop.py)

Descrição do módulo no fonte: Bounded square crop coordinates shared by desktop frontends.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `crop_box` | [2](../Onda/cover_crop.py#L2) | função/método |

</details>

<details>
<summary><code>cover_crop_ui.py</code> — 7 declarações</summary>

[Onda/cover_crop_ui.py](../Onda/cover_crop_ui.py)

Descrição do módulo no fonte: Local square cover cropper with a bounded preview and temporary output.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CoverCropper` | [13](../Onda/cover_crop_ui.py#L13) | classe |
| `CoverCropper.__init__` | [14](../Onda/cover_crop_ui.py#L14) | função/método |
| `CoverCropper.bounds` | [42](../Onda/cover_crop_ui.py#L42) | função/método |
| `CoverCropper.render` | [48](../Onda/cover_crop_ui.py#L48) | função/método |
| `CoverCropper.move` | [55](../Onda/cover_crop_ui.py#L55) | função/método |
| `CoverCropper.reset` | [61](../Onda/cover_crop_ui.py#L61) | função/método |
| `CoverCropper.apply` | [64](../Onda/cover_crop_ui.py#L64) | função/método |

</details>

<details>
<summary><code>credentials.py</code> — 8 declarações</summary>

[Onda/credentials.py](../Onda/credentials.py)

Descrição do módulo no fonte: Windows current-user DPAPI storage. Never falls back to plaintext.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CredentialError` | [10](../Onda/credentials.py#L10) | classe |
| `_crypt` | [14](../Onda/credentials.py#L14) | função/método |
| `_crypt.Blob` | [18](../Onda/credentials.py#L18) | classe |
| `CredentialStore` | [46](../Onda/credentials.py#L46) | classe |
| `CredentialStore.__init__` | [47](../Onda/credentials.py#L47) | função/método |
| `CredentialStore.load` | [51](../Onda/credentials.py#L51) | função/método |
| `CredentialStore.save` | [67](../Onda/credentials.py#L67) | função/método |
| `CredentialStore.forget` | [92](../Onda/credentials.py#L92) | função/método |

</details>

<details>
<summary><code>daily_desktop.py</code> — 14 declarações</summary>

[Onda/daily_desktop.py](../Onda/daily_desktop.py)

Descrição do módulo no fonte: Desktop completion policy and one bounded native-shell timer.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `settings_controls` | [11](../Onda/daily_desktop.py#L11) | função/método |
| `close_controls` | [16](../Onda/daily_desktop.py#L16) | função/método |
| `queue_progress` | [20](../Onda/daily_desktop.py#L20) | função/método |
| `DailyDesktop` | [30](../Onda/daily_desktop.py#L30) | classe |
| `DailyDesktop.__init__` | [31](../Onda/daily_desktop.py#L31) | função/método |
| `DailyDesktop.hide` | [45](../Onda/daily_desktop.py#L45) | função/método |
| `DailyDesktop.restore` | [51](../Onda/daily_desktop.py#L51) | função/método |
| `DailyDesktop.poll` | [55](../Onda/daily_desktop.py#L55) | função/método |
| `DailyDesktop.busy` | [86](../Onda/daily_desktop.py#L86) | função/método |
| `DailyDesktop.finished` | [89](../Onda/daily_desktop.py#L89) | função/método |
| `DailyDesktop.begin_shutdown` | [104](../Onda/daily_desktop.py#L104) | função/método |
| `DailyDesktop.begin_shutdown.tick` | [111](../Onda/daily_desktop.py#L111) | função/método |
| `DailyDesktop.cancel_shutdown` | [124](../Onda/daily_desktop.py#L124) | função/método |
| `DailyDesktop.close` | [130](../Onda/daily_desktop.py#L130) | função/método |

</details>

<details>
<summary><code>desktop_entry.py</code> — 2 declarações</summary>

[Onda/desktop_entry.py](../Onda/desktop_entry.py)

Descrição do módulo no fonte: Bootstrap for the private, relocatable Windows runtime.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `create_app` | [22](../Onda/desktop_entry.py#L22) | função/método |
| `self_test` | [44](../Onda/desktop_entry.py#L44) | função/método |

</details>

<details>
<summary><code>download_defaults.py</code> — 4 declarações</summary>

[Onda/download_defaults.py](../Onda/download_defaults.py)

Descrição do módulo no fonte: Effective download options, independent from spacing and tab visibility.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `download_cookies` | [5](../Onda/download_defaults.py#L5) | função/método |
| `supported_social` | [12](../Onda/download_defaults.py#L12) | função/método |
| `automatic_social` | [16](../Onda/download_defaults.py#L16) | função/método |
| `effective_download` | [19](../Onda/download_defaults.py#L19) | função/método |

</details>

<details>
<summary><code>download_feedback.py</code> — 2 declarações</summary>

[Onda/download_feedback.py](../Onda/download_feedback.py)

Descrição do módulo no fonte: User-facing download details derived only from reported engine events.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `failure_advice` | [2](../Onda/download_feedback.py#L2) | função/método |
| `download_detail` | [12](../Onda/download_feedback.py#L12) | função/método |

</details>

<details>
<summary><code>drop_input.py</code> — 4 declarações</summary>

[Onda/drop_input.py](../Onda/drop_input.py)

Descrição do módulo no fonte: Validate dropped media and links before handing them to existing workflows.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `dropped_files` | [7](../Onda/drop_input.py#L7) | função/método |
| `dropped_links` | [11](../Onda/drop_input.py#L11) | função/método |
| `receive` | [20](../Onda/drop_input.py#L20) | função/método |
| `receive.accept` | [44](../Onda/drop_input.py#L44) | função/método |

</details>

<details>
<summary><code>duplicate_links.py</code> — 5 declarações</summary>

[Onda/duplicate_links.py](../Onda/duplicate_links.py)

Descrição do módulo no fonte: Stable source identities: ignore sharing parameters, never guess by title.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `source_key` | [6](../Onda/duplicate_links.py#L6) | função/método |
| `job_source` | [43](../Onda/duplicate_links.py#L43) | função/método |
| `duplicate_job` | [56](../Onda/duplicate_links.py#L56) | função/método |
| `queue_duplicate_key` | [66](../Onda/duplicate_links.py#L66) | função/método |
| `queue_duplicate_key.freeze` | [71](../Onda/duplicate_links.py#L71) | função/método |

</details>

<details>
<summary><code>edition_evidence.py</code> — 7 declarações</summary>

[Onda/edition_evidence.py](../Onda/edition_evidence.py)

Descrição do módulo no fonte: Shared, conservative edition evidence for catalogs and audio sources.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `finite_positive` | [7](../Onda/edition_evidence.py#L7) | função/método |
| `recording_title` | [11](../Onda/edition_evidence.py#L11) | função/método |
| `date_parts` | [17](../Onda/edition_evidence.py#L17) | função/método |
| `same_release` | [29](../Onda/edition_evidence.py#L29) | função/método |
| `edition_details` | [35](../Onda/edition_evidence.py#L35) | função/método |
| `edition_conflicts` | [66](../Onda/edition_evidence.py#L66) | função/método |
| `differences` | [73](../Onda/edition_evidence.py#L73) | função/método |

</details>

<details>
<summary><code>effects_ui.py</code> — 25 declarações</summary>

[Onda/effects_ui.py](../Onda/effects_ui.py)

Descrição do módulo no fonte: Slowed + Reverb workspace: local audio, independent controls, preview/export.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `EffectsPane` | [32](../Onda/effects_ui.py#L32) | classe |
| `EffectsPane.__init__` | [33](../Onda/effects_ui.py#L33) | função/método |
| `EffectsPane.choose_lyrics` | [137](../Onda/effects_ui.py#L137) | função/método |
| `EffectsPane.choose` | [147](../Onda/effects_ui.py#L147) | função/método |
| `EffectsPane.use_file` | [152](../Onda/effects_ui.py#L152) | função/método |
| `EffectsPane.clock` | [165](../Onda/effects_ui.py#L165) | função/método |
| `EffectsPane.set_position` | [171](../Onda/effects_ui.py#L171) | função/método |
| `EffectsPane.source_changed` | [180](../Onda/effects_ui.py#L180) | função/método |
| `EffectsPane.probe_duration` | [190](../Onda/effects_ui.py#L190) | função/método |
| `EffectsPane.probe_duration.worker` | [193](../Onda/effects_ui.py#L193) | função/método |
| `EffectsPane.sync_position` | [206](../Onda/effects_ui.py#L206) | função/método |
| `EffectsPane.seek_begin` | [210](../Onda/effects_ui.py#L210) | função/método |
| `EffectsPane.seek_move` | [220](../Onda/effects_ui.py#L220) | função/método |
| `EffectsPane.seek_end` | [226](../Onda/effects_ui.py#L226) | função/método |
| `EffectsPane.seek_key` | [235](../Onda/effects_ui.py#L235) | função/método |
| `EffectsPane.changed` | [245](../Onda/effects_ui.py#L245) | função/método |
| `EffectsPane.apply_preset` | [257](../Onda/effects_ui.py#L257) | função/método |
| `EffectsPane.preview` | [264](../Onda/effects_ui.py#L264) | função/método |
| `EffectsPane.stop_preview` | [290](../Onda/effects_ui.py#L290) | função/método |
| `EffectsPane.export` | [299](../Onda/effects_ui.py#L299) | função/método |
| `EffectsPane.render` | [340](../Onda/effects_ui.py#L340) | função/método |
| `EffectsPane.poll` | [397](../Onda/effects_ui.py#L397) | função/método |
| `EffectsPane.cancel` | [452](../Onda/effects_ui.py#L452) | função/método |
| `EffectsPane.cancel.stop` | [454](../Onda/effects_ui.py#L454) | função/método |
| `EffectsPane.shutdown` | [460](../Onda/effects_ui.py#L460) | função/método |

</details>

<details>
<summary><code>effects_worker.py</code> — 2 declarações</summary>

[Onda/effects_worker.py](../Onda/effects_worker.py)

Descrição do módulo no fonte: Isolated FFmpeg effect render with progress and atomic output publication.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `preserve_tags` | [14](../Onda/effects_worker.py#L14) | função/método |
| `render` | [64](../Onda/effects_worker.py#L64) | função/método |

</details>

<details>
<summary><code>engine.py</code> — 34 declarações</summary>

[Onda/engine.py](../Onda/engine.py)

Descrição do módulo no fonte: Download engine: isolated worker, structured events, no UI dependencies.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `audio_bitrate` | [32](../Onda/engine.py#L32) | função/método |
| `validate_url` | [41](../Onda/engine.py#L41) | função/método |
| `binaries` | [61](../Onda/engine.py#L61) | função/método |
| `build_options` | [68](../Onda/engine.py#L68) | função/método |
| `reject_live` | [148](../Onda/engine.py#L148) | função/método |
| `download_with_recovery` | [153](../Onda/engine.py#L153) | função/método |
| `download_with_recovery.RememberAudioFormat` | [163](../Onda/engine.py#L163) | classe |
| `download_with_recovery.RememberAudioFormat.run` | [164](../Onda/engine.py#L164) | função/método |
| `emit` | [217](../Onda/engine.py#L217) | função/método |
| `Logger` | [221](../Onda/engine.py#L221) | classe |
| `Logger.__init__` | [222](../Onda/engine.py#L222) | função/método |
| `Logger.debug` | [229](../Onda/engine.py#L229) | função/método |
| `Logger.warning` | [233](../Onda/engine.py#L233) | função/método |
| `Logger.error` | [236](../Onda/engine.py#L236) | função/método |
| `ask_version` | [240](../Onda/engine.py#L240) | função/método |
| `ask_catalog` | [257](../Onda/engine.py#L257) | função/método |
| `ask_review` | [273](../Onda/engine.py#L273) | função/método |
| `ask_duplicate` | [283](../Onda/engine.py#L283) | função/método |
| `ask_media` | [294](../Onda/engine.py#L294) | função/método |
| `ask_flac_browser` | [305](../Onda/engine.py#L305) | função/método |
| `run_worker` | [317](../Onda/engine.py#L317) | função/método |
| `run_worker.progress` | [399](../Onda/engine.py#L399) | função/método |
| `run_worker.postprocess` | [412](../Onda/engine.py#L412) | função/método |
| `run_worker.CaptureFile` | [415](../Onda/engine.py#L415) | classe |
| `run_worker.CaptureFile.run` | [416](../Onda/engine.py#L416) | função/método |
| `run_worker.EstimateSize` | [445](../Onda/engine.py#L445) | classe |
| `run_worker.EstimateSize.run` | [446](../Onda/engine.py#L446) | função/método |
| `run_worker.VerifyRecording` | [453](../Onda/engine.py#L453) | classe |
| `run_worker.VerifyRecording.run` | [454](../Onda/engine.py#L454) | função/método |
| `run_worker.PrepareDirectMetadata` | [459](../Onda/engine.py#L459) | classe |
| `run_worker.PrepareDirectMetadata.run` | [460](../Onda/engine.py#L460) | função/método |
| `run_worker.configure` | [480](../Onda/engine.py#L480) | função/método |
| `run_worker.attempt_recording` | [494](../Onda/engine.py#L494) | função/método |
| `stop_process` | [528](../Onda/engine.py#L528) | função/método |

</details>

<details>
<summary><code>error_localization.py</code> — 4 declarações</summary>

[Onda/error_localization.py](../Onda/error_localization.py)

Descrição do módulo no fonte: Localize external diagnostics without changing paths, URLs or error codes.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `rules` | [10](../Onda/error_localization.py#L10) | função/método |
| `technical_text` | [18](../Onda/error_localization.py#L18) | função/método |
| `technical_text.replace` | [23](../Onda/error_localization.py#L23) | função/método |
| `error_text` | [32](../Onda/error_localization.py#L32) | função/método |

</details>

<details>
<summary><code>failure_report.py</code> — 3 declarações</summary>

[Onda/failure_report.py](../Onda/failure_report.py)

Descrição do módulo no fonte: Failure reports deliberately exclude configs, credentials and completed jobs.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `failed_rows` | [9](../Onda/failure_report.py#L9) | função/método |
| `report_text` | [16](../Onda/failure_report.py#L16) | função/método |
| `replace_metadata` | [21](../Onda/failure_report.py#L21) | função/método |

</details>

<details>
<summary><code>failure_ui.py</code> — 12 declarações</summary>

[Onda/failure_ui.py](../Onda/failure_ui.py)

Descrição do módulo no fonte: Post-run failures with export and a catalog search tied to the failed item.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `FailureWindow` | [11](../Onda/failure_ui.py#L11) | classe |
| `FailureWindow.__init__` | [12](../Onda/failure_ui.py#L12) | função/método |
| `FailureWindow.__init__.show_reason` | [37](../Onda/failure_ui.py#L37) | função/método |
| `FailureWindow.selected` | [59](../Onda/failure_ui.py#L59) | função/método |
| `FailureWindow.search` | [65](../Onda/failure_ui.py#L65) | função/método |
| `FailureWindow.search.worker` | [72](../Onda/failure_ui.py#L72) | função/método |
| `FailureWindow.poll` | [78](../Onda/failure_ui.py#L78) | função/método |
| `FailureWindow.apply` | [86](../Onda/failure_ui.py#L86) | função/método |
| `FailureWindow.retry` | [95](../Onda/failure_ui.py#L95) | função/método |
| `FailureWindow.save` | [103](../Onda/failure_ui.py#L103) | função/método |
| `FailureWindow.close` | [110](../Onda/failure_ui.py#L110) | função/método |
| `show_failures` | [113](../Onda/failure_ui.py#L113) | função/método |

</details>

<details>
<summary><code>ffmpeg_runtime.py</code> — 14 declarações</summary>

[Onda/ffmpeg_runtime.py](../Onda/ffmpeg_runtime.py)

Descrição do módulo no fonte: Download media tools directly from their publisher; never bundle them in ONDA.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadCancelled` | [23](../Onda/ffmpeg_runtime.py#L23) | classe |
| `data_root` | [27](../Onda/ffmpeg_runtime.py#L27) | função/método |
| `cache_folder` | [31](../Onda/ffmpeg_runtime.py#L31) | função/método |
| `complete_folder` | [35](../Onda/ffmpeg_runtime.py#L35) | função/método |
| `cached_folder` | [39](../Onda/ffmpeg_runtime.py#L39) | função/método |
| `existing_folder` | [51](../Onda/ffmpeg_runtime.py#L51) | função/método |
| `download_tools` | [72](../Onda/ffmpeg_runtime.py#L72) | função/método |
| `download_tools.check_cancelled` | [82](../Onda/ffmpeg_runtime.py#L82) | função/método |
| `download_with_window` | [142](../Onda/ffmpeg_runtime.py#L142) | função/método |
| `download_with_window.close` | [168](../Onda/ffmpeg_runtime.py#L168) | função/método |
| `download_with_window.worker` | [173](../Onda/ffmpeg_runtime.py#L173) | função/método |
| `download_with_window.worker.progress` | [177](../Onda/ffmpeg_runtime.py#L177) | função/método |
| `download_with_window.start` | [189](../Onda/ffmpeg_runtime.py#L189) | função/método |
| `download_with_window.poll` | [196](../Onda/ffmpeg_runtime.py#L196) | função/método |

</details>

<details>
<summary><code>file_output.py</code> — 5 declarações</summary>

[Onda/file_output.py](../Onda/file_output.py)

Descrição do módulo no fonte: Safe output directories and explicit collision choices.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `component` | [15](../Onda/file_output.py#L15) | função/método |
| `destination` | [24](../Onda/file_output.py#L24) | função/método |
| `publish` | [56](../Onda/file_output.py#L56) | função/método |
| `cleanup_completed_work` | [142](../Onda/file_output.py#L142) | função/método |
| `cleanup_completed_work.reparse` | [145](../Onda/file_output.py#L145) | função/método |

</details>

<details>
<summary><code>first_run.py</code> — 3 declarações</summary>

[Onda/first_run.py](../Onda/first_run.py)

Descrição do módulo no fonte: One-time, per-user welcome state independent of saved preferences.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `FirstRunStore` | [5](../Onda/first_run.py#L5) | classe |
| `FirstRunStore.__init__` | [6](../Onda/first_run.py#L6) | função/método |
| `FirstRunStore.claim` | [9](../Onda/first_run.py#L9) | função/método |

</details>

<details>
<summary><code>flac_browser.py</code> — 3 declarações</summary>

[Onda/flac_browser.py](../Onda/flac_browser.py)

Descrição do módulo no fonte: Browser-assisted FLAC import: no challenge tokens or private service API.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `search_url` | [15](../Onda/flac_browser.py#L15) | função/método |
| `validate_flac` | [20](../Onda/flac_browser.py#L20) | função/método |
| `import_flac` | [41](../Onda/flac_browser.py#L41) | função/método |

</details>

<details>
<summary><code>flac_browser_ui.py</code> — 4 declarações</summary>

[Onda/flac_browser_ui.py](../Onda/flac_browser_ui.py)

Descrição do módulo no fonte: Small non-blocking desktop handoff to the user's browser.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `FlacBrowserDialog` | [9](../Onda/flac_browser_ui.py#L9) | classe |
| `FlacBrowserDialog.__init__` | [10](../Onda/flac_browser_ui.py#L10) | função/método |
| `FlacBrowserDialog.open_browser` | [34](../Onda/flac_browser_ui.py#L34) | função/método |
| `FlacBrowserDialog.choose` | [38](../Onda/flac_browser_ui.py#L38) | função/método |

</details>

<details>
<summary><code>history_details.py</code> — 4 declarações</summary>

[Onda/history_details.py](../Onda/history_details.py)

Descrição do módulo no fonte: Read local history details without a network request or changing files.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `history_details` | [6](../Onda/history_details.py#L6) | função/método |
| `_cached_details` | [15](../Onda/history_details.py#L15) | função/método |
| `detail_lines` | [26](../Onda/history_details.py#L26) | função/método |
| `history_platform` | [36](../Onda/history_details.py#L36) | função/método |

</details>

<details>
<summary><code>history_origin.py</code> — 1 declarações</summary>

[Onda/history_origin.py](../Onda/history_origin.py)

Descrição do módulo no fonte: Resolve recorded download identities into browser links, never local commands.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `history_origin` | [5](../Onda/history_origin.py#L5) | função/método |

</details>

<details>
<summary><code>history_ui.py</code> — 25 declarações</summary>

[Onda/history_ui.py](../Onda/history_ui.py)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `HistoryPane` | [13](../Onda/history_ui.py#L13) | classe |
| `HistoryPane.__init__` | [14](../Onda/history_ui.py#L14) | função/método |
| `HistoryPane.schedule_search` | [75](../Onda/history_ui.py#L75) | função/método |
| `HistoryPane.shutdown` | [80](../Onda/history_ui.py#L80) | função/método |
| `HistoryPane.cancel_search` | [88](../Onda/history_ui.py#L88) | função/método |
| `HistoryPane.refresh` | [93](../Onda/history_ui.py#L93) | função/método |
| `HistoryPane.refresh.load_origins` | [127](../Onda/history_ui.py#L127) | função/método |
| `HistoryPane.render_cards` | [134](../Onda/history_ui.py#L134) | função/método |
| `HistoryPane.render_cards.worker` | [173](../Onda/history_ui.py#L173) | função/método |
| `HistoryPane.resize_cards` | [181](../Onda/history_ui.py#L181) | função/método |
| `HistoryPane.more_cards` | [192](../Onda/history_ui.py#L192) | função/método |
| `HistoryPane.select_card` | [196](../Onda/history_ui.py#L196) | função/método |
| `HistoryPane.toggle_card` | [202](../Onda/history_ui.py#L202) | função/método |
| `HistoryPane.edit_batch` | [207](../Onda/history_ui.py#L207) | função/método |
| `HistoryPane.highlight_cards` | [212](../Onda/history_ui.py#L212) | função/método |
| `HistoryPane.card_action` | [224](../Onda/history_ui.py#L224) | função/método |
| `HistoryPane.poll_cards` | [228](../Onda/history_ui.py#L228) | função/método |
| `HistoryPane.current` | [256](../Onda/history_ui.py#L256) | função/método |
| `HistoryPane.origin` | [266](../Onda/history_ui.py#L266) | função/método |
| `HistoryPane.update_origin_button` | [270](../Onda/history_ui.py#L270) | função/método |
| `HistoryPane.open_origin` | [272](../Onda/history_ui.py#L272) | função/método |
| `HistoryPane.open` | [278](../Onda/history_ui.py#L278) | função/método |
| `HistoryPane.effects` | [291](../Onda/history_ui.py#L291) | função/método |
| `HistoryPane.edit_audio` | [297](../Onda/history_ui.py#L297) | função/método |
| `HistoryPane.clear` | [305](../Onda/history_ui.py#L305) | função/método |

</details>

<details>
<summary><code>i18n.py</code> — 6 declarações</summary>

[Onda/i18n.py](../Onda/i18n.py)

Descrição do módulo no fonte: Shared UI catalog; persisted identifiers and user content stay unchanged.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalize_language` | [11](../Onda/i18n.py#L11) | função/método |
| `set_language` | [15](../Onda/i18n.py#L15) | função/método |
| `catalog` | [21](../Onda/i18n.py#L21) | função/método |
| `english_catalog` | [27](../Onda/i18n.py#L27) | função/método |
| `patterns` | [32](../Onda/i18n.py#L32) | função/método |
| `tr` | [45](../Onda/i18n.py#L45) | função/método |

</details>

<details>
<summary><code>i18n_tk.py</code> — 13 declarações</summary>

[Onda/i18n_tk.py](../Onda/i18n_tk.py)

Descrição do módulo no fonte: Translate rendered Tk labels and choices while retaining canonical values.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `display_var` | [7](../Onda/i18n_tk.py#L7) | função/método |
| `display_var.update` | [12](../Onda/i18n_tk.py#L12) | função/método |
| `TranslatedCombobox` | [22](../Onda/i18n_tk.py#L22) | classe |
| `TranslatedCombobox.__init__` | [24](../Onda/i18n_tk.py#L24) | função/método |
| `TranslatedCombobox._translated_choices` | [37](../Onda/i18n_tk.py#L37) | função/método |
| `TranslatedCombobox._label` | [41](../Onda/i18n_tk.py#L41) | função/método |
| `TranslatedCombobox._from_source` | [45](../Onda/i18n_tk.py#L45) | função/método |
| `TranslatedCombobox._from_display` | [51](../Onda/i18n_tk.py#L51) | função/método |
| `TranslatedCombobox.cget` | [59](../Onda/i18n_tk.py#L59) | função/método |
| `TranslatedCombobox.get` | [64](../Onda/i18n_tk.py#L64) | função/método |
| `TranslatedCombobox.set` | [67](../Onda/i18n_tk.py#L67) | função/método |
| `TranslatedCombobox.configure` | [70](../Onda/i18n_tk.py#L70) | função/método |
| `TranslatedCombobox._cleanup` | [88](../Onda/i18n_tk.py#L88) | função/método |

</details>

<details>
<summary><code>image_output.py</code> — 5 declarações</summary>

[Onda/image_output.py](../Onda/image_output.py)

Descrição do módulo no fonte: Image export options shared by preview and downloads.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `validate_options` | [14](../Onda/image_output.py#L14) | função/método |
| `output_size` | [27](../Onda/image_output.py#L27) | função/método |
| `transform_image` | [38](../Onda/image_output.py#L38) | função/método |
| `_render_image` | [56](../Onda/image_output.py#L56) | função/método |
| `open_preview` | [108](../Onda/image_output.py#L108) | função/método |

</details>

<details>
<summary><code>images_ui.py</code> — 12 declarações</summary>

[Onda/images_ui.py](../Onda/images_ui.py)

Descrição do módulo no fonte: Dedicated image controls; transfers still use the shared supervised queue.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ImagesPane` | [17](../Onda/images_ui.py#L17) | classe |
| `ImagesPane.__init__` | [18](../Onda/images_ui.py#L18) | função/método |
| `ImagesPane.options` | [74](../Onda/images_ui.py#L74) | função/método |
| `ImagesPane.changed` | [87](../Onda/images_ui.py#L87) | função/método |
| `ImagesPane.link_changed` | [99](../Onda/images_ui.py#L99) | função/método |
| `ImagesPane.enqueue` | [104](../Onda/images_ui.py#L104) | função/método |
| `ImagesPane.preview` | [120](../Onda/images_ui.py#L120) | função/método |
| `ImagesPane.preview.work` | [135](../Onda/images_ui.py#L135) | função/método |
| `ImagesPane.preview.work.emit` | [140](../Onda/images_ui.py#L140) | função/método |
| `ImagesPane.render_preview` | [153](../Onda/images_ui.py#L153) | função/método |
| `ImagesPane.poll` | [170](../Onda/images_ui.py#L170) | função/método |
| `ImagesPane.shutdown` | [188](../Onda/images_ui.py#L188) | função/método |

</details>

<details>
<summary><code>instagram_media.py</code> — 5 declarações</summary>

[Onda/instagram_media.py](../Onda/instagram_media.py)

Descrição do módulo no fonte: Use yt-dlp's current Instagram session/API support without dropping photos.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `is_instagram` | [9](../Onda/instagram_media.py#L9) | função/método |
| `InstagramMediaIE` | [14](../Onda/instagram_media.py#L14) | classe |
| `InstagramMediaIE._extract_product` | [15](../Onda/instagram_media.py#L15) | função/método |
| `product_items` | [21](../Onda/instagram_media.py#L21) | função/método |
| `instagram_items` | [52](../Onda/instagram_media.py#L52) | função/método |

</details>

<details>
<summary><code>interface_fonts.py</code> — 4 declarações</summary>

[Onda/interface_fonts.py](../Onda/interface_fonts.py)

Descrição do módulo no fonte: Font choices backed by local system fonts; no downloads required.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `font_scale` | [6](../Onda/interface_fonts.py#L6) | função/método |
| `font_choices` | [21](../Onda/interface_fonts.py#L21) | função/método |
| `font_family` | [26](../Onda/interface_fonts.py#L26) | função/método |
| `valid_font` | [34](../Onda/interface_fonts.py#L34) | função/método |

</details>

<details>
<summary><code>interface_spacing.py</code> — 3 declarações</summary>

[Onda/interface_spacing.py](../Onda/interface_spacing.py)

Descrição do módulo no fonte: Live layout density without scaling fonts, icons or minimum control sizes.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `spacing_scale` | [7](../Onda/interface_spacing.py#L7) | função/método |
| `_pixels` | [10](../Onda/interface_spacing.py#L10) | função/método |
| `apply_spacing` | [14](../Onda/interface_spacing.py#L14) | função/método |

</details>

<details>
<summary><code>jukebox.py</code> — 45 declarações</summary>

[Onda/jukebox.py](../Onda/jukebox.py)

Descrição do módulo no fonte: Local beat graph and continuous PCM renderer shared by desktop and Android.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `Cancelled` | [16](../Onda/jukebox.py#L16) | classe |
| `check` | [18](../Onda/jukebox.py#L18) | função/método |
| `_run` | [21](../Onda/jukebox.py#L21) | função/método |
| `_run.drain` | [25](../Onda/jukebox.py#L25) | função/método |
| `_fft_setup` | [39](../Onda/jukebox.py#L39) | função/método |
| `_features` | [55](../Onda/jukebox.py#L55) | função/método |
| `_features.norm` | [68](../Onda/jukebox.py#L68) | função/método |
| `energy_matched_links` | [74](../Onda/jukebox.py#L74) | função/método |
| `energy_matched_links.rms` | [77](../Onda/jukebox.py#L77) | função/método |
| `energy_matched_links.compatible` | [80](../Onda/jukebox.py#L80) | função/método |
| `pcm_energy_levels` | [87](../Onda/jukebox.py#L87) | função/método |
| `pcm_boundary_levels` | [98](../Onda/jukebox.py#L98) | função/método |
| `with_join_features` | [116](../Onda/jukebox.py#L116) | função/método |
| `join_context` | [134](../Onda/jukebox.py#L134) | função/método |
| `join_context.cosine` | [144](../Onda/jukebox.py#L144) | função/método |
| `sustained_midrange` | [153](../Onda/jukebox.py#L153) | função/método |
| `join_fade_seconds` | [162](../Onda/jukebox.py#L162) | função/método |
| `refine_energy` | [171](../Onda/jukebox.py#L171) | função/método |
| `phrase_similarity` | [180](../Onda/jukebox.py#L180) | função/método |
| `phrase_similarity.cosine` | [189](../Onda/jukebox.py#L189) | função/método |
| `analyse_wave` | [198](../Onda/jukebox.py#L198) | função/método |
| `cache_root` | [266](../Onda/jukebox.py#L266) | função/método |
| `prepare` | [270](../Onda/jukebox.py#L270) | função/método |
| `validate_model` | [329](../Onda/jukebox.py#L329) | função/método |
| `loop_boundary` | [336](../Onda/jukebox.py#L336) | função/método |
| `branch_probability` | [355](../Onda/jukebox.py#L355) | função/método |
| `variation_neighbors` | [361](../Onda/jukebox.py#L361) | função/método |
| `Session` | [367](../Onda/jukebox.py#L367) | classe |
| `Session.__init__` | [368](../Onda/jukebox.py#L368) | função/método |
| `Session._read` | [382](../Onda/jukebox.py#L382) | função/método |
| `Session.seek` | [385](../Onda/jukebox.py#L385) | função/método |
| `Session.chunk` | [391](../Onda/jukebox.py#L391) | função/método |
| `Session.chunk.seam_cost` | [422](../Onda/jukebox.py#L422) | função/método |
| `Session.close` | [479](../Onda/jukebox.py#L479) | função/método |
| `cache_in_use` | [486](../Onda/jukebox.py#L486) | função/método |
| `SearchLog` | [489](../Onda/jukebox.py#L489) | classe |
| `SearchLog.__init__` | [490](../Onda/jukebox.py#L490) | função/método |
| `SearchLog.debug` | [494](../Onda/jukebox.py#L494) | função/método |
| `SearchLog.warning` | [495](../Onda/jukebox.py#L495) | função/método |
| `SearchLog.error` | [496](../Onda/jukebox.py#L496) | função/método |
| `fetch_audio` | [498](../Onda/jukebox.py#L498) | função/método |
| `fetch_audio.Capture` | [520](../Onda/jukebox.py#L520) | classe |
| `fetch_audio.Capture.run` | [521](../Onda/jukebox.py#L521) | função/método |
| `fetch_audio.hook` | [526](../Onda/jukebox.py#L526) | função/método |
| `fetch_audio.configure` | [534](../Onda/jukebox.py#L534) | função/método |

</details>

<details>
<summary><code>jukebox_audio.py</code> — 11 declarações</summary>

[Onda/jukebox_audio.py](../Onda/jukebox_audio.py)

Descrição do módulo no fonte: Small bounded PCM output for Windows: two queued buffers, no per-beat players.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `WaveFormat` | [8](../Onda/jukebox_audio.py#L8) | classe |
| `WaveHeader` | [11](../Onda/jukebox_audio.py#L11) | classe |
| `WaveTime` | [14](../Onda/jukebox_audio.py#L14) | classe |
| `PcmOutput` | [17](../Onda/jukebox_audio.py#L17) | classe |
| `PcmOutput.__init__` | [18](../Onda/jukebox_audio.py#L18) | função/método |
| `PcmOutput._check` | [31](../Onda/jukebox_audio.py#L31) | função/método |
| `PcmOutput.control` | [33](../Onda/jukebox_audio.py#L33) | função/método |
| `PcmOutput.notify` | [40](../Onda/jukebox_audio.py#L40) | função/método |
| `PcmOutput._drain` | [51](../Onda/jukebox_audio.py#L51) | função/método |
| `PcmOutput.write` | [59](../Onda/jukebox_audio.py#L59) | função/método |
| `PcmOutput.close` | [76](../Onda/jukebox_audio.py#L76) | função/método |

</details>

<details>
<summary><code>jukebox_equalizer.py</code> — 9 declarações</summary>

[Onda/jukebox_equalizer.py](../Onda/jukebox_equalizer.py)

Descrição do módulo no fonte: Ten peaking biquads, stereo state and settings restricted to Jukebox PCM.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `number` | [11](../Onda/jukebox_equalizer.py#L11) | função/método |
| `clean` | [17](../Onda/jukebox_equalizer.py#L17) | função/método |
| `presets` | [32](../Onda/jukebox_equalizer.py#L32) | função/método |
| `preset_name` | [36](../Onda/jukebox_equalizer.py#L36) | função/método |
| `Equalizer` | [42](../Onda/jukebox_equalizer.py#L42) | classe |
| `Equalizer.__init__` | [43](../Onda/jukebox_equalizer.py#L43) | função/método |
| `Equalizer.configure` | [45](../Onda/jukebox_equalizer.py#L45) | função/método |
| `Equalizer.process` | [62](../Onda/jukebox_equalizer.py#L62) | função/método |
| `Equalizer._process` | [76](../Onda/jukebox_equalizer.py#L76) | função/método |

</details>

<details>
<summary><code>jukebox_equalizer_ui.py</code> — 7 declarações</summary>

[Onda/jukebox_equalizer_ui.py](../Onda/jukebox_equalizer_ui.py)

Descrição do módulo no fonte: Compact, live parametric equalizer editor for the desktop Jukebox.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `EqualizerWindow` | [8](../Onda/jukebox_equalizer_ui.py#L8) | classe |
| `EqualizerWindow.__init__` | [9](../Onda/jukebox_equalizer_ui.py#L9) | função/método |
| `EqualizerWindow.apply_preset` | [43](../Onda/jukebox_equalizer_ui.py#L43) | função/método |
| `EqualizerWindow.labels` | [50](../Onda/jukebox_equalizer_ui.py#L50) | função/método |
| `EqualizerWindow.save` | [54](../Onda/jukebox_equalizer_ui.py#L54) | função/método |
| `EqualizerWindow.reset` | [61](../Onda/jukebox_equalizer_ui.py#L61) | função/método |
| `EqualizerWindow.finish` | [64](../Onda/jukebox_equalizer_ui.py#L64) | função/método |

</details>

<details>
<summary><code>jukebox_stream.py</code> — 13 declarações</summary>

[Onda/jukebox_stream.py](../Onda/jukebox_stream.py)

Descrição do módulo no fonte: Continuous, bounded PCM crossfades shared by Windows and Android.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `mix_pcm` | [7](../Onda/jukebox_stream.py#L7) | função/método |
| `_Buffered` | [20](../Onda/jukebox_stream.py#L20) | classe |
| `_Buffered.__init__` | [21](../Onda/jukebox_stream.py#L21) | função/método |
| `_Buffered.fill` | [23](../Onda/jukebox_stream.py#L23) | função/método |
| `_Buffered.take` | [27](../Onda/jukebox_stream.py#L27) | função/método |
| `_Buffered.close` | [32](../Onda/jukebox_stream.py#L32) | função/método |
| `Stream` | [35](../Onda/jukebox_stream.py#L35) | classe |
| `Stream.__init__` | [36](../Onda/jukebox_stream.py#L36) | função/método |
| `Stream.transitioning` | [39](../Onda/jukebox_stream.py#L39) | função/método |
| `Stream.switch` | [40](../Onda/jukebox_stream.py#L40) | função/método |
| `Stream.seek` | [48](../Onda/jukebox_stream.py#L48) | função/método |
| `Stream.chunk` | [53](../Onda/jukebox_stream.py#L53) | função/método |
| `Stream.close` | [67](../Onda/jukebox_stream.py#L67) | função/método |

</details>

<details>
<summary><code>jukebox_ui.py</code> — 33 declarações</summary>

[Onda/jukebox_ui.py](../Onda/jukebox_ui.py)

Descrição do módulo no fonte: Desktop Jukebox workspace, reusing catalog search and the shared PCM engine.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxPane` | [11](../Onda/jukebox_ui.py#L11) | classe |
| `JukeboxPane.__init__` | [12](../Onda/jukebox_ui.py#L12) | função/método |
| `JukeboxPane.open_equalizer` | [60](../Onda/jukebox_ui.py#L60) | função/método |
| `JukeboxPane.busy` | [66](../Onda/jukebox_ui.py#L66) | função/método |
| `JukeboxPane.layout` | [67](../Onda/jukebox_ui.py#L67) | função/método |
| `JukeboxPane.config` | [74](../Onda/jukebox_ui.py#L74) | função/método |
| `JukeboxPane.choose` | [76](../Onda/jukebox_ui.py#L76) | função/método |
| `JukeboxPane.set_source` | [79](../Onda/jukebox_ui.py#L79) | função/método |
| `JukeboxPane.task` | [83](../Onda/jukebox_ui.py#L83) | função/método |
| `JukeboxPane.task.emit` | [86](../Onda/jukebox_ui.py#L86) | função/método |
| `JukeboxPane.task.worker` | [87](../Onda/jukebox_ui.py#L87) | função/método |
| `JukeboxPane.analyse` | [97](../Onda/jukebox_ui.py#L97) | função/método |
| `JukeboxPane.analyse.analyse` | [99](../Onda/jukebox_ui.py#L99) | função/método |
| `JukeboxPane.search` | [111](../Onda/jukebox_ui.py#L111) | função/método |
| `JukeboxPane.search.search` | [119](../Onda/jukebox_ui.py#L119) | função/método |
| `JukeboxPane.load_selected` | [126](../Onda/jukebox_ui.py#L126) | função/método |
| `JukeboxPane.load_selected.load` | [131](../Onda/jukebox_ui.py#L131) | função/método |
| `JukeboxPane.seek_point` | [141](../Onda/jukebox_ui.py#L141) | função/método |
| `JukeboxPane.set_track_info` | [150](../Onda/jukebox_ui.py#L150) | função/método |
| `JukeboxPane.update_params` | [156](../Onda/jukebox_ui.py#L156) | função/método |
| `JukeboxPane.toggle_normal` | [159](../Onda/jukebox_ui.py#L159) | função/método |
| `JukeboxPane.play_pause` | [161](../Onda/jukebox_ui.py#L161) | função/método |
| `JukeboxPane.play_pause.worker` | [172](../Onda/jukebox_ui.py#L172) | função/método |
| `JukeboxPane.play_pause.worker.progress` | [177](../Onda/jukebox_ui.py#L177) | função/método |
| `JukeboxPane.stop` | [202](../Onda/jukebox_ui.py#L202) | função/método |
| `JukeboxPane.stop_preview` | [204](../Onda/jukebox_ui.py#L204) | função/método |
| `JukeboxPane.draw` | [208](../Onda/jukebox_ui.py#L208) | função/método |
| `JukeboxPane.draw.point` | [218](../Onda/jukebox_ui.py#L218) | função/método |
| `JukeboxPane.move_marker` | [236](../Onda/jukebox_ui.py#L236) | função/método |
| `JukeboxPane.move_marker.point` | [260](../Onda/jukebox_ui.py#L260) | função/método |
| `JukeboxPane.poll` | [265](../Onda/jukebox_ui.py#L265) | função/método |
| `JukeboxPane.sync_media` | [305](../Onda/jukebox_ui.py#L305) | função/método |
| `JukeboxPane.shutdown` | [326](../Onda/jukebox_ui.py#L326) | função/método |

</details>

<details>
<summary><code>keyboard_shortcuts.py</code> — 15 declarações</summary>

[Onda/keyboard_shortcuts.py](../Onda/keyboard_shortcuts.py)

Descrição do módulo no fonte: Desktop shortcuts scoped to the main window and the relevant page.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `KeyboardShortcuts` | [36](../Onda/keyboard_shortcuts.py#L36) | classe |
| `KeyboardShortcuts.__init__` | [37](../Onda/keyboard_shortcuts.py#L37) | função/método |
| `KeyboardShortcuts.rebind` | [48](../Onda/keyboard_shortcuts.py#L48) | função/método |
| `KeyboardShortcuts.set_shortcut` | [63](../Onda/keyboard_shortcuts.py#L63) | função/método |
| `KeyboardShortcuts.fill_reference` | [70](../Onda/keyboard_shortcuts.py#L70) | função/método |
| `KeyboardShortcuts.action_label` | [83](../Onda/keyboard_shortcuts.py#L83) | função/método |
| `KeyboardShortcuts.edit_selected` | [92](../Onda/keyboard_shortcuts.py#L92) | função/método |
| `KeyboardShortcuts.edit_selected.capture` | [103](../Onda/keyboard_shortcuts.py#L103) | função/método |
| `KeyboardShortcuts.edit_selected.save` | [116](../Onda/keyboard_shortcuts.py#L116) | função/método |
| `KeyboardShortcuts.attach` | [128](../Onda/keyboard_shortcuts.py#L128) | função/método |
| `KeyboardShortcuts.allowed` | [140](../Onda/keyboard_shortcuts.py#L140) | função/método |
| `KeyboardShortcuts.editing` | [146](../Onda/keyboard_shortcuts.py#L146) | função/método |
| `KeyboardShortcuts.select` | [150](../Onda/keyboard_shortcuts.py#L150) | função/método |
| `KeyboardShortcuts.dispatch` | [157](../Onda/keyboard_shortcuts.py#L157) | função/método |
| `KeyboardShortcuts.show_help` | [224](../Onda/keyboard_shortcuts.py#L224) | função/método |

</details>

<details>
<summary><code>kwai.py</code> — 8 declarações</summary>

[Onda/kwai.py](../Onda/kwai.py)

Descrição do módulo no fonte: Read Kwai's public Nuxt post data as data, without executing page scripts.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `object_at` | [10](../Onda/kwai.py#L10) | função/método |
| `normalize_literal` | [35](../Onda/kwai.py#L35) | função/método |
| `nuxt_objects` | [43](../Onda/kwai.py#L43) | função/método |
| `walk` | [62](../Onda/kwai.py#L62) | função/método |
| `find_post` | [72](../Onda/kwai.py#L72) | função/método |
| `find_schema_video` | [94](../Onda/kwai.py#L94) | função/método |
| `OndaKwaiIE` | [124](../Onda/kwai.py#L124) | classe |
| `OndaKwaiIE._real_extract` | [128](../Onda/kwai.py#L128) | função/método |

</details>

<details>
<summary><code>lazy_ui.py</code> — 11 declarações</summary>

[Onda/lazy_ui.py](../Onda/lazy_ui.py)

Descrição do módulo no fonte: Notebook containers which create their content only when needed.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LazyPane` | [6](../Onda/lazy_ui.py#L6) | classe |
| `LazyPane.__init__` | [7](../Onda/lazy_ui.py#L7) | função/método |
| `LazyPane.ensure_ready` | [17](../Onda/lazy_ui.py#L17) | função/método |
| `LazyPane.busy` | [29](../Onda/lazy_ui.py#L29) | função/método |
| `LazyPane.stop_preview` | [32](../Onda/lazy_ui.py#L32) | função/método |
| `LazyPane.shutdown` | [36](../Onda/lazy_ui.py#L36) | função/método |
| `LazyPane.refresh` | [40](../Onda/lazy_ui.py#L40) | função/método |
| `LazyPane.__getattribute__` | [55](../Onda/lazy_ui.py#L55) | função/método |
| `LazyPane.__setattr__` | [60](../Onda/lazy_ui.py#L60) | função/método |
| `LazyPane.__delattr__` | [66](../Onda/lazy_ui.py#L66) | função/método |
| `LazyPane.__getattr__` | [72](../Onda/lazy_ui.py#L72) | função/método |

</details>

<details>
<summary><code>library.py</code> — 12 declarações</summary>

[Onda/library.py](../Onda/library.py)

Descrição do módulo no fonte: Local queue/history, without account credentials or session tokens.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LibraryStore` | [12](../Onda/library.py#L12) | classe |
| `LibraryStore.__init__` | [13](../Onda/library.py#L13) | função/método |
| `LibraryStore.connect` | [30](../Onda/library.py#L30) | função/método |
| `LibraryStore.save_queue` | [38](../Onda/library.py#L38) | função/método |
| `LibraryStore.load_queue` | [56](../Onda/library.py#L56) | função/método |
| `LibraryStore.add_history` | [69](../Onda/library.py#L69) | função/método |
| `LibraryStore.history` | [76](../Onda/library.py#L76) | função/método |
| `LibraryStore.remove_history` | [90](../Onda/library.py#L90) | função/método |
| `LibraryStore.restore_history` | [97](../Onda/library.py#L97) | função/método |
| `LibraryStore.find_duplicate` | [106](../Onda/library.py#L106) | função/método |
| `LibraryStore.comparison_history` | [115](../Onda/library.py#L115) | função/método |
| `LibraryStore.clear_history` | [120](../Onda/library.py#L120) | função/método |

</details>

<details>
<summary><code>list_context.py</code> — 26 declarações</summary>

[Onda/list_context.py](../Onda/list_context.py)

Descrição do módulo no fonte: Context menus share the same commands and state as each list's controls.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `action` | [7](../Onda/list_context.py#L7) | função/método |
| `button` | [11](../Onda/list_context.py#L11) | função/método |
| `copy_text` | [15](../Onda/list_context.py#L15) | função/método |
| `copy_rows` | [21](../Onda/list_context.py#L21) | função/método |
| `ListContext` | [26](../Onda/list_context.py#L26) | classe |
| `ListContext.__init__` | [27](../Onda/list_context.py#L27) | função/método |
| `ListContext.select` | [34](../Onda/list_context.py#L34) | função/método |
| `ListContext.mouse` | [42](../Onda/list_context.py#L42) | função/método |
| `ListContext.keyboard` | [52](../Onda/list_context.py#L52) | função/método |
| `ListContext.popup` | [60](../Onda/list_context.py#L60) | função/método |
| `ListContext.card` | [84](../Onda/list_context.py#L84) | função/método |
| `ListContext.card.show` | [85](../Onda/list_context.py#L85) | função/método |
| `ListContext.card.keyboard` | [88](../Onda/list_context.py#L88) | função/método |
| `display_actions` | [97](../Onda/list_context.py#L97) | função/método |
| `queue_actions` | [102](../Onda/list_context.py#L102) | função/método |
| `bind_queue` | [116](../Onda/list_context.py#L116) | função/método |
| `bind_history` | [120](../Onda/list_context.py#L120) | função/método |
| `bind_history.actions` | [121](../Onda/list_context.py#L121) | função/método |
| `bind_history.changed` | [128](../Onda/list_context.py#L128) | função/método |
| `bind_catalog` | [137](../Onda/list_context.py#L137) | função/método |
| `bind_playlist` | [141](../Onda/list_context.py#L141) | função/método |
| `bind_playlist.actions` | [142](../Onda/list_context.py#L142) | função/método |
| `bind_metadata` | [152](../Onda/list_context.py#L152) | função/método |
| `bind_version` | [156](../Onda/list_context.py#L156) | função/método |
| `bind_playlist_list` | [161](../Onda/list_context.py#L161) | função/método |
| `bind_playlist_list.actions` | [163](../Onda/list_context.py#L163) | função/método |

</details>

<details>
<summary><code>lossless_source.py</code> — 8 declarações</summary>

[Onda/lossless_source.py](../Onda/lossless_source.py)

Descrição do módulo no fonte: Direct public FLAC source. No browser session, secrets or lossy fallback.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `rank_matches` | [12](../Onda/lossless_source.py#L12) | função/método |
| `choose_match` | [49](../Onda/lossless_source.py#L49) | função/método |
| `retry_delay` | [77](../Onda/lossless_source.py#L77) | função/método |
| `wait_retry` | [93](../Onda/lossless_source.py#L93) | função/método |
| `validator` | [103](../Onda/lossless_source.py#L103) | função/método |
| `fetch_file` | [108](../Onda/lossless_source.py#L108) | função/método |
| `search_matches` | [201](../Onda/lossless_source.py#L201) | função/método |
| `download_flac` | [231](../Onda/lossless_source.py#L231) | função/método |

</details>

<details>
<summary><code>lyrics_service.py</code> — 8 declarações</summary>

[Onda/lyrics_service.py](../Onda/lyrics_service.py)

Descrição do módulo no fonte: Explicit LRCLIB lookup using recording metadata; no page scraping.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `timed_record` | [9](../Onda/lyrics_service.py#L9) | função/método |
| `timed_record.Loader` | [22](../Onda/lyrics_service.py#L22) | classe |
| `timed_record.mapping` | [23](../Onda/lyrics_service.py#L23) | função/método |
| `best_recording` | [51](../Onda/lyrics_service.py#L51) | função/método |
| `best_recording.normalize` | [55](../Onda/lyrics_service.py#L55) | função/método |
| `best_recording.similarity` | [57](../Onda/lyrics_service.py#L57) | função/método |
| `fetch_lyrics` | [79](../Onda/lyrics_service.py#L79) | função/método |
| `fetch_lyrics.request` | [100](../Onda/lyrics_service.py#L100) | função/método |

</details>

<details>
<summary><code>matching.py</code> — 14 declarações</summary>

[Onda/matching.py](../Onda/matching.py)

Descrição do módulo no fonte: Conservative catalog-to-YouTube matching; never assumes the first hit is correct.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `words` | [6](../Onda/matching.py#L6) | função/método |
| `without_guest_credit` | [13](../Onda/matching.py#L13) | função/método |
| `NoCompatibleMatch` | [21](../Onda/matching.py#L21) | classe |
| `AmbiguousMatch` | [25](../Onda/matching.py#L25) | classe |
| `AmbiguousMatch.__init__` | [26](../Onda/matching.py#L26) | função/método |
| `revalidate_match` | [31](../Onda/matching.py#L31) | função/método |
| `matching_tokens` | [55](../Onda/matching.py#L55) | função/método |
| `version_signature` | [80](../Onda/matching.py#L80) | função/método |
| `score_candidate` | [93](../Onda/matching.py#L93) | função/método |
| `select_candidate` | [136](../Onda/matching.py#L136) | função/método |
| `find_youtube` | [197](../Onda/matching.py#L197) | função/método |
| `_find_youtube` | [216](../Onda/matching.py#L216) | função/método |
| `_find_youtube.search` | [223](../Onda/matching.py#L223) | função/método |
| `resolve_youtube` | [286](../Onda/matching.py#L286) | função/método |

</details>

<details>
<summary><code>media_links.py</code> — 6 declarações</summary>

[Onda/media_links.py](../Onda/media_links.py)

Descrição do módulo no fonte: Resolve public web media without treating search results as files.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `unwrap_google` | [8](../Onda/media_links.py#L8) | função/método |
| `MediaPage` | [23](../Onda/media_links.py#L23) | classe |
| `MediaPage.__init__` | [24](../Onda/media_links.py#L24) | função/método |
| `MediaPage.handle_starttag` | [28](../Onda/media_links.py#L28) | função/método |
| `MediaPage.handle_endtag` | [45](../Onda/media_links.py#L45) | função/método |
| `prepare_link` | [50](../Onda/media_links.py#L50) | função/método |

</details>

<details>
<summary><code>media_picker.py</code> — 10 declarações</summary>

[Onda/media_picker.py](../Onda/media_picker.py)

Descrição do módulo no fonte: Select individual photos/videos before downloading a large carousel.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MediaPicker` | [11](../Onda/media_picker.py#L11) | classe |
| `MediaPicker.__init__` | [12](../Onda/media_picker.py#L12) | função/método |
| `MediaPicker.selected` | [86](../Onda/media_picker.py#L86) | função/método |
| `MediaPicker.changed` | [89](../Onda/media_picker.py#L89) | função/método |
| `MediaPicker.select_all` | [96](../Onda/media_picker.py#L96) | função/método |
| `MediaPicker.accept` | [101](../Onda/media_picker.py#L101) | função/método |
| `MediaPicker.preview` | [108](../Onda/media_picker.py#L108) | função/método |
| `MediaPicker.preview.worker` | [117](../Onda/media_picker.py#L117) | função/método |
| `MediaPicker.poll` | [135](../Onda/media_picker.py#L135) | função/método |
| `MediaPicker.destroy` | [151](../Onda/media_picker.py#L151) | função/método |

</details>

<details>
<summary><code>media_selection.py</code> — 2 declarações</summary>

[Onda/media_selection.py](../Onda/media_selection.py)

Descrição do módulo no fonte: Validated per-video output choices shared by UI and worker.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `output_choices` | [15](../Onda/media_selection.py#L15) | função/método |
| `validate_selection` | [23](../Onda/media_selection.py#L23) | função/método |

</details>

<details>
<summary><code>metadata.py</code> — 27 declarações</summary>

[Onda/metadata.py](../Onda/metadata.py)

Descrição do módulo no fonte: Read-only catalog metadata and optional Spotify-to-public-catalog resolution.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MetadataError` | [12](../Onda/metadata.py#L12) | classe |
| `_names` | [16](../Onda/metadata.py#L16) | função/método |
| `_rows` | [21](../Onda/metadata.py#L21) | função/método |
| `is_streaming_link` | [25](../Onda/metadata.py#L25) | função/método |
| `parse_link` | [38](../Onda/metadata.py#L38) | função/método |
| `base_record` | [77](../Onda/metadata.py#L77) | função/método |
| `deezer_record` | [84](../Onda/metadata.py#L84) | função/método |
| `spotify_record` | [100](../Onda/metadata.py#L100) | função/método |
| `apple_record` | [116](../Onda/metadata.py#L116) | função/método |
| `apple_artwork` | [134](../Onda/metadata.py#L134) | função/método |
| `MetadataClient` | [143](../Onda/metadata.py#L143) | classe |
| `MetadataClient.__init__` | [144](../Onda/metadata.py#L144) | função/método |
| `MetadataClient.close` | [154](../Onda/metadata.py#L154) | função/método |
| `MetadataClient.request` | [158](../Onda/metadata.py#L158) | função/método |
| `MetadataClient.request.check` | [159](../Onda/metadata.py#L159) | função/método |
| `MetadataClient.get_json` | [205](../Onda/metadata.py#L205) | função/método |
| `MetadataClient.resolve_short_link` | [217](../Onda/metadata.py#L217) | função/método |
| `MetadataClient.spotify_token` | [234](../Onda/metadata.py#L234) | função/método |
| `MetadataClient.fetch` | [245](../Onda/metadata.py#L245) | função/método |
| `MetadataClient.resolve_deezer_link` | [277](../Onda/metadata.py#L277) | função/método |
| `MetadataClient.resolve` | [295](../Onda/metadata.py#L295) | função/método |
| `MetadataClient.complete_spotify` | [330](../Onda/metadata.py#L330) | função/método |
| `MetadataClient.confirm_catalog` | [387](../Onda/metadata.py#L387) | função/método |
| `MetadataClient.search` | [408](../Onda/metadata.py#L408) | função/método |
| `MetadataClient.search.get` | [423](../Onda/metadata.py#L423) | função/método |
| `deezer_release_date` | [464](../Onda/metadata.py#L464) | função/método |
| `display_release_date` | [478](../Onda/metadata.py#L478) | função/método |

</details>

<details>
<summary><code>metadata_badges.py</code> — 4 declarações</summary>

[Onda/metadata_badges.py](../Onda/metadata_badges.py)

Descrição do módulo no fonte: Offline monochrome metadata-provider badges; never infer from audio download URLs.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `provider` | [6](../Onda/metadata_badges.py#L6) | função/método |
| `apply_badge` | [11](../Onda/metadata_badges.py#L11) | função/método |
| `_tinted` | [30](../Onda/metadata_badges.py#L30) | função/método |
| `apply_tree_badge` | [35](../Onda/metadata_badges.py#L35) | função/método |

</details>

<details>
<summary><code>metadata_ui.py</code> — 13 declarações</summary>

[Onda/metadata_ui.py](../Onda/metadata_ui.py)

Descrição do módulo no fonte: Independent catalog window; all network work stays off the Tk thread.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MetadataWindow` | [15](../Onda/metadata_ui.py#L15) | classe |
| `MetadataWindow.__init__` | [16](../Onda/metadata_ui.py#L16) | função/método |
| `MetadataWindow.enter_fetch` | [91](../Onda/metadata_ui.py#L91) | função/método |
| `MetadataWindow.fetch` | [95](../Onda/metadata_ui.py#L95) | função/método |
| `MetadataWindow.worker` | [115](../Onda/metadata_ui.py#L115) | função/método |
| `MetadataWindow.poll` | [138](../Onda/metadata_ui.py#L138) | função/método |
| `MetadataWindow.selected_record` | [166](../Onda/metadata_ui.py#L166) | função/método |
| `MetadataWindow.select` | [171](../Onda/metadata_ui.py#L171) | função/método |
| `MetadataWindow.set_details` | [195](../Onda/metadata_ui.py#L195) | função/método |
| `MetadataWindow.open_url` | [201](../Onda/metadata_ui.py#L201) | função/método |
| `MetadataWindow.export` | [206](../Onda/metadata_ui.py#L206) | função/método |
| `MetadataWindow.cancel` | [218](../Onda/metadata_ui.py#L218) | função/método |
| `MetadataWindow.close` | [223](../Onda/metadata_ui.py#L223) | função/método |

</details>

<details>
<summary><code>music_search.py</code> — 13 declarações</summary>

[Onda/music_search.py](../Onda/music_search.py)

Descrição do módulo no fonte: Bounded catalog discovery shared by desktop and Android.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SearchCancelled` | [19](../Onda/music_search.py#L19) | classe |
| `diagnostics` | [32](../Onda/music_search.py#L32) | função/método |
| `count_selection` | [38](../Onda/music_search.py#L38) | função/método |
| `clear_cache` | [44](../Onda/music_search.py#L44) | função/método |
| `parse_query` | [49](../Onda/music_search.py#L49) | função/método |
| `parse_query.field` | [55](../Onda/music_search.py#L55) | função/método |
| `_seconds` | [79](../Onda/music_search.py#L79) | função/método |
| `accepts` | [84](../Onda/music_search.py#L84) | função/método |
| `_rank` | [129](../Onda/music_search.py#L129) | função/método |
| `search_music` | [154](../Onda/music_search.py#L154) | função/método |
| `search_music.check` | [157](../Onda/music_search.py#L157) | função/método |
| `search_music.lookup` | [178](../Onda/music_search.py#L178) | função/método |
| `search_music.collect` | [216](../Onda/music_search.py#L216) | função/método |

</details>

<details>
<summary><code>online_image_preview.py</code> — 8 declarações</summary>

[Onda/online_image_preview.py](../Onda/online_image_preview.py)

Descrição do módulo no fonte: Read-only post discovery and bounded, lazy thumbnail cache shared by both UIs.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `can_preview` | [12](../Onda/online_image_preview.py#L12) | função/método |
| `check` | [19](../Onda/online_image_preview.py#L19) | função/método |
| `candidates` | [23](../Onda/online_image_preview.py#L23) | função/método |
| `read_limited` | [83](../Onda/online_image_preview.py#L83) | função/método |
| `discard` | [92](../Onda/online_image_preview.py#L92) | função/método |
| `discover` | [101](../Onda/online_image_preview.py#L101) | função/método |
| `thumbnail` | [130](../Onda/online_image_preview.py#L130) | função/método |
| `clear_cache` | [157](../Onda/online_image_preview.py#L157) | função/método |

</details>

<details>
<summary><code>output_rules.py</code> — 5 declarações</summary>

[Onda/output_rules.py](../Onda/output_rules.py)

Descrição do módulo no fonte: Bounded filename and folder presets shared by desktop and Android downloads.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `positive_number` | [11](../Onda/output_rules.py#L11) | função/método |
| `fields` | [19](../Onda/output_rules.py#L19) | função/método |
| `folder_parts` | [33](../Onda/output_rules.py#L33) | função/método |
| `output_filename` | [46](../Onda/output_rules.py#L46) | função/método |
| `preview_path` | [65](../Onda/output_rules.py#L65) | função/método |

</details>

<details>
<summary><code>parallel_queue.py</code> — 11 declarações</summary>

[Onda/parallel_queue.py](../Onda/parallel_queue.py)

Descrição do módulo no fonte: Bounded desktop workers; modal choices are serialized on the Tk thread.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ParallelQueue` | [6](../Onda/parallel_queue.py#L6) | classe |
| `ParallelQueue.__init__` | [7](../Onda/parallel_queue.py#L7) | função/método |
| `ParallelQueue.start` | [11](../Onda/parallel_queue.py#L11) | função/método |
| `ParallelQueue.extend` | [18](../Onda/parallel_queue.py#L18) | função/método |
| `ParallelQueue.fill` | [25](../Onda/parallel_queue.py#L25) | função/método |
| `ParallelQueue.admit` | [69](../Onda/parallel_queue.py#L69) | função/método |
| `ParallelQueue.choice_closed` | [93](../Onda/parallel_queue.py#L93) | função/método |
| `ParallelQueue.finish` | [100](../Onda/parallel_queue.py#L100) | função/método |
| `ParallelQueue.stop` | [112](../Onda/parallel_queue.py#L112) | função/método |
| `ParallelQueue.stop.terminate` | [120](../Onda/parallel_queue.py#L120) | função/método |
| `ParallelQueue.reply` | [126](../Onda/parallel_queue.py#L126) | função/método |

</details>

<details>
<summary><code>performance.py</code> — 10 declarações</summary>

[Onda/performance.py](../Onda/performance.py)

Descrição do módulo no fonte: Desktop resource controls; defaults preserve existing behavior.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `cpu_threads` | [5](../Onda/performance.py#L5) | função/método |
| `thread_choices` | [8](../Onda/performance.py#L8) | função/método |
| `clean` | [15](../Onda/performance.py#L15) | função/método |
| `snapshot` | [24](../Onda/performance.py#L24) | função/método |
| `thread_args` | [27](../Onda/performance.py#L27) | função/método |
| `priority_flags` | [33](../Onda/performance.py#L33) | função/método |
| `available_memory_mb` | [38](../Onda/performance.py#L38) | função/método |
| `available_memory_mb.MemoryStatus` | [41](../Onda/performance.py#L41) | classe |
| `can_start` | [47](../Onda/performance.py#L47) | função/método |
| `controls` | [52](../Onda/performance.py#L52) | função/método |

</details>

<details>
<summary><code>photo_music.py</code> — 4 declarações</summary>

[Onda/photo_music.py](../Onda/photo_music.py)

Descrição do módulo no fonte: Render a still image with the soundtrack actually supplied by its post.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `direct_audio` | [9](../Onda/photo_music.py#L9) | função/método |
| `instagram_audio` | [22](../Onda/photo_music.py#L22) | função/método |
| `render_photo_video` | [41](../Onda/photo_music.py#L41) | função/método |
| `_render_photo_video` | [48](../Onda/photo_music.py#L48) | função/método |

</details>

<details>
<summary><code>platform_info.py</code> — 3 declarações</summary>

[Onda/platform_info.py](../Onda/platform_info.py)

Descrição do módulo no fonte: Offline platform identity for catalog, queue and history cards.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `platforms` | [8](../Onda/platform_info.py#L8) | função/método |
| `platform_info` | [11](../Onda/platform_info.py#L11) | função/método |
| `history_kind` | [27](../Onda/platform_info.py#L27) | função/método |

</details>

<details>
<summary><code>playback_controls.py</code> — 7 declarações</summary>

[Onda/playback_controls.py](../Onda/playback_controls.py)

Descrição do módulo no fonte: Playback timing and click-free gain, independent of the UI and audio device.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SleepTimer` | [5](../Onda/playback_controls.py#L5) | classe |
| `SleepTimer.__init__` | [6](../Onda/playback_controls.py#L6) | função/método |
| `SleepTimer.arm` | [7](../Onda/playback_controls.py#L7) | função/método |
| `SleepTimer.cancel` | [11](../Onda/playback_controls.py#L11) | função/método |
| `SleepTimer.remaining` | [12](../Onda/playback_controls.py#L12) | função/método |
| `SleepTimer.gain` | [13](../Onda/playback_controls.py#L13) | função/método |
| `fade_pcm` | [15](../Onda/playback_controls.py#L15) | função/método |

</details>

<details>
<summary><code>playback_input.py</code> — 2 declarações</summary>

[Onda/playback_input.py](../Onda/playback_input.py)

Descrição do módulo no fonte: Resolve the same music, direct-media and collection inputs for both players.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `collection_url` | [7](../Onda/playback_input.py#L7) | função/método |
| `resolve_input` | [22](../Onda/playback_input.py#L22) | função/método |

</details>

<details>
<summary><code>playback_session.py</code> — 2 declarações</summary>

[Onda/playback_session.py](../Onda/playback_session.py)

Descrição do módulo no fonte: Local playback snapshots; restoring never starts a decoder or audio output.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `save` | [9](../Onda/playback_session.py#L9) | função/método |
| `restore` | [22](../Onda/playback_session.py#L22) | função/método |

</details>

<details>
<summary><code>playback_ui.py</code> — 11 declarações</summary>

[Onda/playback_ui.py](../Onda/playback_ui.py)

Descrição do módulo no fonte: One stable effects tab, with independent internal workspaces and shared file input.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PlaybackPane` | [7](../Onda/playback_ui.py#L7) | classe |
| `PlaybackPane.__init__` | [8](../Onda/playback_ui.py#L8) | função/método |
| `PlaybackPane.busy` | [18](../Onda/playback_ui.py#L18) | função/método |
| `PlaybackPane.busy` | [20](../Onda/playback_ui.py#L20) | função/método |
| `PlaybackPane.switched` | [21](../Onda/playback_ui.py#L21) | função/método |
| `PlaybackPane.use_file` | [29](../Onda/playback_ui.py#L29) | função/método |
| `PlaybackPane.stop_preview` | [33](../Onda/playback_ui.py#L33) | função/método |
| `PlaybackPane.cancel` | [34](../Onda/playback_ui.py#L34) | função/método |
| `PlaybackPane.shutdown` | [35](../Onda/playback_ui.py#L35) | função/método |
| `PlaybackPane.__setattr__` | [36](../Onda/playback_ui.py#L36) | função/método |
| `PlaybackPane.__getattr__` | [41](../Onda/playback_ui.py#L41) | função/método |

</details>

<details>
<summary><code>playlist_files.py</code> — 5 declarações</summary>

[Onda/playlist_files.py](../Onda/playlist_files.py)

Descrição do módulo no fonte: Portable playlist interchange: links only, never credentials or media.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `track_url` | [11](../Onda/playlist_files.py#L11) | função/método |
| `load_csv` | [18](../Onda/playlist_files.py#L18) | função/método |
| `load_csv.field` | [30](../Onda/playlist_files.py#L30) | função/método |
| `export_text` | [59](../Onda/playlist_files.py#L59) | função/método |
| `export_local_text` | [75](../Onda/playlist_files.py#L75) | função/método |

</details>

<details>
<summary><code>playlist_import.py</code> — 4 declarações</summary>

[Onda/playlist_import.py](../Onda/playlist_import.py)

Descrição do módulo no fonte: Public playlist enumeration only; each track goes through the normal worker.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `spotify_playlist` | [14](../Onda/playlist_import.py#L14) | função/método |
| `load_playlist` | [43](../Onda/playlist_import.py#L43) | função/método |
| `_load_playlist` | [52](../Onda/playlist_import.py#L52) | função/método |
| `load_text` | [115](../Onda/playlist_import.py#L115) | função/método |

</details>

<details>
<summary><code>playlist_list_ui.py</code> — 3 declarações</summary>

[Onda/playlist_list_ui.py](../Onda/playlist_list_ui.py)

Descrição do módulo no fonte: A separate, read-only view of the loaded playlist.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PlaylistListWindow` | [9](../Onda/playlist_list_ui.py#L9) | classe |
| `PlaylistListWindow.__init__` | [10](../Onda/playlist_list_ui.py#L10) | função/método |
| `PlaylistListWindow.refresh` | [39](../Onda/playlist_list_ui.py#L39) | função/método |

</details>

<details>
<summary><code>playlist_options.py</code> — 1 declarações</summary>

[Onda/playlist_options.py](../Onda/playlist_options.py)

Descrição do módulo no fonte: Configurable bounds shared by playlist import and downloads.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `playlist_limit` | [6](../Onda/playlist_options.py#L6) | função/método |

</details>

<details>
<summary><code>playlist_sync.py</code> — 6 declarações</summary>

[Onda/playlist_sync.py](../Onda/playlist_sync.py)

Descrição do módulo no fonte: Conservative, offline collection reconciliation shared by desktop and Android.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalized` | [14](../Onda/playlist_sync.py#L14) | função/método |
| `duration` | [17](../Onda/playlist_sync.py#L17) | função/método |
| `reconcile` | [23](../Onda/playlist_sync.py#L23) | função/método |
| `compare_collection` | [69](../Onda/playlist_sync.py#L69) | função/método |
| `scan_folder` | [83](../Onda/playlist_sync.py#L83) | função/método |
| `scan_folder.fail` | [96](../Onda/playlist_sync.py#L96) | função/método |

</details>

<details>
<summary><code>playlist_sync_ui.py</code> — 7 declarações</summary>

[Onda/playlist_sync_ui.py](../Onda/playlist_sync_ui.py)

Descrição do módulo no fonte: Collection comparison controls using the existing playlist list and queue.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `controls` | [8](../Onda/playlist_sync_ui.py#L8) | função/método |
| `choose` | [17](../Onda/playlist_sync_ui.py#L17) | função/método |
| `start` | [28](../Onda/playlist_sync_ui.py#L28) | função/método |
| `start.worker` | [36](../Onda/playlist_sync_ui.py#L36) | função/método |
| `show` | [44](../Onda/playlist_sync_ui.py#L44) | função/método |
| `show_detail` | [67](../Onda/playlist_sync_ui.py#L67) | função/método |
| `add_missing` | [75](../Onda/playlist_sync_ui.py#L75) | função/método |

</details>

<details>
<summary><code>playlist_ui.py</code> — 28 declarações</summary>

[Onda/playlist_ui.py](../Onda/playlist_ui.py)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `search_text` | [15](../Onda/playlist_ui.py#L15) | função/método |
| `PlaylistPane` | [20](../Onda/playlist_ui.py#L20) | classe |
| `PlaylistPane.__init__` | [21](../Onda/playlist_ui.py#L21) | função/método |
| `PlaylistPane.sync_auto_match` | [138](../Onda/playlist_ui.py#L138) | função/método |
| `PlaylistPane.format_changed` | [143](../Onda/playlist_ui.py#L143) | função/método |
| `PlaylistPane.set_busy` | [160](../Onda/playlist_ui.py#L160) | função/método |
| `PlaylistPane.load` | [168](../Onda/playlist_ui.py#L168) | função/método |
| `PlaylistPane.load.worker` | [182](../Onda/playlist_ui.py#L182) | função/método |
| `PlaylistPane.text_file` | [196](../Onda/playlist_ui.py#L196) | função/método |
| `PlaylistPane.show_list` | [213](../Onda/playlist_ui.py#L213) | função/método |
| `PlaylistPane.connect_spotify` | [224](../Onda/playlist_ui.py#L224) | função/método |
| `PlaylistPane.export_file` | [233](../Onda/playlist_ui.py#L233) | função/método |
| `PlaylistPane.display` | [260](../Onda/playlist_ui.py#L260) | função/método |
| `PlaylistPane.display.load_cover` | [275](../Onda/playlist_ui.py#L275) | função/método |
| `PlaylistPane.display.render_batch` | [294](../Onda/playlist_ui.py#L294) | função/método |
| `PlaylistPane.schedule_filter` | [319](../Onda/playlist_ui.py#L319) | função/método |
| `PlaylistPane.filter_records` | [324](../Onda/playlist_ui.py#L324) | função/método |
| `PlaylistPane.selected_keys` | [338](../Onda/playlist_ui.py#L338) | função/método |
| `PlaylistPane.check` | [344](../Onda/playlist_ui.py#L344) | função/método |
| `PlaylistPane.check.worker` | [355](../Onda/playlist_ui.py#L355) | função/método |
| `PlaylistPane.check.worker.Quiet` | [358](../Onda/playlist_ui.py#L358) | classe |
| `PlaylistPane.check.worker.Quiet.debug` | [359](../Onda/playlist_ui.py#L359) | função/método |
| `PlaylistPane.check.worker.Quiet.warning` | [360](../Onda/playlist_ui.py#L360) | função/método |
| `PlaylistPane.check.worker.Quiet.error` | [361](../Onda/playlist_ui.py#L361) | função/método |
| `PlaylistPane.check.worker.need_choice` | [378](../Onda/playlist_ui.py#L378) | função/método |
| `PlaylistPane.add` | [395](../Onda/playlist_ui.py#L395) | função/método |
| `PlaylistPane.poll` | [438](../Onda/playlist_ui.py#L438) | função/método |
| `PlaylistPane.shutdown` | [468](../Onda/playlist_ui.py#L468) | função/método |

</details>

<details>
<summary><code>preferences.py</code> — 11 declarações</summary>

[Onda/preferences.py](../Onda/preferences.py)

Descrição do módulo no fonte: Non-secret, opt-in preferences. Only explicit UI fields are persisted.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PreferenceStore` | [10](../Onda/preferences.py#L10) | classe |
| `PreferenceStore.__init__` | [11](../Onda/preferences.py#L11) | função/método |
| `PreferenceStore.remember_enabled` | [15](../Onda/preferences.py#L15) | função/método |
| `PreferenceStore.load_language` | [23](../Onda/preferences.py#L23) | função/método |
| `PreferenceStore.save_language` | [30](../Onda/preferences.py#L30) | função/método |
| `PreferenceStore.load_display` | [43](../Onda/preferences.py#L43) | função/método |
| `PreferenceStore.save_display` | [50](../Onda/preferences.py#L50) | função/método |
| `PreferenceStore.clean` | [62](../Onda/preferences.py#L62) | função/método |
| `PreferenceStore.load` | [189](../Onda/preferences.py#L189) | função/método |
| `PreferenceStore.save` | [202](../Onda/preferences.py#L202) | função/método |
| `PreferenceStore.forget` | [217](../Onda/preferences.py#L217) | função/método |

</details>

<details>
<summary><code>preview_options.py</code> — 1 declarações</summary>

[Onda/preview_options.py](../Onda/preview_options.py)

Descrição do módulo no fonte: Shared choices for playback limits, measured in output seconds.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `preview_seconds` | [5](../Onda/preview_options.py#L5) | função/método |

</details>

<details>
<summary><code>qt_desktop_ui.py</code> — 5 declarações</summary>

[Onda/qt_desktop_ui.py](../Onda/qt_desktop_ui.py)

Descrição do módulo no fonte: Qt desktop shell, native workspaces and the QML Jukebox.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `create_application` | [15](../Onda/qt_desktop_ui.py#L15) | função/método |
| `create_application.refresh_icon` | [41](../Onda/qt_desktop_ui.py#L41) | função/método |
| `close_application` | [60](../Onda/qt_desktop_ui.py#L60) | função/método |
| `packaged_self_test` | [68](../Onda/qt_desktop_ui.py#L68) | função/método |
| `main` | [93](../Onda/qt_desktop_ui.py#L93) | função/método |

</details>

<details>
<summary><code>qt_graph_ui.py</code> — 11 declarações</summary>

[Onda/qt_graph_ui.py](../Onda/qt_graph_ui.py)

Descrição do módulo no fonte: Cached graph layer: phase/marker animation is rendered separately by Qt Quick.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `BeatGraph` | [7](../Onda/qt_graph_ui.py#L7) | classe |
| `BeatGraph.__init__` | [9](../Onda/qt_graph_ui.py#L9) | função/método |
| `BeatGraph.graphData` | [14](../Onda/qt_graph_ui.py#L14) | função/método |
| `BeatGraph.graphData` | [16](../Onda/qt_graph_ui.py#L16) | função/método |
| `BeatGraph.accent` | [19](../Onda/qt_graph_ui.py#L19) | função/método |
| `BeatGraph.accent` | [21](../Onda/qt_graph_ui.py#L21) | função/método |
| `BeatGraph.muted` | [24](../Onda/qt_graph_ui.py#L24) | função/método |
| `BeatGraph.muted` | [26](../Onda/qt_graph_ui.py#L26) | função/método |
| `BeatGraph.paint` | [28](../Onda/qt_graph_ui.py#L28) | função/método |
| `BeatGraph.paint.point` | [31](../Onda/qt_graph_ui.py#L31) | função/método |
| `BeatGraph.paint.curve` | [33](../Onda/qt_graph_ui.py#L33) | função/método |

</details>

<details>
<summary><code>qt_jukebox_ui.py</code> — 90 declarações</summary>

[Onda/qt_jukebox_ui.py](../Onda/qt_jukebox_ui.py)

Descrição do módulo no fonte: Qt adapter for the existing Jukebox engine; workers never touch QML objects.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxBridge` | [22](../Onda/qt_jukebox_ui.py#L22) | classe |
| `JukeboxBridge.__init__` | [32](../Onda/qt_jukebox_ui.py#L32) | função/método |
| `JukeboxBridge.state` | [54](../Onda/qt_jukebox_ui.py#L54) | função/método |
| `JukeboxBridge.queuedTracks` | [59](../Onda/qt_jukebox_ui.py#L59) | função/método |
| `JukeboxBridge.playback` | [61](../Onda/qt_jukebox_ui.py#L61) | função/método |
| `JukeboxBridge.setSleep` | [64](../Onda/qt_jukebox_ui.py#L64) | função/método |
| `JukeboxBridge.refresh_clock` | [68](../Onda/qt_jukebox_ui.py#L68) | função/método |
| `JukeboxBridge.tick_sleep` | [71](../Onda/qt_jukebox_ui.py#L71) | função/método |
| `JukeboxBridge.setTrackMinutes` | [79](../Onda/qt_jukebox_ui.py#L79) | função/método |
| `JukeboxBridge.setGradualTransition` | [82](../Onda/qt_jukebox_ui.py#L82) | função/método |
| `JukeboxBridge.playback_gain` | [84](../Onda/qt_jukebox_ui.py#L84) | função/método |
| `JukeboxBridge.transitionSeconds` | [88](../Onda/qt_jukebox_ui.py#L88) | função/método |
| `JukeboxBridge.setTransitionSeconds` | [90](../Onda/qt_jukebox_ui.py#L90) | função/método |
| `JukeboxBridge.queue_info` | [92](../Onda/qt_jukebox_ui.py#L92) | função/método |
| `JukeboxBridge.enqueueFiles` | [96](../Onda/qt_jukebox_ui.py#L96) | função/método |
| `JukeboxBridge.prepare_local` | [107](../Onda/qt_jukebox_ui.py#L107) | função/método |
| `JukeboxBridge.fetch_record` | [115](../Onda/qt_jukebox_ui.py#L115) | função/método |
| `JukeboxBridge.prepare_next_queued` | [122](../Onda/qt_jukebox_ui.py#L122) | função/método |
| `JukeboxBridge.prepare_next_queued.worker` | [129](../Onda/qt_jukebox_ui.py#L129) | função/método |
| `JukeboxBridge.retryQueued` | [136](../Onda/qt_jukebox_ui.py#L136) | função/método |
| `JukeboxBridge.enqueueRecord` | [138](../Onda/qt_jukebox_ui.py#L138) | função/método |
| `JukeboxBridge.enqueueResult` | [142](../Onda/qt_jukebox_ui.py#L142) | função/método |
| `JukeboxBridge.removeQueued` | [145](../Onda/qt_jukebox_ui.py#L145) | função/método |
| `JukeboxBridge.moveQueued` | [155](../Onda/qt_jukebox_ui.py#L155) | função/método |
| `JukeboxBridge.clearPlaybackQueue` | [161](../Onda/qt_jukebox_ui.py#L161) | função/método |
| `JukeboxBridge.playQueued` | [166](../Onda/qt_jukebox_ui.py#L166) | função/método |
| `JukeboxBridge.activate_queued` | [182](../Onda/qt_jukebox_ui.py#L182) | função/método |
| `JukeboxBridge.previousTrack` | [186](../Onda/qt_jukebox_ui.py#L186) | função/método |
| `JukeboxBridge.queueRepeat` | [190](../Onda/qt_jukebox_ui.py#L190) | função/método |
| `JukeboxBridge.queueShuffle` | [192](../Onda/qt_jukebox_ui.py#L192) | função/método |
| `JukeboxBridge.setQueueRepeat` | [194](../Onda/qt_jukebox_ui.py#L194) | função/método |
| `JukeboxBridge.setQueueShuffle` | [197](../Onda/qt_jukebox_ui.py#L197) | função/método |
| `JukeboxBridge.nextTrack` | [199](../Onda/qt_jukebox_ui.py#L199) | função/método |
| `JukeboxBridge.position` | [214](../Onda/qt_jukebox_ui.py#L214) | função/método |
| `JukeboxBridge.phase` | [216](../Onda/qt_jukebox_ui.py#L216) | função/método |
| `JukeboxBridge.elapsed` | [218](../Onda/qt_jukebox_ui.py#L218) | função/método |
| `JukeboxBridge.jumps` | [221](../Onda/qt_jukebox_ui.py#L221) | função/método |
| `JukeboxBridge.graph` | [223](../Onda/qt_jukebox_ui.py#L223) | função/método |
| `JukeboxBridge.cursor` | [241](../Onda/qt_jukebox_ui.py#L241) | função/método |
| `JukeboxBridge.cursor.point` | [243](../Onda/qt_jukebox_ui.py#L243) | função/método |
| `JukeboxBridge.brandPath` | [251](../Onda/qt_jukebox_ui.py#L251) | função/método |
| `JukeboxBridge.palette` | [256](../Onda/qt_jukebox_ui.py#L256) | função/método |
| `JukeboxBridge.animations` | [260](../Onda/qt_jukebox_ui.py#L260) | função/método |
| `JukeboxBridge.fontScale` | [262](../Onda/qt_jukebox_ui.py#L262) | função/método |
| `JukeboxBridge.spacing` | [266](../Onda/qt_jukebox_ui.py#L266) | função/método |
| `JukeboxBridge.themes` | [268](../Onda/qt_jukebox_ui.py#L268) | função/método |
| `JukeboxBridge.accents` | [270](../Onda/qt_jukebox_ui.py#L270) | função/método |
| `JukeboxBridge.theme` | [274](../Onda/qt_jukebox_ui.py#L274) | função/método |
| `JukeboxBridge.accent` | [276](../Onda/qt_jukebox_ui.py#L276) | função/método |
| `JukeboxBridge.equalizer` | [278](../Onda/qt_jukebox_ui.py#L278) | função/método |
| `JukeboxBridge.presetNames` | [280](../Onda/qt_jukebox_ui.py#L280) | função/método |
| `JukeboxBridge.presetName` | [282](../Onda/qt_jukebox_ui.py#L282) | função/método |
| `JukeboxBridge.update_graph` | [284](../Onda/qt_jukebox_ui.py#L284) | função/método |
| `JukeboxBridge.translate` | [288](../Onda/qt_jukebox_ui.py#L288) | função/método |
| `JukeboxBridge.translateError` | [290](../Onda/qt_jukebox_ui.py#L290) | função/método |
| `JukeboxBridge.refreshSearchResults` | [291](../Onda/qt_jukebox_ui.py#L291) | função/método |
| `JukeboxBridge.update_state` | [294](../Onda/qt_jukebox_ui.py#L294) | função/método |
| `JukeboxBridge.persist` | [297](../Onda/qt_jukebox_ui.py#L297) | função/método |
| `JukeboxBridge.save_preferences` | [300](../Onda/qt_jukebox_ui.py#L300) | função/método |
| `JukeboxBridge.setAppearance` | [308](../Onda/qt_jukebox_ui.py#L308) | função/método |
| `JukeboxBridge.setParams` | [312](../Onda/qt_jukebox_ui.py#L312) | função/método |
| `JukeboxBridge.applyPreset` | [318](../Onda/qt_jukebox_ui.py#L318) | função/método |
| `JukeboxBridge.set_equalizer` | [320](../Onda/qt_jukebox_ui.py#L320) | função/método |
| `JukeboxBridge.enableEqualizer` | [323](../Onda/qt_jukebox_ui.py#L323) | função/método |
| `JukeboxBridge.setPreamp` | [325](../Onda/qt_jukebox_ui.py#L325) | função/método |
| `JukeboxBridge.setBand` | [327](../Onda/qt_jukebox_ui.py#L327) | função/método |
| `JukeboxBridge.resetEqualizer` | [331](../Onda/qt_jukebox_ui.py#L331) | função/método |
| `JukeboxBridge.config` | [333](../Onda/qt_jukebox_ui.py#L333) | função/método |
| `JukeboxBridge.emit` | [340](../Onda/qt_jukebox_ui.py#L340) | função/método |
| `JukeboxBridge.task` | [342](../Onda/qt_jukebox_ui.py#L342) | função/método |
| `JukeboxBridge.task.post` | [347](../Onda/qt_jukebox_ui.py#L347) | função/método |
| `JukeboxBridge.task.worker` | [350](../Onda/qt_jukebox_ui.py#L350) | função/método |
| `JukeboxBridge.start_worker` | [356](../Onda/qt_jukebox_ui.py#L356) | função/método |
| `JukeboxBridge.openFile` | [360](../Onda/qt_jukebox_ui.py#L360) | função/método |
| `JukeboxBridge.search` | [366](../Onda/qt_jukebox_ui.py#L366) | função/método |
| `JukeboxBridge.search.search` | [371](../Onda/qt_jukebox_ui.py#L371) | função/método |
| `JukeboxBridge.selectResult` | [380](../Onda/qt_jukebox_ui.py#L380) | função/método |
| `JukeboxBridge.prepare_record` | [383](../Onda/qt_jukebox_ui.py#L383) | função/método |
| `JukeboxBridge.handle_event` | [389](../Onda/qt_jukebox_ui.py#L389) | função/método |
| `JukeboxBridge.playPause` | [461](../Onda/qt_jukebox_ui.py#L461) | função/método |
| `JukeboxBridge.playPause.worker` | [472](../Onda/qt_jukebox_ui.py#L472) | função/método |
| `JukeboxBridge.playPause.worker.progress` | [477](../Onda/qt_jukebox_ui.py#L477) | função/método |
| `JukeboxBridge.playPause.worker.progress.announce` | [480](../Onda/qt_jukebox_ui.py#L480) | função/método |
| `JukeboxBridge.closeSearch` | [515](../Onda/qt_jukebox_ui.py#L515) | função/método |
| `JukeboxBridge.cancelOperation` | [520](../Onda/qt_jukebox_ui.py#L520) | função/método |
| `JukeboxBridge.stop` | [525](../Onda/qt_jukebox_ui.py#L525) | função/método |
| `JukeboxBridge.seek` | [533](../Onda/qt_jukebox_ui.py#L533) | função/método |
| `JukeboxBridge.media_state` | [536](../Onda/qt_jukebox_ui.py#L536) | função/método |
| `JukeboxBridge.sync_media` | [539](../Onda/qt_jukebox_ui.py#L539) | função/método |
| `JukeboxBridge.shutdown` | [563](../Onda/qt_jukebox_ui.py#L563) | função/método |

</details>

<details>
<summary><code>qt_models_ui.py</code> — 9 declarações</summary>

[Onda/qt_models_ui.py](../Onda/qt_models_ui.py)

Descrição do módulo no fonte: Qt list models with row updates instead of rebuilding long queues.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `RowsModel` | [3](../Onda/qt_models_ui.py#L3) | classe |
| `RowsModel.__init__` | [5](../Onda/qt_models_ui.py#L5) | função/método |
| `RowsModel.roleNames` | [6](../Onda/qt_models_ui.py#L6) | função/método |
| `RowsModel.rowCount` | [7](../Onda/qt_models_ui.py#L7) | função/método |
| `RowsModel.data` | [8](../Onda/qt_models_ui.py#L8) | função/método |
| `RowsModel.count` | [11](../Onda/qt_models_ui.py#L11) | função/método |
| `RowsModel.get` | [13](../Onda/qt_models_ui.py#L13) | função/método |
| `RowsModel.replace` | [14](../Onda/qt_models_ui.py#L14) | função/método |
| `RowsModel.update` | [26](../Onda/qt_models_ui.py#L26) | função/método |

</details>

<details>
<summary><code>qt_operations_ui.py</code> — 4 declarações</summary>

[Onda/qt_operations_ui.py](../Onda/qt_operations_ui.py)

Descrição do módulo no fonte: Headless operations reused by Qt. No widgets or GUI event loops.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `client` | [5](../Onda/qt_operations_ui.py#L5) | função/método |
| `image_details` | [12](../Onda/qt_operations_ui.py#L12) | função/método |
| `perform` | [21](../Onda/qt_operations_ui.py#L21) | função/método |
| `perform.capture` | [189](../Onda/qt_operations_ui.py#L189) | função/método |

</details>

<details>
<summary><code>qt_platform_icons_ui.py</code> — 3 declarações</summary>

[Onda/qt_platform_icons_ui.py](../Onda/qt_platform_icons_ui.py)

Descrição do módulo no fonte: Platform silhouettes tinted for the current desktop theme.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PlatformIcons` | [5](../Onda/qt_platform_icons_ui.py#L5) | classe |
| `PlatformIcons.__init__` | [6](../Onda/qt_platform_icons_ui.py#L6) | função/método |
| `PlatformIcons.requestImage` | [7](../Onda/qt_platform_icons_ui.py#L7) | função/método |

</details>

<details>
<summary><code>qt_workspace_ui.py</code> — 164 declarações</summary>

[Onda/qt_workspace_ui.py](../Onda/qt_workspace_ui.py)

Descrição do módulo no fonte: Native Qt controller; shared media engines execute off the UI thread.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DesktopWorkspace` | [15](../Onda/qt_workspace_ui.py#L15) | classe |
| `DesktopWorkspace.__init__` | [18](../Onda/qt_workspace_ui.py#L18) | função/método |
| `DesktopWorkspace.save_playback_session` | [65](../Onda/qt_workspace_ui.py#L65) | função/método |
| `DesktopWorkspace.currentPage` | [69](../Onda/qt_workspace_ui.py#L69) | função/método |
| `DesktopWorkspace.title` | [71](../Onda/qt_workspace_ui.py#L71) | função/método |
| `DesktopWorkspace.ready` | [73](../Onda/qt_workspace_ui.py#L73) | função/método |
| `DesktopWorkspace.error` | [75](../Onda/qt_workspace_ui.py#L75) | função/método |
| `DesktopWorkspace.status` | [77](../Onda/qt_workspace_ui.py#L77) | função/método |
| `DesktopWorkspace.values` | [79](../Onda/qt_workspace_ui.py#L79) | função/método |
| `DesktopWorkspace.preferences` | [81](../Onda/qt_workspace_ui.py#L81) | função/método |
| `DesktopWorkspace.settingsFields` | [83](../Onda/qt_workspace_ui.py#L83) | função/método |
| `DesktopWorkspace.settingsSearchMatches` | [85](../Onda/qt_workspace_ui.py#L85) | função/método |
| `DesktopWorkspace.hiddenTabs` | [89](../Onda/qt_workspace_ui.py#L89) | função/método |
| `DesktopWorkspace.choice` | [91](../Onda/qt_workspace_ui.py#L91) | função/método |
| `DesktopWorkspace.activity` | [93](../Onda/qt_workspace_ui.py#L93) | função/método |
| `DesktopWorkspace.queueModel` | [95](../Onda/qt_workspace_ui.py#L95) | função/método |
| `DesktopWorkspace.linksModel` | [97](../Onda/qt_workspace_ui.py#L97) | função/método |
| `DesktopWorkspace.catalogModel` | [99](../Onda/qt_workspace_ui.py#L99) | função/método |
| `DesktopWorkspace.playlistModel` | [101](../Onda/qt_workspace_ui.py#L101) | função/método |
| `DesktopWorkspace.historyModel` | [103](../Onda/qt_workspace_ui.py#L103) | função/método |
| `DesktopWorkspace.attach` | [104](../Onda/qt_workspace_ui.py#L104) | função/método |
| `DesktopWorkspace.restore_window_layout` | [115](../Onda/qt_workspace_ui.py#L115) | função/método |
| `DesktopWorkspace.capture_window_layout` | [127](../Onda/qt_workspace_ui.py#L127) | função/método |
| `DesktopWorkspace.save_window_layout` | [132](../Onda/qt_workspace_ui.py#L132) | função/método |
| `DesktopWorkspace.remember_window_state` | [142](../Onda/qt_workspace_ui.py#L142) | função/método |
| `DesktopWorkspace.remember_window_state.settled` | [147](../Onda/qt_workspace_ui.py#L147) | função/método |
| `DesktopWorkspace.start` | [153](../Onda/qt_workspace_ui.py#L153) | função/método |
| `DesktopWorkspace.update_available` | [163](../Onda/qt_workspace_ui.py#L163) | função/método |
| `DesktopWorkspace.clean_idle_temporaries` | [166](../Onda/qt_workspace_ui.py#L166) | função/método |
| `DesktopWorkspace.config` | [171](../Onda/qt_workspace_ui.py#L171) | função/método |
| `DesktopWorkspace.canPreviewImages` | [177](../Onda/qt_workspace_ui.py#L177) | função/método |
| `DesktopWorkspace.image_options` | [181](../Onda/qt_workspace_ui.py#L181) | função/método |
| `DesktopWorkspace.notify` | [185](../Onda/qt_workspace_ui.py#L185) | função/método |
| `DesktopWorkspace.log` | [186](../Onda/qt_workspace_ui.py#L186) | função/método |
| `DesktopWorkspace.setOption` | [188](../Onda/qt_workspace_ui.py#L188) | função/método |
| `DesktopWorkspace.setSetting` | [199](../Onda/qt_workspace_ui.py#L199) | função/método |
| `DesktopWorkspace.from_bridge` | [227](../Onda/qt_workspace_ui.py#L227) | função/método |
| `DesktopWorkspace.persist` | [232](../Onda/qt_workspace_ui.py#L232) | função/método |
| `DesktopWorkspace.pause_background_jukebox` | [245](../Onda/qt_workspace_ui.py#L245) | função/método |
| `DesktopWorkspace.selectNavigationPage` | [249](../Onda/qt_workspace_ui.py#L249) | função/método |
| `DesktopWorkspace.selectPage` | [253](../Onda/qt_workspace_ui.py#L253) | função/método |
| `DesktopWorkspace.showSettings` | [261](../Onda/qt_workspace_ui.py#L261) | função/método |
| `DesktopWorkspace.showShortcuts` | [263](../Onda/qt_workspace_ui.py#L263) | função/método |
| `DesktopWorkspace.showMetadata` | [265](../Onda/qt_workspace_ui.py#L265) | função/método |
| `DesktopWorkspace.run_task` | [266](../Onda/qt_workspace_ui.py#L266) | função/método |
| `DesktopWorkspace.run_task.work` | [276](../Onda/qt_workspace_ui.py#L276) | função/método |
| `DesktopWorkspace.launch_thread` | [287](../Onda/qt_workspace_ui.py#L287) | função/método |
| `DesktopWorkspace.cancel_task` | [289](../Onda/qt_workspace_ui.py#L289) | função/método |
| `DesktopWorkspace.invoke` | [306](../Onda/qt_workspace_ui.py#L306) | função/método |
| `DesktopWorkspace.dispatch` | [313](../Onda/qt_workspace_ui.py#L313) | função/método |
| `DesktopWorkspace.dispatch.loaded` | [320](../Onda/qt_workspace_ui.py#L320) | função/método |
| `DesktopWorkspace.dispatch.fetched` | [324](../Onda/qt_workspace_ui.py#L324) | função/método |
| `DesktopWorkspace.dispatch.loaded` | [347](../Onda/qt_workspace_ui.py#L347) | função/método |
| `DesktopWorkspace.dispatch.loaded` | [362](../Onda/qt_workspace_ui.py#L362) | função/método |
| `DesktopWorkspace.dispatch.loaded` | [374](../Onda/qt_workspace_ui.py#L374) | função/método |
| `DesktopWorkspace.dispatch.enqueued` | [386](../Onda/qt_workspace_ui.py#L386) | função/método |
| `DesktopWorkspace.dispatch.loaded` | [419](../Onda/qt_workspace_ui.py#L419) | função/método |
| `DesktopWorkspace.dispatch.loaded` | [430](../Onda/qt_workspace_ui.py#L430) | função/método |
| `DesktopWorkspace.dispatch.loaded.selected` | [435](../Onda/qt_workspace_ui.py#L435) | função/método |
| `DesktopWorkspace.dispatch.completed` | [666](../Onda/qt_workspace_ui.py#L666) | função/método |
| `DesktopWorkspace.taskLabel` | [675](../Onda/qt_workspace_ui.py#L675) | função/método |
| `DesktopWorkspace.queueActionEnabled` | [680](../Onda/qt_workspace_ui.py#L680) | função/método |
| `DesktopWorkspace.preparationAdvice` | [684](../Onda/qt_workspace_ui.py#L684) | função/método |
| `DesktopWorkspace.workflowLabel` | [688](../Onda/qt_workspace_ui.py#L688) | função/método |
| `DesktopWorkspace.pageLabel` | [692](../Onda/qt_workspace_ui.py#L692) | função/método |
| `DesktopWorkspace.shortcutFields` | [694](../Onda/qt_workspace_ui.py#L694) | função/método |
| `DesktopWorkspace.searched` | [699](../Onda/qt_workspace_ui.py#L699) | função/método |
| `DesktopWorkspace.filter_catalog` | [701](../Onda/qt_workspace_ui.py#L701) | função/método |
| `DesktopWorkspace.record_name` | [707](../Onda/qt_workspace_ui.py#L707) | função/método |
| `DesktopWorkspace.collection_loaded` | [708](../Onda/qt_workspace_ui.py#L708) | função/método |
| `DesktopWorkspace.effects_input_loaded` | [711](../Onda/qt_workspace_ui.py#L711) | função/método |
| `DesktopWorkspace.effects_input_loaded.loaded` | [714](../Onda/qt_workspace_ui.py#L714) | função/método |
| `DesktopWorkspace.flush_card_details` | [719](../Onda/qt_workspace_ui.py#L719) | função/método |
| `DesktopWorkspace.flush_card_details.loaded` | [723](../Onda/qt_workspace_ui.py#L723) | função/método |
| `DesktopWorkspace.collection_compared` | [740](../Onda/qt_workspace_ui.py#L740) | função/método |
| `DesktopWorkspace.refresh_history` | [751](../Onda/qt_workspace_ui.py#L751) | função/método |
| `DesktopWorkspace.history_details_loaded` | [767](../Onda/qt_workspace_ui.py#L767) | função/método |
| `DesktopWorkspace.expire_history_undo` | [772](../Onda/qt_workspace_ui.py#L772) | função/método |
| `DesktopWorkspace.online_gallery_loaded` | [774](../Onda/qt_workspace_ui.py#L774) | função/método |
| `DesktopWorkspace.load_online_gallery_image` | [776](../Onda/qt_workspace_ui.py#L776) | função/método |
| `DesktopWorkspace.load_online_gallery_image.loaded` | [782](../Onda/qt_workspace_ui.py#L782) | função/método |
| `DesktopWorkspace.local_gallery` | [789](../Onda/qt_workspace_ui.py#L789) | função/método |
| `DesktopWorkspace.open_image_gallery` | [792](../Onda/qt_workspace_ui.py#L792) | função/método |
| `DesktopWorkspace.clear_history` | [795](../Onda/qt_workspace_ui.py#L795) | função/método |
| `DesktopWorkspace.toggle_row` | [796](../Onda/qt_workspace_ui.py#L796) | função/método |
| `DesktopWorkspace.refresh_queue` | [802](../Onda/qt_workspace_ui.py#L802) | função/método |
| `DesktopWorkspace.refresh_queue_summary` | [806](../Onda/qt_workspace_ui.py#L806) | função/método |
| `DesktopWorkspace.download_images` | [810](../Onda/qt_workspace_ui.py#L810) | função/método |
| `DesktopWorkspace.queue_record` | [821](../Onda/qt_workspace_ui.py#L821) | função/método |
| `DesktopWorkspace.save_queue` | [830](../Onda/qt_workspace_ui.py#L830) | função/método |
| `DesktopWorkspace.enqueue_tracks` | [831](../Onda/qt_workspace_ui.py#L831) | função/método |
| `DesktopWorkspace.enqueue` | [837](../Onda/qt_workspace_ui.py#L837) | função/método |
| `DesktopWorkspace.add_duplicate` | [866](../Onda/qt_workspace_ui.py#L866) | função/método |
| `DesktopWorkspace.start_queue` | [870](../Onda/qt_workspace_ui.py#L870) | função/método |
| `DesktopWorkspace.begin_queue` | [877](../Onda/qt_workspace_ui.py#L877) | função/método |
| `DesktopWorkspace.in_queue_scope` | [886](../Onda/qt_workspace_ui.py#L886) | função/método |
| `DesktopWorkspace.fill_queue` | [887](../Onda/qt_workspace_ui.py#L887) | função/método |
| `DesktopWorkspace.process_worker` | [918](../Onda/qt_workspace_ui.py#L918) | função/método |
| `DesktopWorkspace.stop_queue` | [950](../Onda/qt_workspace_ui.py#L950) | função/método |
| `DesktopWorkspace.stop_job` | [954](../Onda/qt_workspace_ui.py#L954) | função/método |
| `DesktopWorkspace.queue_action` | [961](../Onda/qt_workspace_ui.py#L961) | função/método |
| `DesktopWorkspace.replyChoice` | [1006](../Onda/qt_workspace_ui.py#L1006) | função/método |
| `DesktopWorkspace.present_choice` | [1017](../Onda/qt_workspace_ui.py#L1017) | função/método |
| `DesktopWorkspace.next_choice` | [1023](../Onda/qt_workspace_ui.py#L1023) | função/método |
| `DesktopWorkspace.confirm` | [1025](../Onda/qt_workspace_ui.py#L1025) | função/método |
| `DesktopWorkspace.on_event` | [1028](../Onda/qt_workspace_ui.py#L1028) | função/método |
| `DesktopWorkspace.show_result` | [1109](../Onda/qt_workspace_ui.py#L1109) | função/método |
| `DesktopWorkspace.pick` | [1124](../Onda/qt_workspace_ui.py#L1124) | função/método |
| `DesktopWorkspace.accept_files` | [1137](../Onda/qt_workspace_ui.py#L1137) | função/método |
| `DesktopWorkspace.accept_files.loaded` | [1143](../Onda/qt_workspace_ui.py#L1143) | função/método |
| `DesktopWorkspace.convert` | [1174](../Onda/qt_workspace_ui.py#L1174) | função/método |
| `DesktopWorkspace.convert_to` | [1182](../Onda/qt_workspace_ui.py#L1182) | função/método |
| `DesktopWorkspace.effects_loaded` | [1186](../Onda/qt_workspace_ui.py#L1186) | função/método |
| `DesktopWorkspace.audio_loaded` | [1192](../Onda/qt_workspace_ui.py#L1192) | função/método |
| `DesktopWorkspace.image_result` | [1195](../Onda/qt_workspace_ui.py#L1195) | função/método |
| `DesktopWorkspace.edit_audio` | [1199](../Onda/qt_workspace_ui.py#L1199) | função/método |
| `DesktopWorkspace.export_effects` | [1208](../Onda/qt_workspace_ui.py#L1208) | função/método |
| `DesktopWorkspace.settings_file_action` | [1218](../Onda/qt_workspace_ui.py#L1218) | função/método |
| `DesktopWorkspace.reset_settings` | [1242](../Onda/qt_workspace_ui.py#L1242) | função/método |
| `DesktopWorkspace.queue_finished` | [1244](../Onda/qt_workspace_ui.py#L1244) | função/método |
| `DesktopWorkspace.shutdown_countdown` | [1251](../Onda/qt_workspace_ui.py#L1251) | função/método |
| `DesktopWorkspace.perform_shutdown` | [1253](../Onda/qt_workspace_ui.py#L1253) | função/método |
| `DesktopWorkspace.clipboard_changed` | [1255](../Onda/qt_workspace_ui.py#L1255) | função/método |
| `DesktopWorkspace.tick` | [1261](../Onda/qt_workspace_ui.py#L1261) | função/método |
| `DesktopWorkspace.setup_shell` | [1311](../Onda/qt_workspace_ui.py#L1311) | função/método |
| `DesktopWorkspace.tray_activated` | [1320](../Onda/qt_workspace_ui.py#L1320) | função/método |
| `DesktopWorkspace.suspendShortcuts` | [1325](../Onda/qt_workspace_ui.py#L1325) | função/método |
| `DesktopWorkspace.captureShortcut` | [1330](../Onda/qt_workspace_ui.py#L1330) | função/método |
| `DesktopWorkspace.bind_shortcuts` | [1345](../Onda/qt_workspace_ui.py#L1345) | função/método |
| `DesktopWorkspace.shortcut` | [1352](../Onda/qt_workspace_ui.py#L1352) | função/método |
| `DesktopWorkspace.restore` | [1371](../Onda/qt_workspace_ui.py#L1371) | função/método |
| `DesktopWorkspace.requestClose` | [1383](../Onda/qt_workspace_ui.py#L1383) | função/método |
| `DesktopWorkspace.shutdown` | [1390](../Onda/qt_workspace_ui.py#L1390) | função/método |
| `DesktopWorkspace.music_overrides` | [1405](../Onda/qt_workspace_ui.py#L1405) | função/método |
| `DesktopWorkspace.choose_download_format` | [1410](../Onda/qt_workspace_ui.py#L1410) | função/método |
| `DesktopWorkspace.choose_download_format.chosen` | [1416](../Onda/qt_workspace_ui.py#L1416) | função/método |
| `DesktopWorkspace.update_playlist` | [1428](../Onda/qt_workspace_ui.py#L1428) | função/método |
| `DesktopWorkspace.update_playlist.loaded` | [1429](../Onda/qt_workspace_ui.py#L1429) | função/método |
| `DesktopWorkspace.update_playlist.loaded.compared` | [1431](../Onda/qt_workspace_ui.py#L1431) | função/método |
| `DesktopWorkspace.setMiniPlayerActive` | [1437](../Onda/qt_workspace_ui.py#L1437) | função/método |
| `DesktopWorkspace.openMiniPlayer` | [1439](../Onda/qt_workspace_ui.py#L1439) | função/método |
| `DesktopWorkspace.pinPlayer` | [1445](../Onda/qt_workspace_ui.py#L1445) | função/método |
| `DesktopWorkspace.openLyrics` | [1457](../Onda/qt_workspace_ui.py#L1457) | função/método |
| `DesktopWorkspace.lyricsFrame` | [1460](../Onda/qt_workspace_ui.py#L1460) | função/método |
| `DesktopWorkspace.seekLyrics` | [1483](../Onda/qt_workspace_ui.py#L1483) | função/método |
| `DesktopWorkspace.load_lyrics` | [1489](../Onda/qt_workspace_ui.py#L1489) | função/método |
| `DesktopWorkspace.effects_media_state` | [1503](../Onda/qt_workspace_ui.py#L1503) | função/método |
| `DesktopWorkspace.media_command` | [1511](../Onda/qt_workspace_ui.py#L1511) | função/método |
| `DesktopWorkspace.pause_effects_for_jukebox` | [1521](../Onda/qt_workspace_ui.py#L1521) | função/método |
| `DesktopWorkspace.start_preview` | [1529](../Onda/qt_workspace_ui.py#L1529) | função/método |
| `DesktopWorkspace.stop_preview` | [1535](../Onda/qt_workspace_ui.py#L1535) | função/método |
| `DesktopWorkspace.effects_transition_seconds` | [1540](../Onda/qt_workspace_ui.py#L1540) | função/método |
| `DesktopWorkspace.advance_effects` | [1542](../Onda/qt_workspace_ui.py#L1542) | função/método |
| `DesktopWorkspace.play_effects_entry` | [1555](../Onda/qt_workspace_ui.py#L1555) | função/método |
| `DesktopWorkspace.play_effects_preview` | [1575](../Onda/qt_workspace_ui.py#L1575) | função/método |
| `DesktopWorkspace.receiveDrop` | [1583](../Onda/qt_workspace_ui.py#L1583) | função/método |
| `DesktopWorkspace.decorate_record` | [1593](../Onda/qt_workspace_ui.py#L1593) | função/método |
| `DesktopWorkspace.catalogChoices` | [1600](../Onda/qt_workspace_ui.py#L1600) | função/método |
| `DesktopWorkspace.compareText` | [1602](../Onda/qt_workspace_ui.py#L1602) | função/método |
| `DesktopWorkspace.cover_cropped` | [1613](../Onda/qt_workspace_ui.py#L1613) | função/método |
| `DesktopWorkspace.matches_checked` | [1614](../Onda/qt_workspace_ui.py#L1614) | função/método |
| `DesktopWorkspace.navigation` | [1619](../Onda/qt_workspace_ui.py#L1619) | função/método |
| `DesktopWorkspace.releaseDateText` | [1630](../Onda/qt_workspace_ui.py#L1630) | função/método |
| `DesktopWorkspace.clock` | [1635](../Onda/qt_workspace_ui.py#L1635) | função/método |

</details>

<details>
<summary><code>queue_artwork.py</code> — 6 declarações</summary>

[Onda/queue_artwork.py](../Onda/queue_artwork.py)

Descrição do módulo no fonte: Bounded, asynchronous artwork loading for visible queue cards.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueArtwork` | [6](../Onda/queue_artwork.py#L6) | classe |
| `QueueArtwork.__init__` | [7](../Onda/queue_artwork.py#L7) | função/método |
| `QueueArtwork.get` | [15](../Onda/queue_artwork.py#L15) | função/método |
| `QueueArtwork.run` | [28](../Onda/queue_artwork.py#L28) | função/método |
| `QueueArtwork.poll` | [40](../Onda/queue_artwork.py#L40) | função/método |
| `QueueArtwork.shutdown` | [47](../Onda/queue_artwork.py#L47) | função/método |

</details>

<details>
<summary><code>queue_cards.py</code> — 10 declarações</summary>

[Onda/queue_cards.py](../Onda/queue_cards.py)

Descrição do módulo no fonte: A card view of the existing queue; Treeview remains the selection/order model.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueCards` | [6](../Onda/queue_cards.py#L6) | classe |
| `QueueCards.__init__` | [7](../Onda/queue_cards.py#L7) | função/método |
| `QueueCards.changed` | [20](../Onda/queue_cards.py#L20) | função/método |
| `QueueCards.refresh` | [31](../Onda/queue_cards.py#L31) | função/método |
| `QueueCards.wrap_labels` | [110](../Onda/queue_cards.py#L110) | função/método |
| `QueueCards.select` | [115](../Onda/queue_cards.py#L115) | função/método |
| `QueueCards.remove_selected` | [119](../Onda/queue_cards.py#L119) | função/método |
| `QueueCards.more` | [122](../Onda/queue_cards.py#L122) | função/método |
| `QueueCards.resize_cards` | [124](../Onda/queue_cards.py#L124) | função/método |
| `QueueCards.shutdown` | [133](../Onda/queue_cards.py#L133) | função/método |

</details>

<details>
<summary><code>queue_control.py</code> — 22 declarações</summary>

[Onda/queue_control.py](../Onda/queue_control.py)

Descrição do módulo no fonte: Queue-only ordering, live activity and conservative storage estimates.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `positive` | [11](../Onda/queue_control.py#L11) | função/método |
| `duration` | [17](../Onda/queue_control.py#L17) | função/método |
| `estimated_bytes` | [21](../Onda/queue_control.py#L21) | função/método |
| `sorted_keys` | [30](../Onda/queue_control.py#L30) | função/método |
| `sorted_keys.value` | [34](../Onda/queue_control.py#L34) | função/método |
| `replace_pending` | [39](../Onda/queue_control.py#L39) | função/método |
| `storage_report` | [43](../Onda/queue_control.py#L43) | função/método |
| `summary` | [63](../Onda/queue_control.py#L63) | função/método |
| `activity` | [67](../Onda/queue_control.py#L67) | função/método |
| `observe` | [78](../Onda/queue_control.py#L78) | função/método |
| `QueueControl` | [95](../Onda/queue_control.py#L95) | classe |
| `QueueControl.__init__` | [96](../Onda/queue_control.py#L96) | função/método |
| `QueueControl.apply` | [110](../Onda/queue_control.py#L110) | função/método |
| `QueueControl.sort` | [117](../Onda/queue_control.py#L117) | função/método |
| `QueueControl.move_before` | [121](../Onda/queue_control.py#L121) | função/método |
| `QueueControl.move_selection` | [126](../Onda/queue_control.py#L126) | função/método |
| `QueueControl.bind_drag` | [135](../Onda/queue_control.py#L135) | função/método |
| `QueueControl.bind_drag.press` | [136](../Onda/queue_control.py#L136) | função/método |
| `QueueControl.bind_drag.motion` | [139](../Onda/queue_control.py#L139) | função/método |
| `QueueControl.bind_drag.release` | [146](../Onda/queue_control.py#L146) | função/método |
| `QueueControl.refresh` | [155](../Onda/queue_control.py#L155) | função/método |
| `QueueControl.confirm` | [169](../Onda/queue_control.py#L169) | função/método |

</details>

<details>
<summary><code>queue_details.py</code> — 1 declarações</summary>

[Onda/queue_details.py](../Onda/queue_details.py)

Descrição do módulo no fonte: Small, persistable subset of catalog metadata for queue presentation.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `queue_info` | [3](../Onda/queue_details.py#L3) | função/método |

</details>

<details>
<summary><code>queue_filter.py</code> — 10 declarações</summary>

[Onda/queue_filter.py](../Onda/queue_filter.py)

Descrição do módulo no fonte: Presentation-only filtering; the execution queue model is never detached or reordered.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `folded` | [9](../Onda/queue_filter.py#L9) | função/método |
| `matches` | [10](../Onda/queue_filter.py#L10) | função/método |
| `QueueFilter` | [17](../Onda/queue_filter.py#L17) | classe |
| `QueueFilter.__init__` | [18](../Onda/queue_filter.py#L18) | função/método |
| `QueueFilter.clear` | [28](../Onda/queue_filter.py#L28) | função/método |
| `QueueFilter.changed` | [29](../Onda/queue_filter.py#L29) | função/método |
| `QueueFilter.visible_keys` | [32](../Onda/queue_filter.py#L32) | função/método |
| `QueueFilter.compact` | [45](../Onda/queue_filter.py#L45) | função/método |
| `QueueFilter.connect_scroll` | [81](../Onda/queue_filter.py#L81) | função/método |
| `QueueFilter.select` | [91](../Onda/queue_filter.py#L91) | função/método |

</details>

<details>
<summary><code>queue_timing.py</code> — 7 declarações</summary>

[Onda/queue_timing.py](../Onda/queue_timing.py)

Descrição do módulo no fonte: Session timing based on monotonic active time and observed successful jobs.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `duration_text` | [6](../Onda/queue_timing.py#L6) | função/método |
| `QueueTiming` | [13](../Onda/queue_timing.py#L13) | classe |
| `QueueTiming.__init__` | [14](../Onda/queue_timing.py#L14) | função/método |
| `QueueTiming.reset` | [18](../Onda/queue_timing.py#L18) | função/método |
| `QueueTiming.set_running` | [23](../Onda/queue_timing.py#L23) | função/método |
| `QueueTiming.record_completion` | [30](../Onda/queue_timing.py#L30) | função/método |
| `QueueTiming.snapshot` | [34](../Onda/queue_timing.py#L34) | função/método |

</details>

<details>
<summary><code>queue_titles.py</code> — 14 declarações</summary>

[Onda/queue_titles.py](../Onda/queue_titles.py)

Descrição do módulo no fonte: Names already loaded are immediate; bare music links resolve off the UI thread.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `record_name` | [7](../Onda/queue_titles.py#L7) | função/método |
| `supports_lookup` | [16](../Onda/queue_titles.py#L16) | função/método |
| `describe_streaming` | [22](../Onda/queue_titles.py#L22) | função/método |
| `resolve_record` | [58](../Onda/queue_titles.py#L58) | função/método |
| `resolve_record.QuietLogger` | [68](../Onda/queue_titles.py#L68) | classe |
| `resolve_record.QuietLogger.debug` | [69](../Onda/queue_titles.py#L69) | função/método |
| `resolve_record.QuietLogger.warning` | [70](../Onda/queue_titles.py#L70) | função/método |
| `resolve_record.QuietLogger.error` | [71](../Onda/queue_titles.py#L71) | função/método |
| `resolve_name` | [83](../Onda/queue_titles.py#L83) | função/método |
| `TitleLookup` | [87](../Onda/queue_titles.py#L87) | classe |
| `TitleLookup.__init__` | [88](../Onda/queue_titles.py#L88) | função/método |
| `TitleLookup.submit` | [94](../Onda/queue_titles.py#L94) | função/método |
| `TitleLookup.run` | [105](../Onda/queue_titles.py#L105) | função/método |
| `TitleLookup.shutdown` | [121](../Onda/queue_titles.py#L121) | função/método |

</details>

<details>
<summary><code>queue_undo.py</code> — 5 declarações</summary>

[Onda/queue_undo.py](../Onda/queue_undo.py)

Descrição do módulo no fonte: Bounded queue undo. Files and running download results are never rolled back.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueUndo` | [3](../Onda/queue_undo.py#L3) | classe |
| `QueueUndo.__init__` | [4](../Onda/queue_undo.py#L4) | função/método |
| `QueueUndo.remember` | [5](../Onda/queue_undo.py#L5) | função/método |
| `QueueUndo.record_finished_removal` | [8](../Onda/queue_undo.py#L8) | função/método |
| `QueueUndo.restore` | [11](../Onda/queue_undo.py#L11) | função/método |

</details>

<details>
<summary><code>record_identity.py</code> — 4 declarações</summary>

[Onda/record_identity.py](../Onda/record_identity.py)

Descrição do módulo no fonte: Evidence for translated catalog titles; never use playlist position as track number.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalized_isrc` | [9](../Onda/record_identity.py#L9) | função/método |
| `duration_match` | [14](../Onda/record_identity.py#L14) | função/método |
| `artist_and_duration_match` | [20](../Onda/record_identity.py#L20) | função/método |
| `catalog_identity` | [28](../Onda/record_identity.py#L28) | função/método |

</details>

<details>
<summary><code>reset_settings.py</code> — 7 declarações</summary>

[Onda/reset_settings.py](../Onda/reset_settings.py)

Descrição do módulo no fonte: Reviewable, selective preference resets; user data and accounts stay intact.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `apply_defaults` | [62](../Onda/reset_settings.py#L62) | função/método |
| `ResetSettingsWindow` | [93](../Onda/reset_settings.py#L93) | classe |
| `ResetSettingsWindow.__init__` | [94](../Onda/reset_settings.py#L94) | função/método |
| `ResetSettingsWindow.select` | [135](../Onda/reset_settings.py#L135) | função/método |
| `ResetSettingsWindow.refresh` | [138](../Onda/reset_settings.py#L138) | função/método |
| `ResetSettingsWindow.restore` | [143](../Onda/reset_settings.py#L143) | função/método |
| `show_reset` | [156](../Onda/reset_settings.py#L156) | função/método |

</details>

<details>
<summary><code>review.py</code> — 2 declarações</summary>

[Onda/review.py](../Onda/review.py)

Descrição do módulo no fonte: Validate only user-editable tag fields, leaving source identity intact.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `apply_review` | [8](../Onda/review.py#L8) | função/método |
| `local_cover` | [42](../Onda/review.py#L42) | função/método |

</details>

<details>
<summary><code>review_ui.py</code> — 12 declarações</summary>

[Onda/review_ui.py](../Onda/review_ui.py)

Descrição do módulo no fonte: Metadata/collision dialogs used by the worker's request/reply protocol.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MetadataReview` | [14](../Onda/review_ui.py#L14) | classe |
| `MetadataReview.__init__` | [15](../Onda/review_ui.py#L15) | função/método |
| `MetadataReview.choose_cover` | [74](../Onda/review_ui.py#L74) | função/método |
| `MetadataReview.use_url` | [80](../Onda/review_ui.py#L80) | função/método |
| `MetadataReview.load_cover` | [84](../Onda/review_ui.py#L84) | função/método |
| `MetadataReview.load_cover.worker` | [88](../Onda/review_ui.py#L88) | função/método |
| `MetadataReview.poll` | [106](../Onda/review_ui.py#L106) | função/método |
| `MetadataReview.preview` | [125](../Onda/review_ui.py#L125) | função/método |
| `MetadataReview.confirm` | [135](../Onda/review_ui.py#L135) | função/método |
| `MetadataReview.destroy` | [148](../Onda/review_ui.py#L148) | função/método |
| `DuplicateDialog` | [157](../Onda/review_ui.py#L157) | classe |
| `DuplicateDialog.__init__` | [158](../Onda/review_ui.py#L158) | função/método |

</details>

<details>
<summary><code>search_choices.py</code> — 7 declarações</summary>

[Onda/search_choices.py](../Onda/search_choices.py)

Descrição do módulo no fonte: Bounded local, opt-in recording choices; no credentials or search history.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `identity` | [11](../Onda/search_choices.py#L11) | função/método |
| `ChoiceStore` | [17](../Onda/search_choices.py#L17) | classe |
| `ChoiceStore.__init__` | [18](../Onda/search_choices.py#L18) | função/método |
| `ChoiceStore._connect` | [23](../Onda/search_choices.py#L23) | função/método |
| `ChoiceStore.get` | [33](../Onda/search_choices.py#L33) | função/método |
| `ChoiceStore.set` | [40](../Onda/search_choices.py#L40) | função/método |
| `ChoiceStore.clear` | [49](../Onda/search_choices.py#L49) | função/método |

</details>

<details>
<summary><code>search_evidence.py</code> — 9 declarações</summary>

[Onda/search_evidence.py](../Onda/search_evidence.py)

Descrição do módulo no fonte: Conservative evidence shared by desktop and Android music matching.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `explicit_conflict` | [6](../Onda/search_evidence.py#L6) | função/método |
| `album_core` | [19](../Onda/search_evidence.py#L19) | função/método |
| `release_year` | [25](../Onda/search_evidence.py#L25) | função/método |
| `video_identity` | [30](../Onda/search_evidence.py#L30) | função/método |
| `presentation_title` | [42](../Onda/search_evidence.py#L42) | função/método |
| `presentation_title.labels` | [51](../Onda/search_evidence.py#L51) | função/método |
| `presentation_title.labels.from_album` | [53](../Onda/search_evidence.py#L53) | função/método |
| `presentation_title.labels.brand` | [58](../Onda/search_evidence.py#L58) | função/método |
| `album_search_title` | [89](../Onda/search_evidence.py#L89) | função/método |

</details>

<details>
<summary><code>settings_common_ui.py</code> — 16 declarações</summary>

[Onda/settings_common_ui.py](../Onda/settings_common_ui.py)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `format_controls` | [5](../Onda/settings_common_ui.py#L5) | função/método |
| `format_controls.refresh` | [11](../Onda/settings_common_ui.py#L11) | função/método |
| `image_controls` | [25](../Onda/settings_common_ui.py#L25) | função/método |
| `image_controls.refresh` | [36](../Onda/settings_common_ui.py#L36) | função/método |
| `tab_order_controls` | [44](../Onda/settings_common_ui.py#L44) | função/método |
| `tab_order_controls.refresh` | [47](../Onda/settings_common_ui.py#L47) | função/método |
| `tab_order_controls.move` | [53](../Onda/settings_common_ui.py#L53) | função/método |
| `tab_order_controls.update_hidden` | [72](../Onda/settings_common_ui.py#L72) | função/método |
| `tab_order_controls.refresh_hidden` | [79](../Onda/settings_common_ui.py#L79) | função/método |
| `account_controls` | [84](../Onda/settings_common_ui.py#L84) | função/método |
| `account_controls.disconnect` | [96](../Onda/settings_common_ui.py#L96) | função/método |
| `account_controls.choose` | [101](../Onda/settings_common_ui.py#L101) | função/método |
| `verify_tools` | [111](../Onda/settings_common_ui.py#L111) | função/método |
| `verify_tools.run` | [115](../Onda/settings_common_ui.py#L115) | função/método |
| `verify_tools.run.worker` | [118](../Onda/settings_common_ui.py#L118) | função/método |
| `verify_tools.run.poll` | [126](../Onda/settings_common_ui.py#L126) | função/método |

</details>

<details>
<summary><code>settings_layout.py</code> — 0 declarações</summary>

[Onda/settings_layout.py](../Onda/settings_layout.py)

Descrição do módulo no fonte: Category order shared with Android; persisted preference identifiers remain unchanged.

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>settings_scroll.py</code> — 10 declarações</summary>

[Onda/settings_scroll.py](../Onda/settings_scroll.py)

Descrição do módulo no fonte: Scrollable category pages that adapt to window size and display scaling.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SettingsCategory` | [6](../Onda/settings_scroll.py#L6) | classe |
| `SettingsCategory.__init__` | [7](../Onda/settings_scroll.py#L7) | função/método |
| `SettingsCategory.destroy` | [26](../Onda/settings_scroll.py#L26) | função/método |
| `SettingsCategory.resize` | [32](../Onda/settings_scroll.py#L32) | função/método |
| `SettingsCategory.update_region` | [42](../Onda/settings_scroll.py#L42) | função/método |
| `SettingsCategory.refresh_when_idle` | [52](../Onda/settings_scroll.py#L52) | função/método |
| `SettingsCategory._refresh_layout` | [57](../Onda/settings_scroll.py#L57) | função/método |
| `SettingsCategory.wheel` | [61](../Onda/settings_scroll.py#L61) | função/método |
| `scroll_page` | [70](../Onda/settings_scroll.py#L70) | função/método |
| `refresh_page_layout` | [79](../Onda/settings_scroll.py#L79) | função/método |

</details>

<details>
<summary><code>settings_search.py</code> — 8 declarações</summary>

[Onda/settings_search.py](../Onda/settings_search.py)

Descrição do módulo no fonte: Search actual settings labels in the current language and reveal their location.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalize` | [7](../Onda/settings_search.py#L7) | função/método |
| `SettingsSearch` | [9](../Onda/settings_search.py#L9) | classe |
| `SettingsSearch.__init__` | [10](../Onda/settings_search.py#L10) | função/método |
| `SettingsSearch.changed` | [22](../Onda/settings_search.py#L22) | função/método |
| `SettingsSearch.widgets` | [25](../Onda/settings_search.py#L25) | função/método |
| `SettingsSearch.search` | [29](../Onda/settings_search.py#L29) | função/método |
| `SettingsSearch.open` | [48](../Onda/settings_search.py#L48) | função/método |
| `SettingsSearch.destroyed` | [60](../Onda/settings_search.py#L60) | função/método |

</details>

<details>
<summary><code>settings_search_index.py</code> — 4 declarações</summary>

[Onda/settings_search_index.py](../Onda/settings_search_index.py)

Descrição do módulo no fonte: Search settings labels, descriptions and their real categories in the UI language.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `fold` | [8](../Onda/settings_search_index.py#L8) | função/método |
| `search_terms` | [12](../Onda/settings_search_index.py#L12) | função/método |
| `indexed_text` | [16](../Onda/settings_search_index.py#L16) | função/método |
| `matches` | [20](../Onda/settings_search_index.py#L20) | função/método |

</details>

<details>
<summary><code>shortcut_options.py</code> — 5 declarações</summary>

[Onda/shortcut_options.py](../Onda/shortcut_options.py)

Descrição do módulo no fonte: Validated desktop shortcut preferences; no UI or download dependencies.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `canonical` | [10](../Onda/shortcut_options.py#L10) | função/método |
| `validate_overrides` | [33](../Onda/shortcut_options.py#L33) | função/método |
| `load_overrides` | [53](../Onda/shortcut_options.py#L53) | função/método |
| `effective_bindings` | [57](../Onda/shortcut_options.py#L57) | função/método |
| `display_shortcut` | [63](../Onda/shortcut_options.py#L63) | função/método |

</details>

<details>
<summary><code>silence.py</code> — 4 declarações</summary>

[Onda/silence.py](../Onda/silence.py)

Descrição do módulo no fonte: Cancelable silence analysis; automatic trimming affects only the file edges.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `fingerprint` | [6](../Onda/silence.py#L6) | função/método |
| `bounds` | [10](../Onda/silence.py#L10) | função/método |
| `detect` | [22](../Onda/silence.py#L22) | função/método |
| `cached` | [44](../Onda/silence.py#L44) | função/método |

</details>

<details>
<summary><code>simple_download_ui.py</code> — 2 declarações</summary>

[Onda/simple_download_ui.py](../Onda/simple_download_ui.py)

Descrição do módulo no fonte: Reuse existing controls; hiding them never overwrites saved selections.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `bind_simple_grid` | [2](../Onda/simple_download_ui.py#L2) | função/método |
| `bind_simple_grid.refresh` | [3](../Onda/simple_download_ui.py#L3) | função/método |

</details>

<details>
<summary><code>single_instance.py</code> — 11 declarações</summary>

[Onda/single_instance.py](../Onda/single_instance.py)

Descrição do módulo no fonte: One Onda window per Windows session, shared by portable and installed copies.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SingleInstance` | [9](../Onda/single_instance.py#L9) | classe |
| `SingleInstance.__init__` | [10](../Onda/single_instance.py#L10) | função/método |
| `SingleInstance.notify` | [44](../Onda/single_instance.py#L44) | função/método |
| `SingleInstance.activation_requested` | [52](../Onda/single_instance.py#L52) | função/método |
| `SingleInstance.watch` | [55](../Onda/single_instance.py#L55) | função/método |
| `SingleInstance.poll` | [60](../Onda/single_instance.py#L60) | função/método |
| `SingleInstance.close` | [73](../Onda/single_instance.py#L73) | função/método |
| `SingleInstance.__enter__` | [86](../Onda/single_instance.py#L86) | função/método |
| `SingleInstance.__exit__` | [89](../Onda/single_instance.py#L89) | função/método |
| `already_open_message` | [93](../Onda/single_instance.py#L93) | função/método |
| `run_single_instance` | [104](../Onda/single_instance.py#L104) | função/método |

</details>

<details>
<summary><code>size_estimate.py</code> — 2 declarações</summary>

[Onda/size_estimate.py](../Onda/size_estimate.py)

Descrição do módulo no fonte: Output-size estimates based on selected formats, not all formats on a page.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `positive` | [4](../Onda/size_estimate.py#L4) | função/método |
| `estimate_size` | [8](../Onda/size_estimate.py#L8) | função/método |

</details>

<details>
<summary><code>slider_style.py</code> — 1 declarações</summary>

[Onda/slider_style.py](../Onda/slider_style.py)

Descrição do módulo no fonte: Shared round slider thumb, preserving ttk keyboard and pointer behavior.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `configure_sliders` | [7](../Onda/slider_style.py#L7) | função/método |

</details>

<details>
<summary><code>social_media.py</code> — 31 declarações</summary>

[Onda/social_media.py](../Onda/social_media.py)

Descrição do módulo no fonte: Photo and mixed-post downloads through gallery-dl, sharing Onda's queue IPC.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `GalleryLogger` | [17](../Onda/social_media.py#L17) | classe |
| `GalleryLogger.__init__` | [19](../Onda/social_media.py#L19) | função/método |
| `GalleryLogger.debug` | [23](../Onda/social_media.py#L23) | função/método |
| `GalleryLogger.info` | [26](../Onda/social_media.py#L26) | função/método |
| `GalleryLogger.warning` | [29](../Onda/social_media.py#L29) | função/método |
| `GalleryLogger.error` | [32](../Onda/social_media.py#L32) | função/método |
| `GalleryLogger.traceback` | [37](../Onda/social_media.py#L37) | função/método |
| `is_social` | [42](../Onda/social_media.py#L42) | função/método |
| `session_for` | [47](../Onda/social_media.py#L47) | função/método |
| `PageData` | [62](../Onda/social_media.py#L62) | classe |
| `PageData.__init__` | [63](../Onda/social_media.py#L63) | função/método |
| `PageData.handle_starttag` | [67](../Onda/social_media.py#L67) | função/método |
| `PageData.handle_data` | [71](../Onda/social_media.py#L71) | função/método |
| `PageData.handle_endtag` | [75](../Onda/social_media.py#L75) | função/método |
| `kwai_images` | [81](../Onda/social_media.py#L81) | função/método |
| `kwai_images.walk` | [86](../Onda/social_media.py#L86) | função/método |
| `save_media` | [127](../Onda/social_media.py#L127) | função/método |
| `extract_video_audio` | [231](../Onda/social_media.py#L231) | função/método |
| `media_candidates` | [256](../Onda/social_media.py#L256) | função/método |
| `download_selected` | [266](../Onda/social_media.py#L266) | função/método |
| `save_video` | [321](../Onda/social_media.py#L321) | função/método |
| `save_video.progress` | [344](../Onda/social_media.py#L344) | função/método |
| `save_video.Capture` | [349](../Onda/social_media.py#L349) | classe |
| `save_video.Capture.run` | [350](../Onda/social_media.py#L350) | função/método |
| `save_video.Estimate` | [364](../Onda/social_media.py#L364) | classe |
| `save_video.Estimate.run` | [365](../Onda/social_media.py#L365) | função/método |
| `_download_post` | [389](../Onda/social_media.py#L389) | função/método |
| `video_fallback` | [479](../Onda/social_media.py#L479) | função/método |
| `access_error` | [487](../Onda/social_media.py#L487) | função/método |
| `download_post` | [502](../Onda/social_media.py#L502) | função/método |
| `download_post.choose` | [508](../Onda/social_media.py#L508) | função/método |

</details>

<details>
<summary><code>spotify_account.py</code> — 19 declarações</summary>

[Onda/spotify_account.py](../Onda/spotify_account.py)

Descrição do módulo no fonte: User-authorized, read-only playlist access via OAuth PKCE and loopback.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `token_request` | [24](../Onda/spotify_account.py#L24) | função/método |
| `callback_page` | [39](../Onda/spotify_account.py#L39) | função/método |
| `authorize` | [77](../Onda/spotify_account.py#L77) | função/método |
| `authorize.Callback` | [84](../Onda/spotify_account.py#L84) | classe |
| `authorize.Callback.log_message` | [85](../Onda/spotify_account.py#L85) | função/método |
| `authorize.Callback.do_GET` | [87](../Onda/spotify_account.py#L87) | função/método |
| `authorize.LocalServer` | [105](../Onda/spotify_account.py#L105) | classe |
| `authorize.LocalServer.get_request` | [106](../Onda/spotify_account.py#L106) | função/método |
| `SpotifyAccount` | [138](../Onda/spotify_account.py#L138) | classe |
| `SpotifyAccount.__init__` | [139](../Onda/spotify_account.py#L139) | função/método |
| `SpotifyAccount.connected` | [155](../Onda/spotify_account.py#L155) | função/método |
| `SpotifyAccount.accept` | [158](../Onda/spotify_account.py#L158) | função/método |
| `SpotifyAccount._accept` | [162](../Onda/spotify_account.py#L162) | função/método |
| `SpotifyAccount.disconnect` | [175](../Onda/spotify_account.py#L175) | função/método |
| `SpotifyAccount._disconnect` | [179](../Onda/spotify_account.py#L179) | função/método |
| `SpotifyAccount.token` | [185](../Onda/spotify_account.py#L185) | função/método |
| `SpotifyAccount._token` | [189](../Onda/spotify_account.py#L189) | função/método |
| `SpotifyAccount.get` | [202](../Onda/spotify_account.py#L202) | função/método |
| `SpotifyAccount.playlist` | [228](../Onda/spotify_account.py#L228) | função/método |

</details>

<details>
<summary><code>spotify_account_ui.py</code> — 7 declarações</summary>

[Onda/spotify_account_ui.py](../Onda/spotify_account_ui.py)

Descrição do módulo no fonte: Optional Spotify account connection; all Tk access stays on the UI thread.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SpotifyConnection` | [14](../Onda/spotify_account_ui.py#L14) | classe |
| `SpotifyConnection.__init__` | [15](../Onda/spotify_account_ui.py#L15) | função/método |
| `SpotifyConnection.connect` | [61](../Onda/spotify_account_ui.py#L61) | função/método |
| `SpotifyConnection.connect.worker` | [72](../Onda/spotify_account_ui.py#L72) | função/método |
| `SpotifyConnection.poll` | [79](../Onda/spotify_account_ui.py#L79) | função/método |
| `SpotifyConnection.disconnect` | [102](../Onda/spotify_account_ui.py#L102) | função/método |
| `SpotifyConnection.close` | [112](../Onda/spotify_account_ui.py#L112) | função/método |

</details>

<details>
<summary><code>spotify_metadata.py</code> — 6 declarações</summary>

[Onda/spotify_metadata.py](../Onda/spotify_metadata.py)

Descrição do módulo no fonte: Spotify identity is primary only for validated direct Spotify track links.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `missing` | [7](../Onda/spotify_metadata.py#L7) | função/método |
| `spotify_track` | [10](../Onda/spotify_metadata.py#L10) | função/método |
| `original_metadata` | [16](../Onda/spotify_metadata.py#L16) | função/método |
| `supplement_metadata` | [22](../Onda/spotify_metadata.py#L22) | função/método |
| `source_label` | [36](../Onda/spotify_metadata.py#L36) | função/método |
| `prepare_spotify_config` | [40](../Onda/spotify_metadata.py#L40) | função/método |

</details>

<details>
<summary><code>spotify_public.py</code> — 6 declarações</summary>

[Onda/spotify_public.py](../Onda/spotify_public.py)

Descrição do módulo no fonte: Read only the track entity from the public Spotify embed, never its session.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `EmbedParser` | [8](../Onda/spotify_public.py#L8) | classe |
| `EmbedParser.__init__` | [9](../Onda/spotify_public.py#L9) | função/método |
| `EmbedParser.handle_starttag` | [14](../Onda/spotify_public.py#L14) | função/método |
| `EmbedParser.handle_data` | [18](../Onda/spotify_public.py#L18) | função/método |
| `EmbedParser.handle_endtag` | [22](../Onda/spotify_public.py#L22) | função/método |
| `parse_public_track` | [27](../Onda/spotify_public.py#L27) | função/método |

</details>

<details>
<summary><code>spotify_search.py</code> — 2 declarações</summary>

[Onda/spotify_search.py](../Onda/spotify_search.py)

Descrição do módulo no fonte: Authenticated Spotify catalog search, paginated with fixed API paths.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `search_tracks` | [6](../Onda/spotify_search.py#L6) | função/método |
| `cached_record` | [30](../Onda/spotify_search.py#L30) | função/método |

</details>

<details>
<summary><code>status_notice.py</code> — 8 declarações</summary>

[Onda/status_notice.py](../Onda/status_notice.py)

Descrição do módulo no fonte: Optional dismissal of status text without discarding operation state.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `StatusNotice` | [6](../Onda/status_notice.py#L6) | classe |
| `StatusNotice.__init__` | [7](../Onda/status_notice.py#L7) | função/método |
| `StatusNotice.changed` | [13](../Onda/status_notice.py#L13) | função/método |
| `StatusNotice.animate` | [19](../Onda/status_notice.py#L19) | função/método |
| `StatusNotice.animate.frame` | [32](../Onda/status_notice.py#L32) | função/método |
| `StatusNotice.check` | [39](../Onda/status_notice.py#L39) | função/método |
| `StatusNotice.dismiss` | [50](../Onda/status_notice.py#L50) | função/método |
| `StatusNotice.shutdown` | [53](../Onda/status_notice.py#L53) | função/método |

</details>

<details>
<summary><code>synced_lyrics.py</code> — 4 declarações</summary>

[Onda/synced_lyrics.py](../Onda/synced_lyrics.py)

Descrição do módulo no fonte: Bounded LRC parsing, shared by desktop and Android playback.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `parse_lrc` | [6](../Onda/synced_lyrics.py#L6) | função/método |
| `read_lrc` | [24](../Onda/synced_lyrics.py#L24) | função/método |
| `line_at` | [27](../Onda/synced_lyrics.py#L27) | função/método |
| `karaoke_at` | [32](../Onda/synced_lyrics.py#L32) | função/método |

</details>

<details>
<summary><code>tab_order.py</code> — 18 declarações</summary>

[Onda/tab_order.py](../Onda/tab_order.py)

Descrição do módulo no fonte: Stable tab identities and drag ordering without changing active content.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalize_hidden` | [11](../Onda/tab_order.py#L11) | função/método |
| `NavigationNotebook` | [16](../Onda/tab_order.py#L16) | classe |
| `NavigationNotebook.select` | [17](../Onda/tab_order.py#L17) | função/método |
| `NavigationNotebook.visible_tabs` | [22](../Onda/tab_order.py#L22) | função/método |
| `normalize_order` | [26](../Onda/tab_order.py#L26) | função/método |
| `TabReorder` | [41](../Onda/tab_order.py#L41) | classe |
| `TabReorder.__init__` | [42](../Onda/tab_order.py#L42) | função/método |
| `TabReorder.order` | [58](../Onda/tab_order.py#L58) | função/método |
| `TabReorder.apply` | [62](../Onda/tab_order.py#L62) | função/método |
| `TabReorder.set_hidden` | [70](../Onda/tab_order.py#L70) | função/método |
| `TabReorder.hit` | [78](../Onda/tab_order.py#L78) | função/método |
| `TabReorder.press` | [84](../Onda/tab_order.py#L84) | função/método |
| `TabReorder.motion` | [92](../Onda/tab_order.py#L92) | função/método |
| `TabReorder.release` | [105](../Onda/tab_order.py#L105) | função/método |
| `TabReorder.cancel` | [117](../Onda/tab_order.py#L117) | função/método |
| `TabReorder.context` | [124](../Onda/tab_order.py#L124) | função/método |
| `TabReorder.move` | [138](../Onda/tab_order.py#L138) | função/método |
| `TabReorder.reset` | [147](../Onda/tab_order.py#L147) | função/método |

</details>

<details>
<summary><code>tagging.py</code> — 3 declarações</summary>

[Onda/tagging.py](../Onda/tagging.py)

Descrição do módulo no fonte: Write available catalog fields and provenance to audio, using an atomic replacement.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `fetch_cover` | [9](../Onda/tagging.py#L9) | função/método |
| `apply_tags` | [39](../Onda/tagging.py#L39) | função/método |
| `optional_cover` | [130](../Onda/tagging.py#L130) | função/método |

</details>

<details>
<summary><code>tiktok_media.py</code> — 7 declarações</summary>

[Onda/tiktok_media.py](../Onda/tiktok_media.py)

Descrição do módulo no fonte: Resolve TikTok photos with the same webpage/session support as videos.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `TikTokMediaIE` | [10](../Onda/tiktok_media.py#L10) | classe |
| `TikTokMediaIE._parse_aweme_video_web` | [11](../Onda/tiktok_media.py#L11) | função/método |
| `post_items` | [16](../Onda/tiktok_media.py#L16) | função/método |
| `embedded_post` | [52](../Onda/tiktok_media.py#L52) | função/método |
| `mobile_post` | [74](../Onda/tiktok_media.py#L74) | função/método |
| `mobile_post.page` | [78](../Onda/tiktok_media.py#L78) | função/método |
| `tiktok_items` | [104](../Onda/tiktok_media.py#L104) | função/método |

</details>

<details>
<summary><code>tool_status.py</code> — 7 declarações</summary>

[Onda/tool_status.py](../Onda/tool_status.py)

Descrição do módulo no fonte: Bounded local tool checks and persistent verification/update timestamps.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `now` | [13](../Onda/tool_status.py#L13) | função/método |
| `read` | [17](../Onda/tool_status.py#L17) | função/método |
| `save` | [25](../Onda/tool_status.py#L25) | função/método |
| `updated` | [36](../Onda/tool_status.py#L36) | função/método |
| `check` | [42](../Onda/tool_status.py#L42) | função/método |
| `present` | [63](../Onda/tool_status.py#L63) | função/método |
| `display` | [73](../Onda/tool_status.py#L73) | função/método |

</details>

<details>
<summary><code>twitter_media.py</code> — 3 declarações</summary>

[Onda/twitter_media.py](../Onda/twitter_media.py)

Descrição do módulo no fonte: Resolve photos and videos together using yt-dlp's Twitter session support.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `is_twitter` | [10](../Onda/twitter_media.py#L10) | função/método |
| `tweet_items` | [15](../Onda/twitter_media.py#L15) | função/método |
| `twitter_items` | [69](../Onda/twitter_media.py#L69) | função/método |

</details>

<details>
<summary><code>ui.py</code> — 17 declarações</summary>

[Onda/ui.py](../Onda/ui.py)

Descrição do módulo no fonte: Desktop presentation, kept separate from download and queue behavior.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `UiMixin` | [19](../Onda/ui.py#L19) | classe |
| `UiMixin._style` | [20](../Onda/ui.py#L20) | função/método |
| `UiMixin._layout` | [112](../Onda/ui.py#L112) | função/método |
| `UiMixin._layout.remove_selected` | [266](../Onda/ui.py#L266) | função/método |
| `UiMixin._layout.position_actions` | [307](../Onda/ui.py#L307) | função/método |
| `UiMixin.sync_format` | [319](../Onda/ui.py#L319) | função/método |
| `UiMixin.change_format` | [324](../Onda/ui.py#L324) | função/método |
| `UiMixin.update_quality_selector` | [328](../Onda/ui.py#L328) | função/método |
| `UiMixin.refresh_placeholder` | [347](../Onda/ui.py#L347) | função/método |
| `UiMixin.on_link_edit` | [353](../Onda/ui.py#L353) | função/método |
| `UiMixin.refresh_queue` | [358](../Onda/ui.py#L358) | função/método |
| `UiMixin.refresh_queue_timing` | [374](../Onda/ui.py#L374) | função/método |
| `UiMixin._build_settings` | [391](../Onda/ui.py#L391) | função/método |
| `UiMixin._build_settings.update_output_preview` | [522](../Onda/ui.py#L522) | função/método |
| `UiMixin._build_log` | [592](../Onda/ui.py#L592) | função/método |
| `UiMixin.show_settings` | [611](../Onda/ui.py#L611) | função/método |
| `UiMixin.show_log` | [615](../Onda/ui.py#L615) | função/método |

</details>

<details>
<summary><code>version_picker.py</code> — 12 declarações</summary>

[Onda/version_picker.py](../Onda/version_picker.py)

Descrição do módulo no fonte: Non-blocking version choice while the worker waits for a JSON reply.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `duration_label` | [9](../Onda/version_picker.py#L9) | função/método |
| `VersionPicker` | [16](../Onda/version_picker.py#L16) | classe |
| `VersionPicker.__init__` | [17](../Onda/version_picker.py#L17) | função/método |
| `VersionPicker.selected` | [87](../Onda/version_picker.py#L87) | função/método |
| `VersionPicker.choose` | [96](../Onda/version_picker.py#L96) | função/método |
| `VersionPicker.reject` | [103](../Onda/version_picker.py#L103) | função/método |
| `VersionPicker.clear_choices` | [112](../Onda/version_picker.py#L112) | função/método |
| `VersionPicker.double_click` | [117](../Onda/version_picker.py#L117) | função/método |
| `VersionPicker.open_video` | [124](../Onda/version_picker.py#L124) | função/método |
| `VersionPicker.preview` | [129](../Onda/version_picker.py#L129) | função/método |
| `VersionPicker.poll_preview` | [139](../Onda/version_picker.py#L139) | função/método |
| `VersionPicker.destroy` | [144](../Onda/version_picker.py#L144) | função/método |

</details>

<details>
<summary><code>video_converter.py</code> — 7 declarações</summary>

[Onda/video_converter.py](../Onda/video_converter.py)

Descrição do módulo no fonte: Local video conversion shared by desktop and Android; originals are read-only.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ConversionCancelled` | [24](../Onda/video_converter.py#L24) | classe |
| `probe_video` | [27](../Onda/video_converter.py#L27) | função/método |
| `convert_video` | [43](../Onda/video_converter.py#L43) | função/método |
| `convert_video.check` | [53](../Onda/video_converter.py#L53) | função/método |
| `convert_video.read` | [98](../Onda/video_converter.py#L98) | função/método |
| `convert_batch` | [132](../Onda/video_converter.py#L132) | função/método |
| `convert_batch.progress` | [149](../Onda/video_converter.py#L149) | função/método |

</details>

<details>
<summary><code>video_limits.py</code> — 3 declarações</summary>

[Onda/video_limits.py](../Onda/video_limits.py)

Descrição do módulo no fonte: Honor video ceilings when a platform only exposes a larger/faster source.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `video_stream` | [10](../Onda/video_limits.py#L10) | função/método |
| `limit_filters` | [31](../Onda/video_limits.py#L31) | função/método |
| `enforce_video_limits` | [44](../Onda/video_limits.py#L44) | função/método |

</details>

<details>
<summary><code>welcome_ui.py</code> — 4 declarações</summary>

[Onda/welcome_ui.py](../Onda/welcome_ui.py)

Descrição do módulo no fonte: Optional first-launch setup; edits remain local until the user applies them.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `WelcomeWindow` | [13](../Onda/welcome_ui.py#L13) | classe |
| `WelcomeWindow.__init__` | [14](../Onda/welcome_ui.py#L14) | função/método |
| `WelcomeWindow.choose_folder` | [57](../Onda/welcome_ui.py#L57) | função/método |
| `WelcomeWindow.apply` | [62](../Onda/welcome_ui.py#L62) | função/método |

</details>

<details>
<summary><code>window_icons.py</code> — 3 declarações</summary>

[Onda/window_icons.py](../Onda/window_icons.py)

Descrição do módulo no fonte: Small function icons rendered from shapes; no external assets are required.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `icon_kind` | [5](../Onda/window_icons.py#L5) | função/método |
| `draw_icon` | [17](../Onda/window_icons.py#L17) | função/método |
| `apply_window_icon` | [68](../Onda/window_icons.py#L68) | função/método |

</details>

<details>
<summary><code>window_position.py</code> — 6 declarações</summary>

[Onda/window_position.py](../Onda/window_position.py)

Descrição do módulo no fonte: Center application windows whenever they become visible.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `centered_position` | [6](../Onda/window_position.py#L6) | função/método |
| `_center_windows` | [12](../Onda/window_position.py#L12) | função/método |
| `_center_windows.MonitorInfo` | [16](../Onda/window_position.py#L16) | classe |
| `center_window` | [47](../Onda/window_position.py#L47) | função/método |
| `install_window_centering` | [61](../Onda/window_position.py#L61) | função/método |
| `install_window_centering.on_map` | [62](../Onda/window_position.py#L62) | função/método |

</details>

<details>
<summary><code>windows_drop.py</code> — 19 declarações</summary>

[Onda/windows_drop.py](../Onda/windows_drop.py)

Descrição do módulo no fonte: Windows OLE drop target using system APIs; no optional Tk extension.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `WindowsDrop` | [7](../Onda/windows_drop.py#L7) | classe |
| `WindowsDrop.__init__` | [8](../Onda/windows_drop.py#L8) | função/método |
| `WindowsDrop.build_target` | [37](../Onda/windows_drop.py#L37) | função/método |
| `WindowsDrop.build_target.Point` | [39](../Onda/windows_drop.py#L39) | classe |
| `WindowsDrop.build_target.query` | [44](../Onda/windows_drop.py#L44) | função/método |
| `WindowsDrop.build_target.add` | [50](../Onda/windows_drop.py#L50) | função/método |
| `WindowsDrop.build_target.release` | [51](../Onda/windows_drop.py#L51) | função/método |
| `WindowsDrop.build_target.enter` | [52](../Onda/windows_drop.py#L52) | função/método |
| `WindowsDrop.build_target.over` | [56](../Onda/windows_drop.py#L56) | função/método |
| `WindowsDrop.build_target.leave` | [57](../Onda/windows_drop.py#L57) | função/método |
| `WindowsDrop.build_target.drop` | [58](../Onda/windows_drop.py#L58) | função/método |
| `WindowsDrop.build_target.Target` | [68](../Onda/windows_drop.py#L68) | classe |
| `WindowsDrop.format` | [71](../Onda/windows_drop.py#L71) | função/método |
| `WindowsDrop.format.Format` | [72](../Onda/windows_drop.py#L72) | classe |
| `WindowsDrop.supported` | [75](../Onda/windows_drop.py#L75) | função/método |
| `WindowsDrop.read` | [80](../Onda/windows_drop.py#L80) | função/método |
| `WindowsDrop.read.Medium` | [81](../Onda/windows_drop.py#L81) | classe |
| `WindowsDrop.poll` | [109](../Onda/windows_drop.py#L109) | função/método |
| `WindowsDrop.shutdown` | [119](../Onda/windows_drop.py#L119) | função/método |

</details>

<details>
<summary><code>windows_media.py</code> — 16 declarações</summary>

[Onda/windows_media.py](../Onda/windows_media.py)

Descrição do módulo no fonte: Native Windows SMTC session shared by the existing ONDA players.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `method` | [14](../Onda/windows_media.py#L14) | função/método |
| `checked` | [18](../Onda/windows_media.py#L18) | função/método |
| `release` | [21](../Onda/windows_media.py#L21) | função/método |
| `MediaControls` | [24](../Onda/windows_media.py#L24) | classe |
| `MediaControls.__init__` | [25](../Onda/windows_media.py#L25) | função/método |
| `MediaControls.string` | [52](../Onda/windows_media.py#L52) | função/método |
| `MediaControls.make_delegate` | [54](../Onda/windows_media.py#L54) | função/método |
| `MediaControls.make_delegate.query` | [59](../Onda/windows_media.py#L59) | função/método |
| `MediaControls.make_delegate.add` | [62](../Onda/windows_media.py#L62) | função/método |
| `MediaControls.make_delegate.drop` | [63](../Onda/windows_media.py#L63) | função/método |
| `MediaControls.make_delegate.invoke` | [64](../Onda/windows_media.py#L64) | função/método |
| `MediaControls.make_delegate.Delegate` | [72](../Onda/windows_media.py#L72) | classe |
| `MediaControls.set_cover` | [74](../Onda/windows_media.py#L74) | função/método |
| `MediaControls.navigation` | [99](../Onda/windows_media.py#L99) | função/método |
| `MediaControls.update` | [105](../Onda/windows_media.py#L105) | função/método |
| `MediaControls.close` | [121](../Onda/windows_media.py#L121) | função/método |

</details>

<details>
<summary><code>windows_shell.py</code> — 14 declarações</summary>

[Onda/windows_shell.py](../Onda/windows_shell.py)

Descrição do módulo no fonte: Native Windows tray, balloon notifications and taskbar progress; no helper process.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `Guid` | [7](../Onda/windows_shell.py#L7) | classe |
| `Guid.value` | [10](../Onda/windows_shell.py#L10) | função/método |
| `IconData` | [12](../Onda/windows_shell.py#L12) | classe |
| `WindowsShell` | [15](../Onda/windows_shell.py#L15) | classe |
| `WindowsShell.__init__` | [17](../Onda/windows_shell.py#L17) | função/método |
| `WindowsShell.__init__.window_proc` | [31](../Onda/windows_shell.py#L31) | função/método |
| `WindowsShell.theme_icon` | [62](../Onda/windows_shell.py#L62) | função/método |
| `WindowsShell.com` | [85](../Onda/windows_shell.py#L85) | função/método |
| `WindowsShell.data` | [90](../Onda/windows_shell.py#L90) | função/método |
| `WindowsShell.add` | [93](../Onda/windows_shell.py#L93) | função/método |
| `WindowsShell.remove` | [98](../Onda/windows_shell.py#L98) | função/método |
| `WindowsShell.notify` | [101](../Onda/windows_shell.py#L101) | função/método |
| `WindowsShell.progress` | [106](../Onda/windows_shell.py#L106) | função/método |
| `WindowsShell.close` | [113](../Onda/windows_shell.py#L113) | função/método |

</details>

<details>
<summary><code>workflow_status.py</code> — 2 declarações</summary>

[Onda/workflow_status.py](../Onda/workflow_status.py)

Descrição do módulo no fonte: Presentation-only state names; persisted queue identifiers stay unchanged.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `label` | [10](../Onda/workflow_status.py#L10) | função/método |
| `can_act` | [14](../Onda/workflow_status.py#L14) | função/método |

</details>

<details>
<summary><code>youtube_workload.py</code> — 2 declarações</summary>

[Onda/youtube_workload.py](../Onda/youtube_workload.py)

Descrição do módulo no fonte: Identify jobs which share YouTube's request budget.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `uses_youtube` | [5](../Onda/youtube_workload.py#L5) | função/método |
| `uses_youtube.belongs` | [10](../Onda/youtube_workload.py#L10) | função/método |

</details>

### 23.2 Interface PC Qt/QML

<details>
<summary><code>ActionButton.qml</code> — 0 declarações</summary>

[Onda/qml/ActionButton.qml](../Onda/qml/ActionButton.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>AnimatedLyric.qml</code> — 0 declarações</summary>

[Onda/qml/AnimatedLyric.qml](../Onda/qml/AnimatedLyric.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>BandSlider.qml</code> — 0 declarações</summary>

[Onda/qml/BandSlider.qml](../Onda/qml/BandSlider.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>BrandMark.qml</code> — 0 declarações</summary>

[Onda/qml/BrandMark.qml](../Onda/qml/BrandMark.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>Card.qml</code> — 0 declarações</summary>

[Onda/qml/Card.qml](../Onda/qml/Card.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>CardSizeControl.qml</code> — 0 declarações</summary>

[Onda/qml/CardSizeControl.qml](../Onda/qml/CardSizeControl.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>ChoiceBox.qml</code> — 0 declarações</summary>

[Onda/qml/ChoiceBox.qml](../Onda/qml/ChoiceBox.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>ComparisonPopup.qml</code> — 1 declarações</summary>

[Onda/qml/ComparisonPopup.qml](../Onda/qml/ComparisonPopup.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `onComparisonRequested` | [11](../Onda/qml/ComparisonPopup.qml#L11) | função QML/JS |

</details>

<details>
<summary><code>CoverCropPopup.qml</code> — 1 declarações</summary>

[Onda/qml/CoverCropPopup.qml](../Onda/qml/CoverCropPopup.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `onCropRequested` | [12](../Onda/qml/CoverCropPopup.qml#L12) | função QML/JS |

</details>

<details>
<summary><code>DecisionPopup.qml</code> — 2 declarações</summary>

[Onda/qml/DecisionPopup.qml](../Onda/qml/DecisionPopup.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `onChoiceChanged` | [20](../Onda/qml/DecisionPopup.qml#L20) | função QML/JS |
| `reply` | [27](../Onda/qml/DecisionPopup.qml#L27) | função QML/JS |

</details>

<details>
<summary><code>DownloadFormatPopup.qml</code> — 2 declarações</summary>

[Onda/qml/DownloadFormatPopup.qml](../Onda/qml/DownloadFormatPopup.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `reply` | [23](../Onda/qml/DownloadFormatPopup.qml#L23) | função QML/JS |
| `onChoiceChanged` | [27](../Onda/qml/DownloadFormatPopup.qml#L27) | função QML/JS |

</details>

<details>
<summary><code>DownloadsView.qml</code> — 1 declarações</summary>

[Onda/qml/DownloadsView.qml](../Onda/qml/DownloadsView.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `openContext` | [124](../Onda/qml/DownloadsView.qml#L124) | função QML/JS |

</details>



<details>
<summary><code>EffectsQueueDrawer.qml</code> — 6 declarações</summary>

[Onda/qml/EffectsQueueDrawer.qml](../Onda/qml/EffectsQueueDrawer.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `search` | [12](../Onda/qml/EffectsQueueDrawer.qml#L12) | função QML/JS |
| `onOptionsChanged` | [26](../Onda/qml/EffectsQueueDrawer.qml#L26) | função QML/JS |
| `play` | [31](../Onda/qml/EffectsQueueDrawer.qml#L31) | função QML/JS |
| `move` | [35](../Onda/qml/EffectsQueueDrawer.qml#L35) | função QML/JS |
| `remove` | [39](../Onda/qml/EffectsQueueDrawer.qml#L39) | função QML/JS |
| `retry` | [43](../Onda/qml/EffectsQueueDrawer.qml#L43) | função QML/JS |

</details>

<details>
<summary><code>EmptyState.qml</code> — 0 declarações</summary>

[Onda/qml/EmptyState.qml](../Onda/qml/EmptyState.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>EqualizerPopup.qml</code> — 0 declarações</summary>

[Onda/qml/EqualizerPopup.qml](../Onda/qml/EqualizerPopup.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>ImageGalleryPopup.qml</code> — 1 declarações</summary>

[Onda/qml/ImageGalleryPopup.qml](../Onda/qml/ImageGalleryPopup.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `navigate` | [18](../Onda/qml/ImageGalleryPopup.qml#L18) | função QML/JS |

</details>

<details>
<summary><code>JukeboxView.qml</code> — 1 declarações</summary>

[Onda/qml/JukeboxView.qml](../Onda/qml/JukeboxView.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `updateParams` | [166](../Onda/qml/JukeboxView.qml#L166) | função QML/JS |

</details>

<details>
<summary><code>LibraryView.qml</code> — 0 declarações</summary>

[Onda/qml/LibraryView.qml](../Onda/qml/LibraryView.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>LineIcon.qml</code> — 3 declarações</summary>

[Onda/qml/LineIcon.qml](../Onda/qml/LineIcon.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `line` | [13](../Onda/qml/LineIcon.qml#L13) | função QML/JS |
| `path` | [14](../Onda/qml/LineIcon.qml#L14) | função QML/JS |
| `circle` | [15](../Onda/qml/LineIcon.qml#L15) | função QML/JS |

</details>

<details>
<summary><code>LyricsWindow.qml</code> — 0 declarações</summary>

[Onda/qml/LyricsWindow.qml](../Onda/qml/LyricsWindow.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>Main.qml</code> — 0 declarações</summary>

[Onda/qml/Main.qml](../Onda/qml/Main.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>MicrophoneButton.qml</code> — 0 declarações</summary>

[Onda/qml/MicrophoneButton.qml](../Onda/qml/MicrophoneButton.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>MiniPlayer.qml</code> — 2 declarações</summary>

[Onda/qml/MiniPlayer.qml](../Onda/qml/MiniPlayer.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `openPlayer` | [53](../Onda/qml/MiniPlayer.qml#L53) | função QML/JS |
| `restoreMain` | [54](../Onda/qml/MiniPlayer.qml#L54) | função QML/JS |

</details>

<details>
<summary><code>OndaMenuItem.qml</code> — 0 declarações</summary>

[Onda/qml/OndaMenuItem.qml](../Onda/qml/OndaMenuItem.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>OndaProgressBar.qml</code> — 0 declarações</summary>

[Onda/qml/OndaProgressBar.qml](../Onda/qml/OndaProgressBar.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>OndaSlider.qml</code> — 0 declarações</summary>

[Onda/qml/OndaSlider.qml](../Onda/qml/OndaSlider.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>OndaSwitch.qml</code> — 0 declarações</summary>

[Onda/qml/OndaSwitch.qml](../Onda/qml/OndaSwitch.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>OndaTextArea.qml</code> — 0 declarações</summary>

[Onda/qml/OndaTextArea.qml](../Onda/qml/OndaTextArea.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>OndaTextField.qml</code> — 0 declarações</summary>

[Onda/qml/OndaTextField.qml](../Onda/qml/OndaTextField.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>OptionField.qml</code> — 2 declarações</summary>

[Onda/qml/OptionField.qml](../Onda/qml/OptionField.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `save` | [14](../Onda/qml/OptionField.qml#L14) | função QML/JS |
| `restoreTime` | [45](../Onda/qml/OptionField.qml#L45) | função QML/JS |

</details>

<details>
<summary><code>PlatformBadge.qml</code> — 0 declarações</summary>

[Onda/qml/PlatformBadge.qml](../Onda/qml/PlatformBadge.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>PlaybackButton.qml</code> — 0 declarações</summary>

[Onda/qml/PlaybackButton.qml](../Onda/qml/PlaybackButton.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>QueueDestinationMenu.qml</code> — 0 declarações</summary>

[Onda/qml/QueueDestinationMenu.qml](../Onda/qml/QueueDestinationMenu.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>QueueDragHandle.qml</code> — 6 declarações</summary>

[Onda/qml/QueueDragHandle.qml](../Onda/qml/QueueDragHandle.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `interactiveAt` | [34](../Onda/qml/QueueDragHandle.qml#L34) | função QML/JS |
| `begin` | [42](../Onda/qml/QueueDragHandle.qml#L42) | função QML/JS |
| `update` | [45](../Onda/qml/QueueDragHandle.qml#L45) | função QML/JS |
| `locateTarget` | [54](../Onda/qml/QueueDragHandle.qml#L54) | função QML/JS |
| `finish` | [64](../Onda/qml/QueueDragHandle.qml#L64) | função QML/JS |
| `cancel` | [71](../Onda/qml/QueueDragHandle.qml#L71) | função QML/JS |

</details>

<details>
<summary><code>ResetPopup.qml</code> — 0 declarações</summary>

[Onda/qml/ResetPopup.qml](../Onda/qml/ResetPopup.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>RoundedArtwork.qml</code> — 5 declarações</summary>

[Onda/qml/RoundedArtwork.qml](../Onda/qml/RoundedArtwork.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `reload` | [18](../Onda/qml/RoundedArtwork.qml#L18) | função QML/JS |
| `onSourceChanged` | [36](../Onda/qml/RoundedArtwork.qml#L36) | função QML/JS |
| `onCornerRadiusChanged` | [36](../Onda/qml/RoundedArtwork.qml#L36) | função QML/JS |
| `onPaintedWidthChanged` | [37](../Onda/qml/RoundedArtwork.qml#L37) | função QML/JS |
| `onPaintedHeightChanged` | [37](../Onda/qml/RoundedArtwork.qml#L37) | função QML/JS |

</details>

<details>
<summary><code>SegmentButton.qml</code> — 0 declarações</summary>

[Onda/qml/SegmentButton.qml](../Onda/qml/SegmentButton.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>SettingsPopup.qml</code> — 0 declarações</summary>

[Onda/qml/SettingsPopup.qml](../Onda/qml/SettingsPopup.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>Shell.qml</code> — 6 declarações</summary>

[Onda/qml/Shell.qml](../Onda/qml/Shell.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `onLyricsRequested` | [13](../Onda/qml/Shell.qml#L13) | função QML/JS |
| `onVisibilityChanged` | [233](../Onda/qml/Shell.qml#L233) | função QML/JS |
| `onSettingsRequested` | [276](../Onda/qml/Shell.qml#L276) | função QML/JS |
| `onSettingsCategoryRequested` | [277](../Onda/qml/Shell.qml#L277) | função QML/JS |
| `onShortcutsRequested` | [278](../Onda/qml/Shell.qml#L278) | função QML/JS |
| `onMessage` | [279](../Onda/qml/Shell.qml#L279) | função QML/JS |

</details>

<details>
<summary><code>ShortcutRecorder.qml</code> — 0 declarações</summary>

[Onda/qml/ShortcutRecorder.qml](../Onda/qml/ShortcutRecorder.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>ShortcutsPopup.qml</code> — 0 declarações</summary>

[Onda/qml/ShortcutsPopup.qml](../Onda/qml/ShortcutsPopup.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>Sidebar.qml</code> — 0 declarações</summary>

[Onda/qml/Sidebar.qml](../Onda/qml/Sidebar.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>TaskButton.qml</code> — 0 declarações</summary>

[Onda/qml/TaskButton.qml](../Onda/qml/TaskButton.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>TimerButton.qml</code> — 0 declarações</summary>

[Onda/qml/TimerButton.qml](../Onda/qml/TimerButton.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>TimerPopup.qml</code> — 0 declarações</summary>

[Onda/qml/TimerPopup.qml](../Onda/qml/TimerPopup.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

<details>
<summary><code>ToolStatusPanel.qml</code> — 1 declarações</summary>

[Onda/qml/ToolStatusPanel.qml](../Onda/qml/ToolStatusPanel.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `dateText` | [12](../Onda/qml/ToolStatusPanel.qml#L12) | função QML/JS |

</details>

<details>
<summary><code>ToolView.qml</code> — 1 declarações</summary>

[Onda/qml/ToolView.qml](../Onda/qml/ToolView.qml)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `summary` | [184](../Onda/qml/ToolView.qml#L184) | função QML/JS |

</details>

<details>
<summary><code>WorkspaceView.qml</code> — 0 declarações</summary>

[Onda/qml/WorkspaceView.qml](../Onda/qml/WorkspaceView.qml)

Componente declarativo sem função nomeada extraída; consultar o arquivo.

</details>

### 23.3 Android: Compose, serviços e infraestrutura Kotlin

<details>
<summary><code>Accessibility.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/Accessibility.kt](../Android/app/src/main/java/br/com/onda/mobile/Accessibility.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `a11yLabel` | [8](../Android/app/src/main/java/br/com/onda/mobile/Accessibility.kt#L8) | função |
| `AccessibleSymbol` | [15](../Android/app/src/main/java/br/com/onda/mobile/Accessibility.kt#L15) | função |
| `a11yState` | [20](../Android/app/src/main/java/br/com/onda/mobile/Accessibility.kt#L20) | função |

</details>

<details>
<summary><code>AdvancedControls.kt</code> — 8 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadConcurrencyOptions` | [20](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L20) | função |
| `AdvancedDownloadOptions` | [26](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L26) | função |
| `PreferenceTransfer` | [52](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L52) | função |
| `AppUpdateControls` | [73](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L73) | função |
| `AudioFileEditor` | [118](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L118) | função |
| `config` | [135](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L135) | função |
| `finish` | [137](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L137) | função |
| `ScheduleTimeButton` | [195](../Android/app/src/main/java/br/com/onda/mobile/AdvancedControls.kt#L195) | função |

</details>

<details>
<summary><code>AlbumGlass.kt</code> — 7 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `albumDominantColor` | [29](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L29) | função |
| `AlbumGlassColors` | [42](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L42) | class |
| `albumGlassColors` | [43](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L43) | função |
| `AlbumGlass` | [51](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L51) | função |
| `rememberAlbumAccent` | [74](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L74) | função |
| `albumLyricsColors` | [94](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L94) | função |
| `rememberLyricsColors` | [101](../Android/app/src/main/java/br/com/onda/mobile/AlbumGlass.kt#L101) | função |

</details>

<details>
<summary><code>AndroidPlaybackSurface.kt</code> — 7 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `AndroidPlaybackSurface` | [25](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L25) | função |
| `toggle` | [82](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L82) | função |
| `previous` | [83](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L83) | função |
| `next` | [84](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L84) | função |
| `seek` | [85](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L85) | função |
| `openQueue` | [89](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L89) | função |
| `cover` | [90](../Android/app/src/main/java/br/com/onda/mobile/AndroidPlaybackSurface.kt#L90) | função |

</details>

<details>
<summary><code>AndroidShell.kt</code> — 11 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `OndaIcon` | [49](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L49) | função |
| `line` | [53](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L53) | função |
| `path` | [54](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L54) | função |
| `OndaAppBar` | [127](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L127) | função |
| `mainDestinations` | [137](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L137) | função |
| `pageSwipeExclusion` | [141](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L141) | função |
| `SwipePageHost` | [149](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L149) | função |
| `OndaBottomNavigation` | [189](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L189) | função |
| `OndaMiniPlayer` | [201](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L201) | função |
| `MorePage` | [248](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L248) | função |
| `MoreRow` | [267](../Android/app/src/main/java/br/com/onda/mobile/AndroidShell.kt#L267) | função |

</details>

<details>
<summary><code>AppearanceWindow.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/AppearanceWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/AppearanceWindow.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `AppearanceWindow` | [18](../Android/app/src/main/java/br/com/onda/mobile/AppearanceWindow.kt#L18) | função |
| `put` | [20](../Android/app/src/main/java/br/com/onda/mobile/AppearanceWindow.kt#L20) | função |

</details>

<details>
<summary><code>AudioReplacement.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/AudioReplacement.kt](../Android/app/src/main/java/br/com/onda/mobile/AudioReplacement.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `audioDigest` | [11](../Android/app/src/main/java/br/com/onda/mobile/AudioReplacement.kt#L11) | função |
| `replaceAudioOriginal` | [19](../Android/app/src/main/java/br/com/onda/mobile/AudioReplacement.kt#L19) | função |

</details>

<details>
<summary><code>BatchMetadataEditor.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/BatchMetadataEditor.kt](../Android/app/src/main/java/br/com/onda/mobile/BatchMetadataEditor.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `BatchMetadataEditor` | [28](../Android/app/src/main/java/br/com/onda/mobile/BatchMetadataEditor.kt#L28) | função |
| `apply` | [50](../Android/app/src/main/java/br/com/onda/mobile/BatchMetadataEditor.kt#L50) | função |

</details>

<details>
<summary><code>BlackTheme.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/BlackTheme.kt](../Android/app/src/main/java/br/com/onda/mobile/BlackTheme.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `pureBlackSurfaces` | [6](../Android/app/src/main/java/br/com/onda/mobile/BlackTheme.kt#L6) | função |
| `ondaDialogContainerColor` | [22](../Android/app/src/main/java/br/com/onda/mobile/BlackTheme.kt#L22) | função |
| `highContrastScheme` | [27](../Android/app/src/main/java/br/com/onda/mobile/BlackTheme.kt#L27) | função |

</details>

<details>
<summary><code>BrandMark.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/BrandMark.kt](../Android/app/src/main/java/br/com/onda/mobile/BrandMark.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `OndaBrandMark` | [18](../Android/app/src/main/java/br/com/onda/mobile/BrandMark.kt#L18) | função |

</details>

<details>
<summary><code>CacheControls.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/CacheControls.kt](../Android/app/src/main/java/br/com/onda/mobile/CacheControls.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CacheControls` | [14](../Android/app/src/main/java/br/com/onda/mobile/CacheControls.kt#L14) | função |
| `readSize` | [24](../Android/app/src/main/java/br/com/onda/mobile/CacheControls.kt#L24) | função |
| `clear` | [37](../Android/app/src/main/java/br/com/onda/mobile/CacheControls.kt#L37) | função |

</details>

<details>
<summary><code>CardMetadata.kt</code> — 5 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt](../Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `onSecondaryClick` | [10](../Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt#L10) | função |
| `rememberCardMetadata` | [16](../Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt#L16) | função |
| `ReleaseDateLabel` | [22](../Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt#L22) | função |
| `openRecordLink` | [27](../Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt#L27) | função |
| `copyRecordLink` | [31](../Android/app/src/main/java/br/com/onda/mobile/CardMetadata.kt#L31) | função |

</details>

<details>
<summary><code>ChoiceWindow.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ChoiceWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/ChoiceWindow.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ChoiceWindow` | [17](../Android/app/src/main/java/br/com/onda/mobile/ChoiceWindow.kt#L17) | função |

</details>

<details>
<summary><code>ClipboardLinks.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ClipboardLinks.kt](../Android/app/src/main/java/br/com/onda/mobile/ClipboardLinks.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ClipboardDownloadPrompt` | [16](../Android/app/src/main/java/br/com/onda/mobile/ClipboardLinks.kt#L16) | função |
| `check` | [29](../Android/app/src/main/java/br/com/onda/mobile/ClipboardLinks.kt#L29) | função |

</details>

<details>
<summary><code>CollectionsLibrary.kt</code> — 9 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CollectionsLibrary` | [13](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L13) | object |
| `file` | [15](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L15) | função |
| `readLocked` | [16](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L16) | função |
| `writeLocked` | [22](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L22) | função |
| `read` | [27](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L27) | função |
| `write` | [28](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L28) | função |
| `save` | [29](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L29) | função |
| `remove` | [33](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L33) | função |
| `identity` | [37](../Android/app/src/main/java/br/com/onda/mobile/CollectionsLibrary.kt#L37) | função |

</details>

<details>
<summary><code>CollectionsPage.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/CollectionsPage.kt](../Android/app/src/main/java/br/com/onda/mobile/CollectionsPage.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CollectionsPage` | [28](../Android/app/src/main/java/br/com/onda/mobile/CollectionsPage.kt#L28) | função |
| `chosen` | [79](../Android/app/src/main/java/br/com/onda/mobile/CollectionsPage.kt#L79) | função |
| `enqueue` | [80](../Android/app/src/main/java/br/com/onda/mobile/CollectionsPage.kt#L80) | função |

</details>

<details>
<summary><code>CoverCropper.kt</code> — 5 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `loadCoverBitmap` | [37](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt#L37) | função |
| `coverOffset` | [61](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt#L61) | função |
| `saveCoverCrop` | [67](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt#L67) | função |
| `CoverCropper` | [79](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt#L79) | função |
| `move` | [106](../Android/app/src/main/java/br/com/onda/mobile/CoverCropper.kt#L106) | função |

</details>

<details>
<summary><code>DailyUse.kt</code> — 16 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueGate` | [20](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L20) | class |
| `queueGate` | [21](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L21) | função |
| `interruptForGate` | [26](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L26) | função |
| `interruptedDownload` | [27](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L27) | função |
| `notificationActions` | [28](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L28) | função |
| `QueueNetwork` | [30](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L30) | class |
| `update` | [35](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L35) | função |
| `onAvailable` | [42](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L42) | função |
| `onCapabilitiesChanged` | [43](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L43) | função |
| `onLost` | [44](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L44) | função |
| `gate` | [48](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L48) | função |
| `close` | [52](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L52) | função |
| `openQueueIntent` | [55](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L55) | função |
| `queueFinished` | [57](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L57) | função |
| `WifiDownloadControls` | [84](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L84) | função |
| `DailyDownloadControls` | [93](../Android/app/src/main/java/br/com/onda/mobile/DailyUse.kt#L93) | função |

</details>

<details>
<summary><code>DownloadBatchFiles.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadBatchFiles.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadBatchFiles.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadBatchFiles` | [11](../Android/app/src/main/java/br/com/onda/mobile/DownloadBatchFiles.kt#L11) | object |
| `intent` | [12](../Android/app/src/main/java/br/com/onda/mobile/DownloadBatchFiles.kt#L12) | função |
| `consume` | [21](../Android/app/src/main/java/br/com/onda/mobile/DownloadBatchFiles.kt#L21) | função |
| `discard` | [29](../Android/app/src/main/java/br/com/onda/mobile/DownloadBatchFiles.kt#L29) | função |

</details>

<details>
<summary><code>DownloadDefaults.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadDefaults.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadDefaults.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `effectiveDownloadOptions` | [6](../Android/app/src/main/java/br/com/onda/mobile/DownloadDefaults.kt#L6) | função |

</details>

<details>
<summary><code>DownloadFeedback.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadFeedback.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadFeedback.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `failureAdvice` | [5](../Android/app/src/main/java/br/com/onda/mobile/DownloadFeedback.kt#L5) | função |
| `downloadDetail` | [14](../Android/app/src/main/java/br/com/onda/mobile/DownloadFeedback.kt#L14) | função |

</details>

<details>
<summary><code>DownloadRequests.kt</code> — 9 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadRequest` | [5](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L5) | class |
| `DownloadRequests` | [7](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L7) | class |
| `submit` | [9](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L9) | função |
| `poll` | [12](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L12) | função |
| `hasPending` | [13](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L13) | função |
| `clear` | [14](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L14) | função |
| `DownloadScope` | [17](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L17) | class |
| `include` | [20](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L20) | função |
| `accepts` | [23](../Android/app/src/main/java/br/com/onda/mobile/DownloadRequests.kt#L23) | função |

</details>

<details>
<summary><code>DownloadSchedule.kt</code> — 5 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `scheduleAllowed` | [12](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt#L12) | função |
| `DownloadSchedule` | [20](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt#L20) | object |
| `configure` | [22](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt#L22) | função |
| `ScheduledDownloadWorker` | [37](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt#L37) | class |
| `doWork` | [38](../Android/app/src/main/java/br/com/onda/mobile/DownloadSchedule.kt#L38) | função |

</details>

<details>
<summary><code>DownloadService.kt</code> — 13 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `downloadNotification` | [10](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L10) | função |
| `refreshDownloadNotification` | [30](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L30) | função |
| `DownloadService` | [42](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L42) | class |
| `power` | [46](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L46) | função |
| `onBind` | [52](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L52) | função |
| `onStartCommand` | [53](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L53) | função |
| `launchWorker` | [70](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L70) | função |
| `onTimeout` | [97](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L97) | função |
| `onDestroy` | [98](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L98) | função |
| `start` | [100](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L100) | função |
| `batch` | [101](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L101) | função |
| `control` | [102](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L102) | função |
| `stop` | [103](../Android/app/src/main/java/br/com/onda/mobile/DownloadService.kt#L103) | função |

</details>

<details>
<summary><code>DownloadsHome.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DownloadsHome.kt](../Android/app/src/main/java/br/com/onda/mobile/DownloadsHome.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadsHome` | [34](../Android/app/src/main/java/br/com/onda/mobile/DownloadsHome.kt#L34) | função |
| `DownloadsOrganization` | [127](../Android/app/src/main/java/br/com/onda/mobile/DownloadsHome.kt#L127) | função |
| `DownloadSummaryCard` | [146](../Android/app/src/main/java/br/com/onda/mobile/DownloadsHome.kt#L146) | função |

</details>

<details>
<summary><code>DuplicateLinks.kt</code> — 5 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt](../Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `sourceKey` | [8](../Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt#L8) | função |
| `jobSource` | [38](../Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt#L38) | função |
| `duplicateJob` | [49](../Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt#L49) | função |
| `QueueDuplicateKey` | [57](../Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt#L57) | class |
| `queueDuplicateKey` | [58](../Android/app/src/main/java/br/com/onda/mobile/DuplicateLinks.kt#L58) | função |

</details>

<details>
<summary><code>EffectsPlaybackBar.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `EffectsTimeline` | [14](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt#L14) | object |
| `position` | [15](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt#L15) | função |
| `remaining` | [17](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt#L17) | função |
| `EffectsPlaybackBar` | [21](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackBar.kt#L21) | função |

</details>

<details>
<summary><code>EffectsPlaybackService.kt</code> — 20 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `EffectsMediaState` | [17](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L17) | class |
| `EffectsPlaybackRuntime` | [24](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L24) | object |
| `publish` | [28](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L28) | função |
| `clear` | [29](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L29) | função |
| `EffectsPlaybackService` | [32](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L32) | class |
| `start` | [34](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L34) | função |
| `resumePlayback` | [42](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L42) | função |
| `onBind` | [47](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L47) | função |
| `onCreate` | [48](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L48) | função |
| `onPlay` | [54](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L54) | função |
| `onPause` | [55](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L55) | função |
| `onStop` | [56](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L56) | função |
| `onSeekTo` | [57](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L57) | função |
| `onSkipToPrevious` | [58](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L58) | função |
| `onSkipToNext` | [59](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L59) | função |
| `action` | [76](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L76) | função |
| `notification` | [77](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L77) | função |
| `onStartCommand` | [87](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L87) | função |
| `onTaskRemoved` | [92](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L92) | função |
| `onDestroy` | [93](../Android/app/src/main/java/br/com/onda/mobile/EffectsPlaybackService.kt#L93) | função |

</details>

<details>
<summary><code>EffectsQueuePanel.kt</code> — 9 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `EffectsArtwork` | [33](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L33) | função |
| `EffectsTrackInformation` | [43](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L43) | função |
| `PlaybackQueueRow` | [60](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L60) | função |
| `EffectsQueuePanel` | [94](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L94) | função |
| `EffectsQueueDrawer` | [132](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L132) | função |
| `SearchTrackInformation` | [140](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L140) | função |
| `PlaybackQueueSearch` | [153](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L153) | função |
| `search` | [163](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L163) | função |
| `PlaybackSearchResult` | [190](../Android/app/src/main/java/br/com/onda/mobile/EffectsQueuePanel.kt#L190) | função |

</details>

<details>
<summary><code>FailureSummary.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/FailureSummary.kt](../Android/app/src/main/java/br/com/onda/mobile/FailureSummary.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `repairedFailureConfig` | [7](../Android/app/src/main/java/br/com/onda/mobile/FailureSummary.kt#L7) | função |
| `failureReportText` | [19](../Android/app/src/main/java/br/com/onda/mobile/FailureSummary.kt#L19) | função |
| `validFailureCatalogUrl` | [29](../Android/app/src/main/java/br/com/onda/mobile/FailureSummary.kt#L29) | função |
| `finishedFailureIds` | [31](../Android/app/src/main/java/br/com/onda/mobile/FailureSummary.kt#L31) | função |

</details>

<details>
<summary><code>FailureSummaryWindow.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/FailureSummaryWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/FailureSummaryWindow.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `FailureSummaryWindow` | [20](../Android/app/src/main/java/br/com/onda/mobile/FailureSummaryWindow.kt#L20) | função |
| `search` | [44](../Android/app/src/main/java/br/com/onda/mobile/FailureSummaryWindow.kt#L44) | função |

</details>

<details>
<summary><code>GalleryGestures.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/GalleryGestures.kt](../Android/app/src/main/java/br/com/onda/mobile/GalleryGestures.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `gallerySwipe` | [14](../Android/app/src/main/java/br/com/onda/mobile/GalleryGestures.kt#L14) | função |

</details>

<details>
<summary><code>HistoryDetails.kt</code> — 5 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `HistoryDetails` | [9](../Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt#L9) | class |
| `readHistoryDetails` | [11](../Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt#L11) | função |
| `field` | [15](../Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt#L15) | função |
| `invalidateHistoryDetails` | [46](../Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt#L46) | função |
| `cachedHistoryDetails` | [50](../Android/app/src/main/java/br/com/onda/mobile/HistoryDetails.kt#L50) | função |

</details>

<details>
<summary><code>HistoryFolders.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `externalFolderUri` | [15](../Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt#L15) | função |
| `historyFolderUri` | [22](../Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt#L22) | função |
| `historyFolderPicker` | [57](../Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt#L57) | função |
| `openHistoryFolder` | [64](../Android/app/src/main/java/br/com/onda/mobile/HistoryFolders.kt#L64) | função |

</details>

<details>
<summary><code>HistoryImageGallery.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryImageGallery.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryImageGallery.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `HistoryImageGallery` | [16](../Android/app/src/main/java/br/com/onda/mobile/HistoryImageGallery.kt#L16) | função |

</details>

<details>
<summary><code>HistoryOrigin.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryOrigin.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryOrigin.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `historyOrigin` | [3](../Android/app/src/main/java/br/com/onda/mobile/HistoryOrigin.kt#L3) | função |

</details>

<details>
<summary><code>HistoryPage.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryPage.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryPage.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `HistoryPage` | [21](../Android/app/src/main/java/br/com/onda/mobile/HistoryPage.kt#L21) | função |

</details>

<details>
<summary><code>HistoryRows.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryRows.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryRows.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `insertHistoryRow` | [4](../Android/app/src/main/java/br/com/onda/mobile/HistoryRows.kt#L4) | função |

</details>

<details>
<summary><code>HistoryToolCard.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/HistoryToolCard.kt](../Android/app/src/main/java/br/com/onda/mobile/HistoryToolCard.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `historyKind` | [27](../Android/app/src/main/java/br/com/onda/mobile/HistoryToolCard.kt#L27) | função |
| `historyDay` | [35](../Android/app/src/main/java/br/com/onda/mobile/HistoryToolCard.kt#L35) | função |
| `HistoryToolCard` | [43](../Android/app/src/main/java/br/com/onda/mobile/HistoryToolCard.kt#L43) | função |
| `action` | [70](../Android/app/src/main/java/br/com/onda/mobile/HistoryToolCard.kt#L70) | função |

</details>

<details>
<summary><code>ImageSourcePicker.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt](../Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `galleryImageIntent` | [21](../Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt#L21) | função |
| `photoPermissions` | [38](../Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt#L38) | função |
| `rememberImageSourcePicker` | [45](../Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt#L45) | função |
| `openGallery` | [57](../Android/app/src/main/java/br/com/onda/mobile/ImageSourcePicker.kt#L57) | função |

</details>

<details>
<summary><code>ImagesPage.kt</code> — 6 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ImagesPage` | [20](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt#L20) | função |
| `imageConfig` | [28](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt#L28) | função |
| `previewOptions` | [31](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt#L31) | função |
| `loadPreview` | [33](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt#L33) | função |
| `ImageOptions` | [65](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt#L65) | função |
| `put` | [68](../Android/app/src/main/java/br/com/onda/mobile/ImagesPage.kt#L68) | função |

</details>

<details>
<summary><code>InAppUpdate.kt</code> — 11 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `UpdateDownload` | [13](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L13) | class |
| `pollUpdateDownload` | [20](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L20) | função |
| `InAppUpdate` | [34](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L34) | class |
| `officialUrl` | [38](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L38) | função |
| `start` | [43](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L43) | função |
| `cancel` | [56](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L56) | função |
| `state` | [62](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L62) | função |
| `validate` | [71](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L71) | função |
| `validateMetadata` | [79](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L79) | função |
| `signatures` | [83](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L83) | função |
| `install` | [88](../Android/app/src/main/java/br/com/onda/mobile/InAppUpdate.kt#L88) | função |

</details>

<details>
<summary><code>InterfaceFonts.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/InterfaceFonts.kt](../Android/app/src/main/java/br/com/onda/mobile/InterfaceFonts.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalizeInterfaceFont` | [18](../Android/app/src/main/java/br/com/onda/mobile/InterfaceFonts.kt#L18) | função |
| `interfaceTypography` | [25](../Android/app/src/main/java/br/com/onda/mobile/InterfaceFonts.kt#L25) | função |

</details>

<details>
<summary><code>Jukebox.kt</code> — 49 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxState` | [51](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L51) | class |
| `JukeboxController` | [53](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L53) | class |
| `setVolume` | [67](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L67) | função |
| `applyGain` | [68](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L68) | função |
| `previousTrack` | [75](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L75) | função |
| `nextTrack` | [76](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L76) | função |
| `moveQueued` | [84](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L84) | função |
| `clearPlaybackQueue` | [85](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L85) | função |
| `gradual` | [86](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L86) | função |
| `setTimer` | [87](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L87) | função |
| `preparationWindow` | [124](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L124) | função |
| `trimPreparedModels` | [135](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L135) | função |
| `updateQueue` | [139](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L139) | função |
| `prepareConfig` | [142](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L142) | função |
| `startQueuePreparation` | [146](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L146) | função |
| `enqueue` | [181](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L181) | função |
| `retryQueued` | [185](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L185) | função |
| `removeQueued` | [186](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L186) | função |
| `TrackSwitch` | [197](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L197) | class |
| `transitionSeconds` | [200](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L200) | função |
| `playQueued` | [201](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L201) | função |
| `searchQueue` | [222](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L222) | função |
| `resolveQueueInput` | [225](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L225) | função |
| `seek` | [235](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L235) | função |
| `onReceive` | [246](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L246) | função |
| `releaseNoisy` | [247](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L247) | função |
| `call` | [249](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L249) | função |
| `prepare` | [255](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L255) | função |
| `savePlaybackSession` | [284](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L284) | função |
| `cancelSearch` | [304](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L304) | função |
| `search` | [309](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L309) | função |
| `pause` | [327](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L327) | função |
| `playPause` | [328](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L328) | função |
| `progress` | [362](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L362) | função |
| `announce` | [367](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L367) | função |
| `stop` | [430](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L430) | função |
| `close` | [441](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L441) | função |
| `PlaybackPage` | [444](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L444) | função |
| `JukeboxPage` | [466](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L466) | função |
| `JukeboxTimerDialog` | [550](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L550) | função |
| `JukeboxQueueDialog` | [576](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L576) | função |
| `search` | [585](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L585) | função |
| `JukeboxGraph` | [619](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L619) | função |
| `point` | [639](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L639) | função |
| `JukeboxConnections` | [668](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L668) | função |
| `point` | [672](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L672) | função |
| `curves` | [673](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L673) | função |
| `jukeboxVisibleLinks` | [687](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L687) | função |
| `jukeboxGraphColors` | [703](../Android/app/src/main/java/br/com/onda/mobile/Jukebox.kt#L703) | função |

</details>

<details>
<summary><code>JukeboxEqualizerDialog.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/JukeboxEqualizerDialog.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxEqualizerDialog.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxEqualizerDialog` | [21](../Android/app/src/main/java/br/com/onda/mobile/JukeboxEqualizerDialog.kt#L21) | função |
| `save` | [35](../Android/app/src/main/java/br/com/onda/mobile/JukeboxEqualizerDialog.kt#L35) | função |
| `close` | [41](../Android/app/src/main/java/br/com/onda/mobile/JukeboxEqualizerDialog.kt#L41) | função |

</details>

<details>
<summary><code>JukeboxLyricsButton.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/JukeboxLyricsButton.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxLyricsButton.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxLyricsButton` | [6](../Android/app/src/main/java/br/com/onda/mobile/JukeboxLyricsButton.kt#L6) | função |

</details>

<details>
<summary><code>JukeboxService.kt</code> — 16 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxRuntime` | [20](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L20) | object |
| `get` | [22](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L22) | função |
| `JukeboxService` | [25](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L25) | class |
| `onBind` | [34](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L34) | função |
| `onCreate` | [35](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L35) | função |
| `onPlay` | [42](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L42) | função |
| `onPause` | [43](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L43) | função |
| `onStop` | [44](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L44) | função |
| `onSkipToPrevious` | [45](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L45) | função |
| `onSkipToNext` | [46](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L46) | função |
| `action` | [84](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L84) | função |
| `notification` | [85](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L85) | função |
| `refresh` | [97](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L97) | função |
| `onStartCommand` | [105](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L105) | função |
| `onTaskRemoved` | [109](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L109) | função |
| `onDestroy` | [110](../Android/app/src/main/java/br/com/onda/mobile/JukeboxService.kt#L110) | função |

</details>

<details>
<summary><code>JukeboxTimer.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt](../Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `JukeboxTimerProgress` | [4](../Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt#L4) | class |
| `advance` | [8](../Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt#L8) | função |
| `restart` | [13](../Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt#L13) | função |
| `jukeboxJumpBlend` | [17](../Android/app/src/main/java/br/com/onda/mobile/JukeboxTimer.kt#L17) | função |

</details>

<details>
<summary><code>LauncherIcons.kt</code> — 15 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LauncherIcons` | [22](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L22) | object |
| `initialize` | [46](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L46) | função |
| `onActivityStarted` | [50](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L50) | função |
| `onActivityStopped` | [57](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L57) | função |
| `onActivityCreated` | [66](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L66) | função |
| `onActivityResumed` | [67](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L67) | função |
| `onActivityPaused` | [68](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L68) | função |
| `onActivitySaveInstanceState` | [69](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L69) | função |
| `onActivityDestroyed` | [70](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L70) | função |
| `aliasFor` | [77](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L77) | função |
| `enabledAliases` | [85](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L85) | função |
| `sync` | [89](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L89) | função |
| `applyPending` | [96](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L96) | função |
| `drawable` | [124](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L124) | função |
| `updateTaskIcon` | [130](../Android/app/src/main/java/br/com/onda/mobile/LauncherIcons.kt#L130) | função |

</details>

<details>
<summary><code>LayoutSpacing.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LayoutSpacing.kt](../Android/app/src/main/java/br/com/onda/mobile/LayoutSpacing.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalizedSpacing` | [8](../Android/app/src/main/java/br/com/onda/mobile/LayoutSpacing.kt#L8) | função |
| `SpacingValues` | [9](../Android/app/src/main/java/br/com/onda/mobile/LayoutSpacing.kt#L9) | class |
| `spacingValues` | [10](../Android/app/src/main/java/br/com/onda/mobile/LayoutSpacing.kt#L10) | função |
| `LayoutSpacing` | [18](../Android/app/src/main/java/br/com/onda/mobile/LayoutSpacing.kt#L18) | object |

</details>

<details>
<summary><code>LicensesWindow.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LicensesWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/LicensesWindow.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LicenseNotice` | [18](../Android/app/src/main/java/br/com/onda/mobile/LicensesWindow.kt#L18) | class |
| `LicensesWindow` | [20](../Android/app/src/main/java/br/com/onda/mobile/LicensesWindow.kt#L20) | função |
| `closePage` | [39](../Android/app/src/main/java/br/com/onda/mobile/LicensesWindow.kt#L39) | função |

</details>

<details>
<summary><code>Localization.kt</code> — 12 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/Localization.kt](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `normalizedLanguage` | [20](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L20) | função |
| `UiTemplate` | [22](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L22) | class |
| `UiCatalog` | [24](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L24) | object |
| `errors` | [26](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L26) | função |
| `templates` | [35](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L35) | função |
| `get` | [50](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L50) | função |
| `translateUi` | [57](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L57) | função |
| `translateError` | [82](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L82) | função |
| `LocalizedTheme` | [88](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L88) | função |
| `UiText` | [94](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L94) | função |
| `UiErrorText` | [104](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L104) | função |
| `uiExceptionMessage` | [112](../Android/app/src/main/java/br/com/onda/mobile/Localization.kt#L112) | função |

</details>

<details>
<summary><code>LyricAnimation.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LyricAnimation.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricAnimation.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `lyricAnimation` | [14](../Android/app/src/main/java/br/com/onda/mobile/LyricAnimation.kt#L14) | função |

</details>

<details>
<summary><code>LyricTimeline.kt</code> — 6 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `lyricPlainText` | [4](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt#L4) | função |
| `LyricWord` | [5](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt#L5) | class |
| `LyricVerse` | [6](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt#L6) | class |
| `LyricTimeline` | [9](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt#L9) | class |
| `activeIndex` | [20](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt#L20) | função |
| `lyricActiveIndex` | [28](../Android/app/src/main/java/br/com/onda/mobile/LyricTimeline.kt#L28) | função |

</details>

<details>
<summary><code>LyricsButton.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LyricsButton.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricsButton.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LyricsButton` | [31](../Android/app/src/main/java/br/com/onda/mobile/LyricsButton.kt#L31) | função |
| `applyLyrics` | [49](../Android/app/src/main/java/br/com/onda/mobile/LyricsButton.kt#L49) | função |

</details>

<details>
<summary><code>LyricsPreviewCard.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/LyricsPreviewCard.kt](../Android/app/src/main/java/br/com/onda/mobile/LyricsPreviewCard.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `LyricsPreviewCard` | [15](../Android/app/src/main/java/br/com/onda/mobile/LyricsPreviewCard.kt#L15) | função |

</details>

<details>
<summary><code>MainActivity.kt</code> — 30 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MainActivity` | [49](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L49) | class |
| `onCreate` | [51](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L51) | função |
| `onStop` | [57](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L57) | função |
| `onNewIntent` | [58](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L58) | função |
| `dispatchKeyEvent` | [61](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L61) | função |
| `receive` | [67](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L67) | função |
| `OndaApp` | [83](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L83) | função |
| `tabLabel` | [215](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L215) | função |
| `PageTitle` | [217](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L217) | função |
| `Select` | [223](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L223) | função |
| `Toggle` | [233](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L233) | função |
| `FormatOptions` | [241](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L241) | função |
| `put` | [244](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L244) | função |
| `SearchPage` | [262](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L262) | função |
| `submitSearch` | [285](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L285) | função |
| `displayReleaseDate` | [372](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L372) | função |
| `TrackCard` | [384](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L384) | função |
| `LinksPage` | [434](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L434) | função |
| `add` | [440](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L440) | função |
| `historySupportsEffects` | [460](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L460) | função |
| `mediaClock` | [465](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L465) | função |
| `PlayerControls` | [467](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L467) | função |
| `EffectsPage` | [481](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L481) | função |
| `seek` | [500](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L500) | função |
| `toggle` | [501](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L501) | função |
| `moveTrack` | [502](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L502) | função |
| `effectName` | [528](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L528) | função |
| `searchEffects` | [533](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L533) | função |
| `load` | [552](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L552) | função |
| `importedAudioName` | [599](../Android/app/src/main/java/br/com/onda/mobile/MainActivity.kt#L599) | função |

</details>

<details>
<summary><code>MediaMimeType.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/MediaMimeType.kt](../Android/app/src/main/java/br/com/onda/mobile/MediaMimeType.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `mediaMimeType` | [6](../Android/app/src/main/java/br/com/onda/mobile/MediaMimeType.kt#L6) | função |

</details>

<details>
<summary><code>MetadataPage.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/MetadataPage.kt](../Android/app/src/main/java/br/com/onda/mobile/MetadataPage.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `MetadataPage` | [20](../Android/app/src/main/java/br/com/onda/mobile/MetadataPage.kt#L20) | função |
| `localAudioItem` | [55](../Android/app/src/main/java/br/com/onda/mobile/MetadataPage.kt#L55) | função |

</details>

<details>
<summary><code>MetadataPlatformBadge.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/MetadataPlatformBadge.kt](../Android/app/src/main/java/br/com/onda/mobile/MetadataPlatformBadge.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `metadataPlatform` | [14](../Android/app/src/main/java/br/com/onda/mobile/MetadataPlatformBadge.kt#L14) | função |
| `MetadataPlatformBadge` | [19](../Android/app/src/main/java/br/com/onda/mobile/MetadataPlatformBadge.kt#L19) | função |

</details>

<details>
<summary><code>NavigableList.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/NavigableList.kt](../Android/app/src/main/java/br/com/onda/mobile/NavigableList.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `NavigableList` | [14](../Android/app/src/main/java/br/com/onda/mobile/NavigableList.kt#L14) | função |

</details>

<details>
<summary><code>NoticeNavigation.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/NoticeNavigation.kt](../Android/app/src/main/java/br/com/onda/mobile/NoticeNavigation.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `noticeDestination` | [4](../Android/app/src/main/java/br/com/onda/mobile/NoticeNavigation.kt#L4) | função |

</details>

<details>
<summary><code>OndaApplication.kt</code> — 18 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `OndaApplication` | [17](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L17) | class |
| `newImageLoader` | [18](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L18) | função |
| `onCreate` | [23](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L23) | função |
| `SecureVault` | [32](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L32) | object |
| `initialize` | [34](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L34) | função |
| `key` | [35](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L35) | função |
| `put` | [43](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L43) | função |
| `get` | [48](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L48) | função |
| `remove` | [56](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L56) | função |
| `clear` | [57](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L57) | função |
| `ToolPreparation` | [60](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L60) | class |
| `MobileEngine` | [62](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L62) | object |
| `initialize` | [65](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L65) | função |
| `call` | [83](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L83) | função |
| `reply` | [100](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L100) | função |
| `cancel` | [103](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L103) | função |
| `EventCallback` | [108](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L108) | interface |
| `onEvent` | [108](../Android/app/src/main/java/br/com/onda/mobile/OndaApplication.kt#L108) | função |

</details>

<details>
<summary><code>OndaLogo.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/OndaLogo.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaLogo.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `OndaLogo` | [13](../Android/app/src/main/java/br/com/onda/mobile/OndaLogo.kt#L13) | função |

</details>

<details>
<summary><code>OndaStore.kt</code> — 58 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadItem` | [19](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L19) | class |
| `HistoryItem` | [20](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L20) | class |
| `Question` | [21](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L21) | class |
| `storedObject` | [23](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L23) | função |
| `OndaDatabase` | [25](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L25) | class |
| `onCreate` | [26](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L26) | função |
| `onUpgrade` | [30](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L30) | função |
| `OndaStore` | [33](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L33) | object |
| `enqueueBatch` | [55](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L55) | função |
| `initialize` | [70](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L70) | função |
| `defaults` | [98](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L98) | função |
| `normalizeAppearance` | [109](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L109) | função |
| `saveSettings` | [135](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L135) | função |
| `config` | [146](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L146) | função |
| `executionConfig` | [158](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L158) | função |
| `refresh` | [162](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L162) | função |
| `refreshQueue` | [163](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L163) | função |
| `comparisonHistory` | [177](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L177) | função |
| `refreshHistory` | [185](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L185) | função |
| `enqueue` | [192](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L192) | função |
| `deferDuplicateStart` | [229](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L229) | função |
| `update` | [233](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L233) | função |
| `rename` | [244](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L244) | função |
| `renamePendingLink` | [249](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L249) | função |
| `updateQueueInformation` | [258](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L258) | função |
| `collectionOptions` | [266](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L266) | função |
| `saveCollectionOptions` | [270](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L270) | função |
| `resetCollectionOptions` | [275](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L275) | função |
| `remove` | [278](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L278) | função |
| `retry` | [290](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L290) | função |
| `replaceDownloadLink` | [291](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L291) | função |
| `useFailureMetadata` | [301](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L301) | função |
| `retryWithVersionChoice` | [310](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L310) | função |
| `reorderPending` | [319](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L319) | função |
| `sortPending` | [326](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L326) | função |
| `movePendingBefore` | [331](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L331) | função |
| `queueEstimate` | [337](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L337) | função |
| `confirmQueueSpace` | [344](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L344) | função |
| `move` | [350](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L350) | função |
| `log` | [357](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L357) | função |
| `ask` | [358](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L358) | função |
| `cancelAllDuplicates` | [362](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L362) | função |
| `answer` | [373](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L373) | função |
| `dismissQuestions` | [377](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L377) | função |
| `duplicateChoice` | [385](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L385) | função |
| `importDocument` | [395](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L395) | função |
| `destination` | [405](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L405) | função |
| `replacePublished` | [457](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L457) | função |
| `publicationConfig` | [462](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L462) | função |
| `publish` | [465](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L465) | função |
| `overwriteAudio` | [491](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L491) | função |
| `open` | [498](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L498) | função |
| `shareIntent` | [503](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L503) | função |
| `share` | [508](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L508) | função |
| `undoHistory` | [513](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L513) | função |
| `removeHistory` | [531](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L531) | função |
| `clearHistory` | [545](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L545) | função |
| `mimeFor` | [546](../Android/app/src/main/java/br/com/onda/mobile/OndaStore.kt#L546) | função |

</details>

<details>
<summary><code>OndaViewModel.kt</code> — 82 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `objects` | [20](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L20) | função |
| `cleanString` | [21](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L21) | função |
| `stringList` | [22](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L22) | função |
| `DialogNotice` | [24](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L24) | class |
| `operationNoticeTitle` | [26](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L26) | função |
| `importNoticeTitle` | [50](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L50) | função |
| `OndaViewModel` | [64](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L64) | class |
| `completeCard` | [67](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L67) | função |
| `showNotice` | [99](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L99) | função |
| `dismissNotice` | [100](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L100) | função |
| `onEvents` | [109](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L109) | função |
| `onPlayerError` | [112](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L112) | função |
| `closeOnlineImages` | [126](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L126) | função |
| `previewOnlineImageAt` | [127](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L127) | função |
| `cancelOnlineImagePreview` | [138](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L138) | função |
| `previewOnlineImages` | [139](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L139) | função |
| `downloadOnlineImages` | [147](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L147) | função |
| `cancelPlaybackCollection` | [165](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L165) | função |
| `effectsQueueIndex` | [169](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L169) | função |
| `appendEffectsRecord` | [172](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L172) | função |
| `effectPreparation` | [186](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L186) | função |
| `effectFailure` | [187](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L187) | função |
| `retryEffectsPreparation` | [189](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L189) | função |
| `loadEffectsInfo` | [216](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L216) | função |
| `appendEffectsFiles` | [246](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L246) | função |
| `moveEffectsTrack` | [247](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L247) | função |
| `removeEffectsTrack` | [248](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L248) | função |
| `clearEffectsQueue` | [249](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L249) | função |
| `storeLyrics` | [252](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L252) | função |
| `lookupLyrics` | [253](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L253) | função |
| `rememberEffectsControls` | [290](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L290) | função |
| `effectsControlSnapshot` | [294](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L294) | função |
| `effectsControlsMatch` | [295](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L295) | função |
| `mediaToggleEffects` | [296](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L296) | função |
| `mediaSeekEffects` | [297](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L297) | função |
| `mediaPreviousEffects` | [298](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L298) | função |
| `mediaNextEffects` | [299](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L299) | função |
| `advanceEffects` | [300](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L300) | função |
| `addPlaybackCollection` | [311](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L311) | função |
| `mediaPauseEffects` | [335](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L335) | função |
| `stopTransientPreview` | [336](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L336) | função |
| `playEffectsQueueTrack` | [337](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L337) | função |
| `publishEffectsMedia` | [352](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L352) | função |
| `EffectRenderKey` | [368](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L368) | class |
| `isEffectsTrackPreloaded` | [373](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L373) | função |
| `effectsTransitionSeconds` | [374](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L374) | função |
| `clearEffectTail` | [375](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L375) | função |
| `beginEffectsTrackChange` | [382](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L382) | função |
| `fadeEffectsIn` | [391](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L391) | função |
| `preloadEffectsTrack` | [408](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L408) | função |
| `lyricsPosition` | [510](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L510) | função |
| `selectEffectsSource` | [511](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L511) | função |
| `setEffectsVolume` | [520](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L520) | função |
| `pauseEffectsPlayback` | [521](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L521) | função |
| `stopEffectsPlayback` | [532](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L532) | função |
| `toggleEffectsPlayback` | [533](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L533) | função |
| `seekEffectsPlayback` | [538](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L538) | função |
| `importConversionBatch` | [543](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L543) | função |
| `previewEffects` | [557](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L557) | função |
| `previewEffects` | [558](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L558) | função |
| `operation` | [572](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L572) | função |
| `report` | [573](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L573) | função |
| `openHistoryFolder` | [619](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L619) | função |
| `connectSpotify` | [627](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L627) | função |
| `cancel` | [638](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L638) | função |
| `releaseDate` | [641](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L641) | função |
| `search` | [660](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L660) | função |
| `loadCollection` | [676](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L676) | função |
| `compareCollectionLocal` | [681](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L681) | função |
| `importCollection` | [710](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L710) | função |
| `importLocal` | [711](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L711) | função |
| `enqueueLink` | [721](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L721) | função |
| `loadQueueInformation` | [743](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L743) | função |
| `useInEffects` | [756](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L756) | função |
| `preview` | [762](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L762) | função |
| `stopPreview` | [773](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L773) | função |
| `previewYouTube` | [775](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L775) | função |
| `queueTrack` | [794](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L794) | função |
| `enqueueLinks` | [802](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L802) | função |
| `queueCollection` | [820](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L820) | função |
| `savePlaybackSession` | [840](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L840) | função |
| `onCleared` | [863](../Android/app/src/main/java/br/com/onda/mobile/OndaViewModel.kt#L863) | função |

</details>

<details>
<summary><code>OnlineImageGallery.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/OnlineImageGallery.kt](../Android/app/src/main/java/br/com/onda/mobile/OnlineImageGallery.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `canPreviewOnlineImages` | [20](../Android/app/src/main/java/br/com/onda/mobile/OnlineImageGallery.kt#L20) | função |
| `OnlineImagePreviewButton` | [27](../Android/app/src/main/java/br/com/onda/mobile/OnlineImageGallery.kt#L27) | função |
| `OnlineImageGallery` | [35](../Android/app/src/main/java/br/com/onda/mobile/OnlineImageGallery.kt#L35) | função |

</details>

<details>
<summary><code>OrganizationOptions.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/OrganizationOptions.kt](../Android/app/src/main/java/br/com/onda/mobile/OrganizationOptions.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `OrganizationOptions` | [11](../Android/app/src/main/java/br/com/onda/mobile/OrganizationOptions.kt#L11) | função |

</details>

<details>
<summary><code>PlatformIdentity.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/PlatformIdentity.kt](../Android/app/src/main/java/br/com/onda/mobile/PlatformIdentity.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PlatformIdentity` | [8](../Android/app/src/main/java/br/com/onda/mobile/PlatformIdentity.kt#L8) | class |
| `identifyPlatform` | [13](../Android/app/src/main/java/br/com/onda/mobile/PlatformIdentity.kt#L13) | função |

</details>

<details>
<summary><code>PlaybackOrderControls.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/PlaybackOrderControls.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaybackOrderControls.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PlaybackOrderControls` | [10](../Android/app/src/main/java/br/com/onda/mobile/PlaybackOrderControls.kt#L10) | função |
| `ShufflePlaybackButton` | [16](../Android/app/src/main/java/br/com/onda/mobile/PlaybackOrderControls.kt#L16) | função |

</details>

<details>
<summary><code>PlaybackQueueOrder.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/PlaybackQueueOrder.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaybackQueueOrder.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `shuffledNextIndex` | [3](../Android/app/src/main/java/br/com/onda/mobile/PlaybackQueueOrder.kt#L3) | função |
| `nextPlaybackIndex` | [8](../Android/app/src/main/java/br/com/onda/mobile/PlaybackQueueOrder.kt#L8) | função |
| `movePlaybackEntry` | [16](../Android/app/src/main/java/br/com/onda/mobile/PlaybackQueueOrder.kt#L16) | função |
| `playbackCursorAfterMove` | [22](../Android/app/src/main/java/br/com/onda/mobile/PlaybackQueueOrder.kt#L22) | função |

</details>

<details>
<summary><code>PlaybackSessions.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PlaybackSessions` | [7](../Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt#L7) | object |
| `load` | [8](../Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt#L8) | função |
| `save` | [11](../Android/app/src/main/java/br/com/onda/mobile/PlaybackSessions.kt#L11) | função |

</details>

<details>
<summary><code>PlaylistLocalFiles.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/PlaylistLocalFiles.kt](../Android/app/src/main/java/br/com/onda/mobile/PlaylistLocalFiles.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `playlistInventory` | [10](../Android/app/src/main/java/br/com/onda/mobile/PlaylistLocalFiles.kt#L10) | função |
| `collectionSyncSummary` | [53](../Android/app/src/main/java/br/com/onda/mobile/PlaylistLocalFiles.kt#L53) | função |
| `collectionSyncState` | [60](../Android/app/src/main/java/br/com/onda/mobile/PlaylistLocalFiles.kt#L60) | função |

</details>

<details>
<summary><code>PreviewRequest.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/PreviewRequest.kt](../Android/app/src/main/java/br/com/onda/mobile/PreviewRequest.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `PreviewRequest` | [10](../Android/app/src/main/java/br/com/onda/mobile/PreviewRequest.kt#L10) | class |
| `cancel` | [15](../Android/app/src/main/java/br/com/onda/mobile/PreviewRequest.kt#L15) | função |
| `start` | [23](../Android/app/src/main/java/br/com/onda/mobile/PreviewRequest.kt#L23) | função |

</details>

<details>
<summary><code>ProgressGate.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ProgressGate.kt](../Android/app/src/main/java/br/com/onda/mobile/ProgressGate.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ProgressGate` | [6](../Android/app/src/main/java/br/com/onda/mobile/ProgressGate.kt#L6) | class |
| `allow` | [8](../Android/app/src/main/java/br/com/onda/mobile/ProgressGate.kt#L8) | função |

</details>

<details>
<summary><code>QueueControls.kt</code> — 13 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `number` | [24](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L24) | função |
| `queueDuration` | [25](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L25) | função |
| `queueBytes` | [29](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L29) | função |
| `orderedPending` | [40](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L40) | função |
| `pendingOrder` | [50](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L50) | função |
| `sizeText` | [56](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L56) | função |
| `QueueSpace` | [58](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L58) | class |
| `text` | [60](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L60) | função |
| `queueSpace` | [67](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L67) | função |
| `queueConnected` | [86](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L86) | função |
| `queueActivity` | [91](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L91) | função |
| `QueueDragHandle` | [104](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L104) | função |
| `targetAtPointer` | [112](../Android/app/src/main/java/br/com/onda/mobile/QueueControls.kt#L112) | função |

</details>

<details>
<summary><code>QueueDisplayControls.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueDisplayControls.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueDisplayControls.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadCardSizeControl` | [13](../Android/app/src/main/java/br/com/onda/mobile/QueueDisplayControls.kt#L13) | função |

</details>

<details>
<summary><code>QueueDragHandle.kt</code> — 6 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueDragPreview` | [24](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt#L24) | class |
| `displacement` | [28](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt#L28) | função |
| `clear` | [34](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt#L34) | função |
| `DraggableQueueCard` | [38](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt#L38) | função |
| `updateTarget` | [52](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt#L52) | função |
| `QueueDragHandle` | [83](../Android/app/src/main/java/br/com/onda/mobile/QueueDragHandle.kt#L83) | função |

</details>

<details>
<summary><code>QueueFilters.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueFilters.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueFilters.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `queueFold` | [7](../Android/app/src/main/java/br/com/onda/mobile/QueueFilters.kt#L7) | função |
| `QueueMatcher` | [8](../Android/app/src/main/java/br/com/onda/mobile/QueueFilters.kt#L8) | class |
| `matches` | [19](../Android/app/src/main/java/br/com/onda/mobile/QueueFilters.kt#L19) | função |
| `queueMatches` | [27](../Android/app/src/main/java/br/com/onda/mobile/QueueFilters.kt#L27) | função |

</details>

<details>
<summary><code>QueueRunner.kt</code> — 6 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `DownloadRuntime` | [9](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt#L9) | object |
| `pause` | [15](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt#L15) | função |
| `resume` | [16](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt#L16) | função |
| `interruptActive` | [17](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt#L17) | função |
| `stop` | [19](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt#L19) | função |
| `runDownloads` | [22](../Android/app/src/main/java/br/com/onda/mobile/QueueRunner.kt#L22) | função |

</details>

<details>
<summary><code>QueueTiming.kt</code> — 7 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueTimes` | [6](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L6) | class |
| `queueDuration` | [7](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L7) | função |
| `QueueTiming` | [13](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L13) | class |
| `reset` | [17](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L17) | função |
| `setRunning` | [18](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L18) | função |
| `recordCompletion` | [22](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L22) | função |
| `snapshot` | [23](../Android/app/src/main/java/br/com/onda/mobile/QueueTiming.kt#L23) | função |

</details>

<details>
<summary><code>QueueTrackInformation.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/QueueTrackInformation.kt](../Android/app/src/main/java/br/com/onda/mobile/QueueTrackInformation.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `QueueTrackInformation` | [16](../Android/app/src/main/java/br/com/onda/mobile/QueueTrackInformation.kt#L16) | função |

</details>

<details>
<summary><code>RoundSlider.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/RoundSlider.kt](../Android/app/src/main/java/br/com/onda/mobile/RoundSlider.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `RoundSlider` | [15](../Android/app/src/main/java/br/com/onda/mobile/RoundSlider.kt#L15) | função |

</details>

<details>
<summary><code>SettingsSearch.kt</code> — 7 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SettingsSearchEntry` | [15](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L15) | class |
| `settingsFold` | [17](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L17) | função |
| `settingsSearchMatches` | [18](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L18) | função |
| `settingsSearchText` | [22](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L22) | função |
| `settingsSearchEntries` | [27](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L27) | função |
| `settingsSearchModifier` | [44](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L44) | função |
| `settingsCategoryOrder` | [52](../Android/app/src/main/java/br/com/onda/mobile/SettingsSearch.kt#L52) | função |

</details>

<details>
<summary><code>SettingsWindow.kt</code> — 6 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `SettingsDivider` | [36](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt#L36) | função |
| `SettingsWindow` | [40](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt#L40) | função |
| `put` | [60](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt#L60) | função |
| `moveBottom` | [174](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt#L174) | função |
| `move` | [191](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt#L191) | função |
| `ResetWindow` | [308](../Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt#L308) | função |

</details>

<details>
<summary><code>SongCardTitle.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/SongCardTitle.kt](../Android/app/src/main/java/br/com/onda/mobile/SongCardTitle.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `songCardTitle` | [4](../Android/app/src/main/java/br/com/onda/mobile/SongCardTitle.kt#L4) | função |

</details>

<details>
<summary><code>SpotifyBrowser.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/SpotifyBrowser.kt](../Android/app/src/main/java/br/com/onda/mobile/SpotifyBrowser.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `spotifyBrowserIntent` | [8](../Android/app/src/main/java/br/com/onda/mobile/SpotifyBrowser.kt#L8) | função |
| `openSpotifyAuthorization` | [12](../Android/app/src/main/java/br/com/onda/mobile/SpotifyBrowser.kt#L12) | função |

</details>

<details>
<summary><code>StatusNotice.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/StatusNotice.kt](../Android/app/src/main/java/br/com/onda/mobile/StatusNotice.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `rememberStatusNotice` | [19](../Android/app/src/main/java/br/com/onda/mobile/StatusNotice.kt#L19) | função |
| `TopStatusNotice` | [33](../Android/app/src/main/java/br/com/onda/mobile/StatusNotice.kt#L33) | função |

</details>

<details>
<summary><code>SystemNavigation.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/SystemNavigation.kt](../Android/app/src/main/java/br/com/onda/mobile/SystemNavigation.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `applyNavigationBarTheme` | [10](../Android/app/src/main/java/br/com/onda/mobile/SystemNavigation.kt#L10) | função |

</details>

<details>
<summary><code>TabVisibility.kt</code> — 5 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt](../Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `hiddenTabs` | [7](../Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt#L7) | função |
| `visibleTabs` | [12](../Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt#L12) | função |
| `normalizeBottomBarOrder` | [19](../Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt#L19) | função |
| `bottomBarOrder` | [21](../Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt#L21) | função |
| `bottomBarDestinations` | [25](../Android/app/src/main/java/br/com/onda/mobile/TabVisibility.kt#L25) | função |

</details>

<details>
<summary><code>TechnicalErrors.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt](../Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `TechnicalErrorCatalog` | [4](../Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt#L4) | class |
| `translate` | [8](../Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt#L8) | função |
| `part` | [9](../Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt#L9) | função |
| `explain` | [18](../Android/app/src/main/java/br/com/onda/mobile/TechnicalErrors.kt#L18) | função |

</details>

<details>
<summary><code>ToolDesign.kt</code> — 6 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `ToolCard` | [20](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt#L20) | função |
| `ToolHeading` | [26](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt#L26) | função |
| `ToolEmpty` | [33](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt#L33) | função |
| `ToolSwitch` | [41](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt#L41) | função |
| `ToolLink` | [65](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt#L65) | função |
| `ToolTabs` | [74](../Android/app/src/main/java/br/com/onda/mobile/ToolDesign.kt#L74) | função |

</details>

<details>
<summary><code>ToolStatusControls.kt</code> — 3 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/ToolStatusControls.kt](../Android/app/src/main/java/br/com/onda/mobile/ToolStatusControls.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `toolDateText` | [26](../Android/app/src/main/java/br/com/onda/mobile/ToolStatusControls.kt#L26) | função |
| `ToolStatusList` | [30](../Android/app/src/main/java/br/com/onda/mobile/ToolStatusControls.kt#L30) | função |
| `ToolStatusControls` | [58](../Android/app/src/main/java/br/com/onda/mobile/ToolStatusControls.kt#L58) | função |

</details>

<details>
<summary><code>TrackDownloadDialog.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/TrackDownloadDialog.kt](../Android/app/src/main/java/br/com/onda/mobile/TrackDownloadDialog.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `TrackDownloadDialog` | [18](../Android/app/src/main/java/br/com/onda/mobile/TrackDownloadDialog.kt#L18) | função |
| `submit` | [27](../Android/app/src/main/java/br/com/onda/mobile/TrackDownloadDialog.kt#L27) | função |

</details>

<details>
<summary><code>TrackMatches.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/TrackMatches.kt](../Android/app/src/main/java/br/com/onda/mobile/TrackMatches.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `mergeTrackMatches` | [6](../Android/app/src/main/java/br/com/onda/mobile/TrackMatches.kt#L6) | função |

</details>

<details>
<summary><code>VersionSelection.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/VersionSelection.kt](../Android/app/src/main/java/br/com/onda/mobile/VersionSelection.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `applyVersionSelection` | [6](../Android/app/src/main/java/br/com/onda/mobile/VersionSelection.kt#L6) | função |

</details>

<details>
<summary><code>VideoConverterPage.kt</code> — 1 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/VideoConverterPage.kt](../Android/app/src/main/java/br/com/onda/mobile/VideoConverterPage.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `VideoConverterPage` | [21](../Android/app/src/main/java/br/com/onda/mobile/VideoConverterPage.kt#L21) | função |

</details>

<details>
<summary><code>WorkflowStatus.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/WorkflowStatus.kt](../Android/app/src/main/java/br/com/onda/mobile/WorkflowStatus.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `workflowLabel` | [4](../Android/app/src/main/java/br/com/onda/mobile/WorkflowStatus.kt#L4) | função |
| `canQueueAction` | [18](../Android/app/src/main/java/br/com/onda/mobile/WorkflowStatus.kt#L18) | função |

</details>

<details>
<summary><code>YouTubeSessionCookies.kt</code> — 4 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionCookies.kt](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionCookies.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `youtubeCookieEntries` | [3](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionCookies.kt#L3) | função |
| `hasYouTubeLogin` | [11](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionCookies.kt#L11) | função |
| `youtubeCookieFile` | [12](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionCookies.kt#L12) | função |
| `isYouTubeCookieFile` | [17](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionCookies.kt#L17) | função |

</details>

<details>
<summary><code>YouTubeSessionWindow.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionWindow.kt](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionWindow.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `YouTubeSessionWindow` | [17](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionWindow.kt#L17) | função |
| `shouldOverrideUrlLoading` | [29](../Android/app/src/main/java/br/com/onda/mobile/YouTubeSessionWindow.kt#L29) | função |

</details>

<details>
<summary><code>YouTubeWorkload.kt</code> — 2 declarações</summary>

[Android/app/src/main/java/br/com/onda/mobile/YouTubeWorkload.kt](../Android/app/src/main/java/br/com/onda/mobile/YouTubeWorkload.kt)

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `usesYouTube` | [5](../Android/app/src/main/java/br/com/onda/mobile/YouTubeWorkload.kt#L5) | função |
| `belongs` | [7](../Android/app/src/main/java/br/com/onda/mobile/YouTubeWorkload.kt#L7) | função |

</details>

### 23.4 Android: ponte Python e credenciais

<details>
<summary><code>credentials.py</code> — 6 declarações</summary>

[Android/app/src/main/python/credentials.py](../Android/app/src/main/python/credentials.py)

Descrição do módulo no fonte: Android credential adapter: encrypted storage is owned by Android Keystore.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `CredentialError` | [4](../Android/app/src/main/python/credentials.py#L4) | classe |
| `CredentialStore` | [7](../Android/app/src/main/python/credentials.py#L7) | classe |
| `CredentialStore.__init__` | [8](../Android/app/src/main/python/credentials.py#L8) | função/método |
| `CredentialStore.load` | [11](../Android/app/src/main/python/credentials.py#L11) | função/método |
| `CredentialStore.save` | [16](../Android/app/src/main/python/credentials.py#L16) | função/método |
| `CredentialStore.forget` | [20](../Android/app/src/main/python/credentials.py#L20) | função/método |

</details>

<details>
<summary><code>mobile_backend.py</code> — 34 declarações</summary>

[Android/app/src/main/python/mobile_backend.py](../Android/app/src/main/python/mobile_backend.py)

Descrição do módulo no fonte: Android adapter for ONDA's shared engine. No desktop/UI imports required.

| Símbolo | Linha | Tipo |
| --- | --- | --- |
| `Cancelled` | [21](../Android/app/src/main/python/mobile_backend.py#L21) | classe |
| `session_options` | [25](../Android/app/src/main/python/mobile_backend.py#L25) | função/método |
| `readable_error` | [40](../Android/app/src/main/python/mobile_backend.py#L40) | função/método |
| `emit` | [50](../Android/app/src/main/python/mobile_backend.py#L50) | função/método |
| `ask` | [62](../Android/app/src/main/python/mobile_backend.py#L62) | função/método |
| `ask_version` | [76](../Android/app/src/main/python/mobile_backend.py#L76) | função/método |
| `ask_catalog` | [90](../Android/app/src/main/python/mobile_backend.py#L90) | função/método |
| `ask_review` | [98](../Android/app/src/main/python/mobile_backend.py#L98) | função/método |
| `ask_duplicate` | [103](../Android/app/src/main/python/mobile_backend.py#L103) | função/método |
| `ask_flac_browser` | [111](../Android/app/src/main/python/mobile_backend.py#L111) | função/método |
| `ask_media` | [120](../Android/app/src/main/python/mobile_backend.py#L120) | função/método |
| `ManagedProcess` | [127](../Android/app/src/main/python/mobile_backend.py#L127) | classe |
| `ManagedProcess.__init__` | [129](../Android/app/src/main/python/mobile_backend.py#L129) | função/método |
| `use_cached_extractor` | [151](../Android/app/src/main/python/mobile_backend.py#L151) | função/método |
| `use_cached_extractor.parts` | [163](../Android/app/src/main/python/mobile_backend.py#L163) | função/método |
| `select_cached_extractor` | [168](../Android/app/src/main/python/mobile_backend.py#L168) | função/método |
| `configure` | [182](../Android/app/src/main/python/mobile_backend.py#L182) | função/método |
| `configure.executable` | [206](../Android/app/src/main/python/mobile_backend.py#L206) | função/método |
| `configure.AndroidOS` | [211](../Android/app/src/main/python/mobile_backend.py#L211) | classe |
| `configure.AndroidOS.__getattr__` | [213](../Android/app/src/main/python/mobile_backend.py#L213) | função/método |
| `configure.AndroidOS.link` | [217](../Android/app/src/main/python/mobile_backend.py#L217) | função/método |
| `configure.initialize` | [236](../Android/app/src/main/python/mobile_backend.py#L236) | função/método |
| `configure.open_image` | [251](../Android/app/src/main/python/mobile_backend.py#L251) | função/método |
| `configure.save_webp` | [273](../Android/app/src/main/python/mobile_backend.py#L273) | função/método |
| `reply` | [286](../Android/app/src/main/python/mobile_backend.py#L286) | função/método |
| `cancel` | [293](../Android/app/src/main/python/mobile_backend.py#L293) | função/método |
| `client` | [306](../Android/app/src/main/python/mobile_backend.py#L306) | função/método |
| `account` | [320](../Android/app/src/main/python/mobile_backend.py#L320) | função/método |
| `render_preview` | [329](../Android/app/src/main/python/mobile_backend.py#L329) | função/método |
| `jukebox_action` | [354](../Android/app/src/main/python/mobile_backend.py#L354) | função/método |
| `perform` | [395](../Android/app/src/main/python/mobile_backend.py#L395) | função/método |
| `perform.capture` | [617](../Android/app/src/main/python/mobile_backend.py#L617) | função/método |
| `perform.opener` | [658](../Android/app/src/main/python/mobile_backend.py#L658) | função/método |
| `run` | [721](../Android/app/src/main/python/mobile_backend.py#L721) | função/método |

</details>

---

<a id="sec-24"></a>

## 24. Site e infraestrutura de construção

Relação dos fontes rastreados de site, empacotamento, integração e construção. Arquivos de runtime gerados e dependências não são reenumerados. Hash permite detectar se o arquivo mudou desde esta revisão; não é assinatura de segurança.

| Arquivo | SHA-256 (12 primeiros caracteres) |
| --- | --- |
| [.github/workflows/pages.yml](../.github/workflows/pages.yml) | `8cf0a6ebc59b` |
| [Android/app/build.gradle.kts](../Android/app/build.gradle.kts) | `0163f190e938` |
| [Android/build.gradle.kts](../Android/build.gradle.kts) | `89bf09d5ae0e` |
| [Android/gradle.properties](../Android/gradle.properties) | `3734df9cdae5` |
| [Android/gradle/wrapper/gradle-wrapper.properties](../Android/gradle/wrapper/gradle-wrapper.properties) | `1a6f8e431f09` |
| [Android/gradlew](../Android/gradlew) | `1ce03a421a97` |
| [Android/gradlew.bat](../Android/gradlew.bat) | `57931b17dd22` |
| [Android/nativebuild/NATIVE_ARTIFACTS.json](../Android/nativebuild/NATIVE_ARTIFACTS.json) | `377045ae069f` |
| [Android/nativebuild/NATIVE_TEST_RESULTS.json](../Android/nativebuild/NATIVE_TEST_RESULTS.json) | `2e1f2db634fb` |
| [Android/nativebuild/RUNTIME_DEPENDENCIES.json](../Android/nativebuild/RUNTIME_DEPENDENCIES.json) | `33029a4ac87e` |
| [Android/nativebuild/VALIDATION.json](../Android/nativebuild/VALIDATION.json) | `815b73aac0d3` |
| [Android/nativebuild/bootstrap.py](../Android/nativebuild/bootstrap.py) | `a774879eb52b` |
| [Android/nativebuild/build-native.sh](../Android/nativebuild/build-native.sh) | `f8c1927f41e7` |
| [Android/nativebuild/source-lock.json](../Android/nativebuild/source-lock.json) | `b4b2c8e2b988` |
| [Android/nativebuild/toolchains.json](../Android/nativebuild/toolchains.json) | `86a82f0c9d7b` |
| [Android/settings.gradle.kts](../Android/settings.gradle.kts) | `d956e7afdd4b` |
| [docs/onda-site/app.js](../docs/onda-site/app.js) | `7725833c0d86` |
| [docs/onda-site/index.html](../docs/onda-site/index.html) | `3507ce8a4619` |
| [docs/onda-site/style.css](../docs/onda-site/style.css) | `a47faf47d862` |
| [empacotamento/Installer.cs](../empacotamento/Installer.cs) | `07403253b204` |
| [empacotamento/Installer.manifest](../empacotamento/Installer.manifest) | `9aba37d7ed18` |
| [empacotamento/Installer.xaml](../empacotamento/Installer.xaml) | `3850a1b8d273` |
| [empacotamento/InstallerStrings.xml](../empacotamento/InstallerStrings.xml) | `f4c045753e1b` |
| [empacotamento/InstallerText.cs](../empacotamento/InstallerText.cs) | `bcacfafe3b83` |
| [empacotamento/Launcher.cs](../empacotamento/Launcher.cs) | `63a905e0c628` |
| [empacotamento/Onda.iss](../empacotamento/Onda.iss) | `6400470f99f6` |
| [empacotamento/Uninstaller.cs](../empacotamento/Uninstaller.cs) | `0904e5667ac1` |
| [empacotamento/Uninstaller.xaml](../empacotamento/Uninstaller.xaml) | `de486f43a657` |
| [empacotamento/build_installer.py](../empacotamento/build_installer.py) | `bbde2f77ab6d` |
| [empacotamento/build_package.py](../empacotamento/build_package.py) | `6e2574387ab0` |
| [empacotamento/generate_brand_icons.py](../empacotamento/generate_brand_icons.py) | `e7a4f15d2e05` |
| [empacotamento/prepare_release.py](../empacotamento/prepare_release.py) | `3d7a4be785c4` |
| [empacotamento/prepare_release_1_1_3.py](../empacotamento/prepare_release_1_1_3.py) | `3357218938b1` |
| [empacotamento/prepare_release_1_1_4.py](../empacotamento/prepare_release_1_1_4.py) | `57a5ee854010` |
| [empacotamento/sync_version.py](../empacotamento/sync_version.py) | `4195f4a532c8` |

### Funções nomeadas do site

[docs/onda-site/app.js](../docs/onda-site/app.js)

- `esc` — linha 321.
- `assetUrl` — linha 326.
- `releaseLabel` — linha 337.
- `platformIcon` — linha 355.
- `updateTheme` — linha 387.
- `render` — linha 425.
- `link` — linha 443.
- `heading` — linha 449.
- `preview` — linha 544.
- `guideImage` — linha 582.
- `routeIndex` — linha 707.

---

<a id="sec-25"></a>

## 25. Cobertura e evidências de teste existentes

Esta fotografia enumera **307 arquivos de produção** do aplicativo (157 Python, 49 QML e 101 Kotlin), **2330 declarações nomeadas** e **35 arquivos de site/construção/infraestrutura**. Foram localizados **243 arquivos de testes Python/Kotlin no levantamento**. Quantidade de arquivos não equivale à quantidade de casos executados.

Relatórios prévios de release registram execuções; não foram reexecutados nesta revisão documental:

- [docs/VALIDACAO-RELEASE-1.2.3.md](../docs/VALIDACAO-RELEASE-1.2.3.md)
- [docs/TESTES-DOWNLOAD-2026-10-24.md](../docs/TESTES-DOWNLOAD-2026-10-24.md)
- [docs/ACESSIBILIDADE-ANDROID.md](../docs/ACESSIBILIDADE-ANDROID.md)
- [Android/validation/RESULTADOS.md](../Android/validation/RESULTADOS.md)

<details>
<summary>Arquivos de testes para consulta futura</summary>

- [Android/app/src/androidTest/java/br/com/onda/mobile/AccessibilityTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/AccessibilityTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/AdvancedFeatureTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/AdvancedFeatureTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/AndroidShellTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/AndroidShellTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/AppearanceWindowTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/AppearanceWindowTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/BatchMetadataUiTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/BatchMetadataUiTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/BlackDialogTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/BlackDialogTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/BlackThemeTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/BlackThemeTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/CacheCleanupTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/CacheCleanupTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/CancelDuplicatesTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/CancelDuplicatesTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/CollectionInputFeaturesTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/CollectionInputFeaturesTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/CompleteLocalizationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/CompleteLocalizationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/CoverCropTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/CoverCropTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/DailyNotificationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/DailyNotificationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/DownloadDefaultsTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/DownloadDefaultsTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/DownloadsHomeTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/DownloadsHomeTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/ErrorNoticeUiTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/ErrorNoticeUiTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/HistoryActionsTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/HistoryActionsTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/HistoryFolderTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/HistoryFolderTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/HistoryViewTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/HistoryViewTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/ImageCarouselFeaturesTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/ImageCarouselFeaturesTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/InAppUpdateTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/InAppUpdateTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/JukeboxMediaTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/JukeboxMediaTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/JukeboxQueuePreparationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/JukeboxQueuePreparationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LargeQueueTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LargeQueueTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LauncherIconTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LauncherIconTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LayoutSpacingUiTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LayoutSpacingUiTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LibraryWorkflowTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LibraryWorkflowTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/ListNavigationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/ListNavigationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LiveCatalogTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LiveCatalogTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LocalImageImportTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LocalImageImportTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/LocalizationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/LocalizationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/MediaChoiceTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/MediaChoiceTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/MetadataOverwriteTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/MetadataOverwriteTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/MetadataPlatformBadgeTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/MetadataPlatformBadgeTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/MetadataTabTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/MetadataTabTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/MobileRuntimeTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/MobileRuntimeTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/NativeLicensesTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/NativeLicensesTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/NavigationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/NavigationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/OndaLogoTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/OndaLogoTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/OnlineImageGalleryTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/OnlineImageGalleryTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/PerformanceBenchmarkTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/PerformanceBenchmarkTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/PlaybackParityUiTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/PlaybackParityUiTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/PlaybackSessionFeaturesTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/PlaybackSessionFeaturesTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/PreferenceRecoveryTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/PreferenceRecoveryTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/QueueControlsTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/QueueControlsTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/QueueDisplayTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/QueueDisplayTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/QueueFilterTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/QueueFilterTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/QueueImprovementsTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/QueueImprovementsTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/QueueNavigationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/QueueNavigationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/QueueTitleLookupTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/QueueTitleLookupTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/ResponsivenessTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/ResponsivenessTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SearchFlowTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SearchFlowTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SearchMatchingTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SearchMatchingTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SecondaryLocalizationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SecondaryLocalizationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SettingsNotificationSearchTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SettingsNotificationSearchTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SettingsSearchTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SettingsSearchTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SpanishDialogTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SpanishDialogTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SpanishLocalizationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SpanishLocalizationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/StatusNoticeAnimationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/StatusNoticeAnimationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/StatusNoticeTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/StatusNoticeTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/StorageRegressionTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/StorageRegressionTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/StoreOptimizationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/StoreOptimizationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SwitchVisibilityTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SwitchVisibilityTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/SystemNavigationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/SystemNavigationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/TabVisibilityTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/TabVisibilityTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/TechnicalErrorLocalizationTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/TechnicalErrorLocalizationTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/ToolsRedesignTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/ToolsRedesignTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/ToolsStorageTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/ToolsStorageTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/TrackCardLayoutTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/TrackCardLayoutTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/VersionSelectionTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/VersionSelectionTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/VideoConverterTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/VideoConverterTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/VideoLimitsTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/VideoLimitsTest.kt)
- [Android/app/src/debug/python/cache_cleanup_smoke.py](../Android/app/src/debug/python/cache_cleanup_smoke.py)
- [Android/app/src/debug/python/mobile_advanced_smoke.py](../Android/app/src/debug/python/mobile_advanced_smoke.py)
- [Android/app/src/debug/python/mobile_history_smoke.py](../Android/app/src/debug/python/mobile_history_smoke.py)
- [Android/app/src/debug/python/mobile_search_smoke.py](../Android/app/src/debug/python/mobile_search_smoke.py)
- [Android/app/src/debug/python/mobile_smoke.py](../Android/app/src/debug/python/mobile_smoke.py)
- [Android/app/src/debug/python/mobile_video_limits_smoke.py](../Android/app/src/debug/python/mobile_video_limits_smoke.py)
- [Android/app/src/debug/python/video_converter_smoke.py](../Android/app/src/debug/python/video_converter_smoke.py)
- [Android/app/src/test/java/br/com/onda/mobile/AlbumGlassTest.kt](../Android/app/src/test/java/br/com/onda/mobile/AlbumGlassTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/BottomBarOrderTest.kt](../Android/app/src/test/java/br/com/onda/mobile/BottomBarOrderTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/DailyUseTest.kt](../Android/app/src/test/java/br/com/onda/mobile/DailyUseTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/DownloadFeedbackTest.kt](../Android/app/src/test/java/br/com/onda/mobile/DownloadFeedbackTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/DownloadRequestsTest.kt](../Android/app/src/test/java/br/com/onda/mobile/DownloadRequestsTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/DuplicateLinksTest.kt](../Android/app/src/test/java/br/com/onda/mobile/DuplicateLinksTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/EffectsTimelineTest.kt](../Android/app/src/test/java/br/com/onda/mobile/EffectsTimelineTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/FailureSummaryTest.kt](../Android/app/src/test/java/br/com/onda/mobile/FailureSummaryTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/HighContrastTest.kt](../Android/app/src/test/java/br/com/onda/mobile/HighContrastTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/HistoryGroupingTest.kt](../Android/app/src/test/java/br/com/onda/mobile/HistoryGroupingTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/HistoryOriginTest.kt](../Android/app/src/test/java/br/com/onda/mobile/HistoryOriginTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/HistoryRowsTest.kt](../Android/app/src/test/java/br/com/onda/mobile/HistoryRowsTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/JukeboxGraphColorsTest.kt](../Android/app/src/test/java/br/com/onda/mobile/JukeboxGraphColorsTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/JukeboxTimerTest.kt](../Android/app/src/test/java/br/com/onda/mobile/JukeboxTimerTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/LayoutSpacingTest.kt](../Android/app/src/test/java/br/com/onda/mobile/LayoutSpacingTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/MediaMimeTypeTest.kt](../Android/app/src/test/java/br/com/onda/mobile/MediaMimeTypeTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/NoticeNavigationTest.kt](../Android/app/src/test/java/br/com/onda/mobile/NoticeNavigationTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/PlaybackParityTest.kt](../Android/app/src/test/java/br/com/onda/mobile/PlaybackParityTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/PreviewRequestTest.kt](../Android/app/src/test/java/br/com/onda/mobile/PreviewRequestTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/QueueMatcherTest.kt](../Android/app/src/test/java/br/com/onda/mobile/QueueMatcherTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/QueueTimingTest.kt](../Android/app/src/test/java/br/com/onda/mobile/QueueTimingTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/SongCardTitleTest.kt](../Android/app/src/test/java/br/com/onda/mobile/SongCardTitleTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/TechnicalErrorsTest.kt](../Android/app/src/test/java/br/com/onda/mobile/TechnicalErrorsTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/YouTubeSessionCookiesTest.kt](../Android/app/src/test/java/br/com/onda/mobile/YouTubeSessionCookiesTest.kt)
- [Android/app/src/test/java/br/com/onda/mobile/YouTubeWorkloadTest.kt](../Android/app/src/test/java/br/com/onda/mobile/YouTubeWorkloadTest.kt)
- [Onda/test_accessibility_options.py](../Onda/test_accessibility_options.py)
- [Onda/test_advanced_features.py](../Onda/test_advanced_features.py)
- [Onda/test_albums.py](../Onda/test_albums.py)
- [Onda/test_android_session.py](../Onda/test_android_session.py)
- [Onda/test_app_version.py](../Onda/test_app_version.py)
- [Onda/test_appearance.py](../Onda/test_appearance.py)
- [Onda/test_artist_alias_lookup.py](../Onda/test_artist_alias_lookup.py)
- [Onda/test_artist_aliases.py](../Onda/test_artist_aliases.py)
- [Onda/test_audit_regressions.py](../Onda/test_audit_regressions.py)
- [Onda/test_auto_match.py](../Onda/test_auto_match.py)
- [Onda/test_auto_select_media.py](../Onda/test_auto_select_media.py)
- [Onda/test_automation.py](../Onda/test_automation.py)
- [Onda/test_brand_mark.py](../Onda/test_brand_mark.py)
- [Onda/test_cache_cleanup.py](../Onda/test_cache_cleanup.py)
- [Onda/test_catalog.py](../Onda/test_catalog.py)
- [Onda/test_catalog_display.py](../Onda/test_catalog_display.py)
- [Onda/test_catalog_recovery.py](../Onda/test_catalog_recovery.py)
- [Onda/test_catalog_title_fallback.py](../Onda/test_catalog_title_fallback.py)
- [Onda/test_choices.py](../Onda/test_choices.py)
- [Onda/test_clear_queue.py](../Onda/test_clear_queue.py)
- [Onda/test_clipboard_links.py](../Onda/test_clipboard_links.py)
- [Onda/test_collection_cards.py](../Onda/test_collection_cards.py)
- [Onda/test_credentials.py](../Onda/test_credentials.py)
- [Onda/test_daily_use.py](../Onda/test_daily_use.py)
- [Onda/test_deep_audit.py](../Onda/test_deep_audit.py)
- [Onda/test_deezer_release_date.py](../Onda/test_deezer_release_date.py)
- [Onda/test_desktop_layout.py](../Onda/test_desktop_layout.py)
- [Onda/test_display_persistence.py](../Onda/test_display_persistence.py)
- [Onda/test_download_cookies.py](../Onda/test_download_cookies.py)
- [Onda/test_download_defaults.py](../Onda/test_download_defaults.py)
- [Onda/test_download_feedback.py](../Onda/test_download_feedback.py)
- [Onda/test_download_performance.py](../Onda/test_download_performance.py)
- [Onda/test_download_recovery.py](../Onda/test_download_recovery.py)
- [Onda/test_dynamic_downloads.py](../Onda/test_dynamic_downloads.py)
- [Onda/test_effects_metadata.py](../Onda/test_effects_metadata.py)
- [Onda/test_engine.py](../Onda/test_engine.py)
- [Onda/test_enter_search.py](../Onda/test_enter_search.py)
- [Onda/test_error_localization.py](../Onda/test_error_localization.py)
- [Onda/test_failure_report.py](../Onda/test_failure_report.py)
- [Onda/test_failure_window.py](../Onda/test_failure_window.py)
- [Onda/test_ffmpeg_runtime.py](../Onda/test_ffmpeg_runtime.py)
- [Onda/test_first_run.py](../Onda/test_first_run.py)
- [Onda/test_flac_browser.py](../Onda/test_flac_browser.py)
- [Onda/test_history_cache.py](../Onda/test_history_cache.py)
- [Onda/test_history_origin.py](../Onda/test_history_origin.py)
- [Onda/test_history_platforms.py](../Onda/test_history_platforms.py)
- [Onda/test_i18n.py](../Onda/test_i18n.py)
- [Onda/test_image_gallery.py](../Onda/test_image_gallery.py)
- [Onda/test_image_preferences.py](../Onda/test_image_preferences.py)
- [Onda/test_images.py](../Onda/test_images.py)
- [Onda/test_interface_fonts.py](../Onda/test_interface_fonts.py)
- [Onda/test_interface_spacing.py](../Onda/test_interface_spacing.py)
- [Onda/test_jukebox.py](../Onda/test_jukebox.py)
- [Onda/test_jukebox_equalizer.py](../Onda/test_jukebox_equalizer.py)
- [Onda/test_jukebox_stream.py](../Onda/test_jukebox_stream.py)
- [Onda/test_keep_pitch.py](../Onda/test_keep_pitch.py)
- [Onda/test_keyboard_shortcuts.py](../Onda/test_keyboard_shortcuts.py)
- [Onda/test_library_features.py](../Onda/test_library_features.py)
- [Onda/test_library_performance.py](../Onda/test_library_performance.py)
- [Onda/test_library_workflows.py](../Onda/test_library_workflows.py)
- [Onda/test_list_context.py](../Onda/test_list_context.py)
- [Onda/test_localization_completeness.py](../Onda/test_localization_completeness.py)
- [Onda/test_lossless_source.py](../Onda/test_lossless_source.py)
- [Onda/test_lyrics_service.py](../Onda/test_lyrics_service.py)
- [Onda/test_media_additions.py](../Onda/test_media_additions.py)
- [Onda/test_media_audio.py](../Onda/test_media_audio.py)
- [Onda/test_media_links.py](../Onda/test_media_links.py)
- [Onda/test_metadata.py](../Onda/test_metadata.py)
- [Onda/test_metadata_badges.py](../Onda/test_metadata_badges.py)
- [Onda/test_online_image_preview.py](../Onda/test_online_image_preview.py)
- [Onda/test_optimization.py](../Onda/test_optimization.py)
- [Onda/test_output_companions.py](../Onda/test_output_companions.py)
- [Onda/test_performance.py](../Onda/test_performance.py)
- [Onda/test_playback_controls.py](../Onda/test_playback_controls.py)
- [Onda/test_playback_input.py](../Onda/test_playback_input.py)
- [Onda/test_playlist_account.py](../Onda/test_playlist_account.py)
- [Onda/test_playlist_folders.py](../Onda/test_playlist_folders.py)
- [Onda/test_playlist_limit.py](../Onda/test_playlist_limit.py)
- [Onda/test_playlist_now.py](../Onda/test_playlist_now.py)
- [Onda/test_playlist_search.py](../Onda/test_playlist_search.py)
- [Onda/test_playlist_sync.py](../Onda/test_playlist_sync.py)
- [Onda/test_preview_duration.py](../Onda/test_preview_duration.py)
- [Onda/test_progress_completion.py](../Onda/test_progress_completion.py)
- [Onda/test_project_audit.py](../Onda/test_project_audit.py)
- [Onda/test_qt_collection_inputs.py](../Onda/test_qt_collection_inputs.py)
- [Onda/test_qt_effects_media.py](../Onda/test_qt_effects_media.py)
- [Onda/test_qt_error_localization.py](../Onda/test_qt_error_localization.py)
- [Onda/test_qt_jukebox.py](../Onda/test_qt_jukebox.py)
- [Onda/test_qt_models.py](../Onda/test_qt_models.py)
- [Onda/test_qt_playback_queue.py](../Onda/test_qt_playback_queue.py)
- [Onda/test_qt_regressions.py](../Onda/test_qt_regressions.py)
- [Onda/test_qt_settings_search.py](../Onda/test_qt_settings_search.py)
- [Onda/test_qt_workspace.py](../Onda/test_qt_workspace.py)
- [Onda/test_quality_improvements.py](../Onda/test_quality_improvements.py)
- [Onda/test_queue_cards.py](../Onda/test_queue_cards.py)
- [Onda/test_queue_control.py](../Onda/test_queue_control.py)
- [Onda/test_queue_filter.py](../Onda/test_queue_filter.py)
- [Onda/test_queue_names.py](../Onda/test_queue_names.py)
- [Onda/test_queue_restore.py](../Onda/test_queue_restore.py)
- [Onda/test_queue_timing.py](../Onda/test_queue_timing.py)
- [Onda/test_quick_download.py](../Onda/test_quick_download.py)
- [Onda/test_remaster_identity.py](../Onda/test_remaster_identity.py)
- [Onda/test_reset_settings.py](../Onda/test_reset_settings.py)
- [Onda/test_responsiveness.py](../Onda/test_responsiveness.py)
- [Onda/test_search_evidence.py](../Onda/test_search_evidence.py)
- [Onda/test_search_precision.py](../Onda/test_search_precision.py)
- [Onda/test_search_upgrade.py](../Onda/test_search_upgrade.py)
- [Onda/test_settings_layout.py](../Onda/test_settings_layout.py)
- [Onda/test_settings_scroll_icons.py](../Onda/test_settings_scroll_icons.py)
- [Onda/test_settings_search.py](../Onda/test_settings_search.py)
- [Onda/test_single_instance.py](../Onda/test_single_instance.py)
- [Onda/test_size_estimate.py](../Onda/test_size_estimate.py)
- [Onda/test_social_detection.py](../Onda/test_social_detection.py)
- [Onda/test_social_flow.py](../Onda/test_social_flow.py)
- [Onda/test_social_media.py](../Onda/test_social_media.py)
- [Onda/test_soundtrack_matching.py](../Onda/test_soundtrack_matching.py)
- [Onda/test_spanish.py](../Onda/test_spanish.py)
- [Onda/test_sped_up.py](../Onda/test_sped_up.py)
- [Onda/test_spotify_optional.py](../Onda/test_spotify_optional.py)
- [Onda/test_spotify_priority.py](../Onda/test_spotify_priority.py)
- [Onda/test_spotify_search.py](../Onda/test_spotify_search.py)
- [Onda/test_svg.py](../Onda/test_svg.py)
- [Onda/test_tab_order.py](../Onda/test_tab_order.py)
- [Onda/test_tab_visibility.py](../Onda/test_tab_visibility.py)
- [Onda/test_tiktok_media.py](../Onda/test_tiktok_media.py)
- [Onda/test_twitter_media.py](../Onda/test_twitter_media.py)
- [Onda/test_video_converter.py](../Onda/test_video_converter.py)
- [Onda/test_video_limits.py](../Onda/test_video_limits.py)
- [Onda/test_window_icons.py](../Onda/test_window_icons.py)
- [Onda/test_window_position.py](../Onda/test_window_position.py)
- [Onda/test_windows_media.py](../Onda/test_windows_media.py)
- [Onda/test_work_cleanup.py](../Onda/test_work_cleanup.py)
- [Onda/test_youtube_workload.py](../Onda/test_youtube_workload.py)
- [empacotamento/test_installer.py](../empacotamento/test_installer.py)
- [empacotamento/test_uninstaller.py](../empacotamento/test_uninstaller.py)

- [Onda/test_workflow_clarity.py](../Onda/test_workflow_clarity.py)
- [Android/app/src/test/java/br/com/onda/mobile/WorkflowStatusTest.kt](../Android/app/src/test/java/br/com/onda/mobile/WorkflowStatusTest.kt)
- [Android/app/src/androidTest/java/br/com/onda/mobile/WorkflowClarityTest.kt](../Android/app/src/androidTest/java/br/com/onda/mobile/WorkflowClarityTest.kt)

- [Onda/test_tools_presentation.py](../Onda/test_tools_presentation.py)

</details>

<!-- INVENTARIO_TECNICO:FIM -->
