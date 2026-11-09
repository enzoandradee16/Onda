# Inventário de funcionalidades do ONDA

Referência de recursos existentes, diferenças entre plataformas e localização das implementações.

> **Atualização de reprodução:** Efeitos e Jukebox agora compartilham a tela, a música, a fila e o player nas duas plataformas. Os ajustes podem funcionar juntos. Consulte [Reprodução unificada](REPRODUCAO-UNIFICADA.md) para o comportamento e a migração atualizados; as referências antigas a duas abas/sessões independentes abaixo descrevem a estrutura anterior.

| Revisão | Aplicativo | Windows | Android |
| --- | --- | --- | --- |
| 27/10/2026 | 1.2.4 | 1.2.4.0 | Código 31 |


**Consulta rápida:** [Funcionalidades](#sec-02) · [Diferenças entre plataformas](#sec-17) · [Limitações](#sec-20) · [Configurações](CONFIGURACOES.md)

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
- [8. Coleção](#sec-08)
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
| Fila de downloads | Página Downloads | Downloads, Em andamento | Mesmos componentes acima |
| Histórico | Página Histórico | Downloads/Concluídos e ferramentas relacionadas | `LibraryView.qml`; `HistoryPage.kt`; `DownloadsHome.kt` |
| Coleção | Página própria | Menu Mais, Salvos/Importar | `LibraryView.qml`; `CollectionsPage.kt` |
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

## 8. Coleção

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
- Efeitos/Jukebox recebem links de coleções nos seus próprios campos e nas pesquisas das filas. Os antigos botões de enviar uma coleção a esses players na página Coleção não são o fluxo principal atual.

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
- Equalizador com 5, 10 ou 15 bandas selecionáveis (10 por padrão), frequência/ganho/Q, pré-amplificação, ativar/desativar, presets e restauração. É próprio do caminho PCM do Jukebox.
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

[empacotamento/prepare_release.py](../empacotamento/prepare_release.py), `Android/build/`, [Android/app/build.gradle.kts](../Android/app/build.gradle.kts), `Android/nativebuild/`, `Android/native-provenance/`, `.github/`, `diagnosticos/`, [docs/VALIDACAO-RELEASE-1.2.7.md](../docs/VALIDACAO-RELEASE-1.2.7.md), [PUBLICAR_RELEASE.md](../PUBLICAR_RELEASE.md).

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
8. **Defaults legados:** chaves como duração antiga de efeitos/continuidade podem permanecer em arquivos de defaults sem controle visível atual. Não tratar cada chave como adição ativa.
9. **Qt e Tk:** ambos os conjuntos de arquivos existem. Funções presentes somente no Tk não comprovam paridade no Qt; consulte os fontes para investigar cada implementação.
10. **Paridade:** biblioteca de coleções salvas, Wi-Fi, player expandido Android, miniplayer Windows e projeção de Links PC têm diferenças intencionais. Recursos comuns também podem ter limites distintos.

---

<a id="sec-21"></a>

## 21. Como manter este documento

Atualização de implementação posterior à base Git: [ferramentas, estados e preparação por faixa](CLAREZA-DE-ESTADOS.md). O índice técnico foi atualizado para incluir os novos módulos: `collection_coverage.py`, `tool_status.py`, `workflow_status.py`, `ToolStatusControls.kt` e `WorkflowStatus.kt`.

- Ao alterar recurso, atualizar sua seção, plataforma, limitações e referências; marcar remoções explicitamente.
- Antes de sugerir melhoria, procurar o termo e sinônimos aqui, conferir os módulos citados e distinguir implementação ausente de bug em implementação existente.
- Usar código/interface atuais como evidência principal; changelogs e relatos são contexto histórico.
- Atualizar versão/data/commit da base após uma nova revisão; as referências devem acompanhar as mudanças do código.
- Não inserir senhas, tokens, cookies, dados de usuário ou chaves de assinatura no inventário.
