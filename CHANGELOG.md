# Histórico de versões

## Em desenvolvimento

- Android: modo Somente Wi-Fi com política ao perder a rede e retomada; controles opcionais de pausar/retomar, parar e abrir a fila na notificação, ativados por padrão.
- PC: minimizar para a bandeja, restaurar/sair pelo menu e progresso agregado na barra de tarefas.
- Ação ao terminar a fila nas duas versões: som, notificação, ambos ou nenhuma. PC também oferece desligamento confirmado e contagem regressiva cancelável.

- Fila no PC e Android: atividade por item, motivos de espera, ordenação de pendentes e reordenação por arrastar, com setas e persistência.
- Estimativa de espaço da fila, margem para temporários, indicação de tamanhos desconhecidos e aviso de possível falta de armazenamento antes de iniciar.

- Letra sincronizada LRC opcional, desligada por padrão, na reprodução local de PC e Android.
- Conversão em lote de áudio e vídeo para os formatos disponíveis no conversor nas duas versões, preservando originais e tratando falhas por arquivo.
- PC: arrastar arquivos para o conversor, editor ou efeitos e arrastar links para adicionar à fila após confirmação.

## 1.1.5 — 2026-10-17

- Reconhecimento de links copiados com confirmação obrigatória antes do download. Evita repetir avisos do mesmo link; opção em Configurações → Geral, ativada por padrão. Android verifica somente com o aplicativo em primeiro plano.
- Abas opcionais podem ser ocultadas individualmente, preservando as principais e a ordem escolhida.
- Interface simplificada opcional oculta controles de formato/qualidade sem alterar espaçamento ou escolhas salvas.
- Instagram, TikTok e Kwai: qualidade automática e seleção inicial de todas as mídias, com opções independentes. Permite desmarcar itens e alternar Selecionar todas/Desmarcar todas.
- Downloads: novas tentativas de capa, conclusão sem imagem quando a capa falha, recuperação com outra versão compatível após rejeição e busca ampliada por álbum, mantendo os filtros de identidade.


## 1.1.4 — 2026-10-16

- Conversor de vídeos em uma aba própria, ao lado de Imagens: MP4, MKV e MOV, qualidade, resolução máxima, bitrate, FPS, remoção de áudio, progresso e cancelamento. O original é preservado.
- Extração de áudio de vídeos para MP3, M4A e AAC, com seleção da qualidade em kbps. A prévia abre o aplicativo padrão do sistema.
- Busca e filtros de estado na fila, com contagem dos resultados e seleção dos itens visíveis. Os filtros não alteram a execução da fila.
- Ícones monocolor da plataforma dos metadados, incluindo Apple Music, e opção Abrir origem no histórico quando o endereço estiver registrado.
- Limpeza de cache nas configurações, com estimativa de espaço e proteção de downloads, fila, histórico, contas e trabalhos ativos.
- Pesquisa nas configurações e categorias unificadas: Geral, Aparência, Downloads, Imagens, Áudio, Contas e Ferramentas. Opções comuns seguem a mesma ordem nas duas versões.
- Verificação de atualizações ao abrir ativada por padrão nas novas instalações; preferências existentes são preservadas.
- Ajustes de ícones no modo compacto, seletores, ações da fila e configurações de escolha automática de versão.


## 1.1.3 — 2026-10-15

- Interface PC/Android: espaçamento Compacto/Padrão/Confortável com aplicação imediata e preferência persistida; exportação/importação inclui a nova opção.
- Android: avisos entram descendo e saem subindo, com opção para desligar e links para configurações/sessão quando há orientação. Checkbox e texto têm mais respiro; ações da fila distribuídas em duas linhas.
- PC: seletores de visualização/tamanho mais largos, atalhos Ctrl+A e Ctrl+setas, além dos demais atalhos da janela de ajuda.
- Recuperação HTTP 403: formatos recusados excluídos da nova tentativa, preferência por HLS do mesmo vídeo e até três tentativas limitadas para áudio.
- Fila separada de Links nas duas interfaces; downloads imediatos abrem a fila e iniciam o processamento. Verificações de identidade e edição preservadas, sem consultas extras quando o primeiro resultado já é compatível.


- Busca adicional de aliases no MusicBrainz após falha da busca normal, com confirmação por gravação e identidade do artista, cache local com expiração, rejeição de homônimos e limite de consultas compartilhado entre downloads.

- Correspondência: alias verificado Antônio Carlos Jobim/Tom Jobim, com fonte registrada e preservação dos filtros de duração e versão. Janela de falhas mantém os botões visíveis e limita a área do motivo com rolagem. Motivo e link original da falha passam a persistir na fila.

- Links Spotify (PC e Android): preserva os metadados originais, reaproveita dados completos das playlists e a conexão nos links individuais. Outros catálogos preenchem somente campos ausentes, com origem registrada por campo; links de outros serviços não recebem essa prioridade.

- PC e Android: resumo automático das falhas ao finalizar a fila, com exportação TXT (música, link e motivo), pesquisa e escolha manual de metadados por item e nova tentativa apenas dos itens desse resumo.

- PC e Android: verificações adicionais de créditos de participação, pontuação, versões equivalentes, artista localizado com ISRC, edições de álbum, ano de lançamento e conteúdo explícito/limpo. Dados estruturados de uploads Topic auxiliam a busca sem desativar os filtros de versão e duração.

- Comparação de títulos preserva letras japonesas e outros alfabetos. Quando a busca no YouTube não encontra uma versão compatível, tenta títulos alternativos confirmados em catálogo por artista e duração junto ao ISRC ou álbum/faixa/disco. A posição na playlist não é usada como número da faixa; títulos originais são preservados no áudio.

- PC: remove a área temporária dos downloads concluídos, incluindo sobras de miniaturas e processamento; apaga `.onda-work` quando o último trabalho termina e a pasta fica vazia. Arquivos parciais de outros itens são preservados para retomada.

- PC e Android: tempo decorrido da execução e estimativa do tempo restante junto à contagem da fila. Pausas não entram no tempo; estimativa usa as conclusões observadas, considerando o ritmo com downloads simultâneos.

- PC e Android: opção independente para escolher automaticamente os metadados de maior similaridade entre resultados compatíveis, preservando escolhas manuais salvas.

- PC e Android: contagem na fila com concluídos/total e quantidade restante, atualizada ao concluir, adicionar ou remover itens. Falhas e cancelamentos continuam como não concluídos.

- Android: navegação rápida nas filas e playlists, ações antes das listas como opção, inclusão em lotes para coleções grandes e pedidos ao serviço com token pequeno.
- Android: sessão atual do YouTube aplicada aos itens já na fila, exportação de cookies validada, importação específica de cookies do YouTube e diagnóstico de sessão recusada.

## 1.1.2 — 2026-10-15

- Detecção de links duplicados na fila e no histórico, com confirmação e normalização de links de compartilhamento.
- Edição seletiva de metadados e capa em lote no Windows e Android, com seleção múltipla no histórico e cópias por padrão.
- Novos modelos de pastas e nomes de arquivos, com prévia e preservação das pastas de playlists.

## 1.1.1 — 2026-10-14

- **Correção de tema Android:** a troca do ícone da tela inicial é concluída em segundo plano, preservando a tela aberta ao alterar tema ou cor de destaque.

- **Otimização:** menos consultas de atualização e de prévia Android em segundo plano; canal de notificações reconfigurado apenas quando necessário; removidas atualizações e imports redundantes no PC.

## 1.1.0 — 2026-10-14

Preparação local da atualização; publicação no GitHub separada.

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


## 1.0.0 — 2026-10-13

Primeira versão oficial para Windows e Android.

- Histórico completo em cards ou compacto, com capas e informações da música, seleção individual e ajuste discreto do tamanho dos cards. No PC, Ctrl + roda do mouse também ajusta o tamanho.
- Preto puro com opção de bordas e separações. No Android, popups e barra de navegação acompanham o tema.
- Ícone interno acompanha a cor de destaque; no PC, os ícones das janelas também acompanham a cor.
- PC: rolagem da página inteira, edição de metadados na própria aba e abertura direta pelo histórico, ajustes de capa e destaque de álbum/artista.
- PC: até 15 downloads simultâneos, com aviso de maior consumo; Backspace também remove itens selecionados nas listas que oferecem remoção.
- Android: correções na importação de imagens locais e permissões, seleção automática de versões e abertura de metadados pelo histórico.
- Android: opção de escolher manualmente a versão quando a seleção automática não encontra uma correspondência suficientemente compatível.
- Correções de acesso às publicações Kwai, consultando páginas desktop e mobile e evitando baixar vídeos recomendados no lugar do solicitado.
- Vídeos: correção da escolha de resolução/FPS no Kwai e demais plataformas; consideração do lado menor em vídeos verticais, preferência por qualidades nativas compatíveis e redução quando a fonte excede os limites escolhidos.
- Avisos com duração padrão de três segundos em novas instalações e melhor distribuição dos botões da pesquisa Android.
- Cache limitado de capas/metadados, menos releituras no histórico, substituição de arquivos Android com cópia de segurança e limpeza de código sem uso.


## Windows 1.0.0-beta.2 / Android 1.0.0-alpha.2 — 2026-10-13

- FLAC direto do Monochrome para músicas de catálogo, com correspondência e validação do áudio.
- Novos downloads durante uma execução e extensão segura do escopo da fila.
- Correção do progresso após conclusão e testes da interface com downloads simultâneos.
- Preparação de versões e pacotes de pré-release.

## Em desenvolvimento

- Busca adicional de aliases no MusicBrainz após falha da busca normal, com confirmação por gravação e identidade do artista, cache local com expiração, rejeição de homônimos e limite de consultas compartilhado entre downloads.

- Correspondência: alias verificado Antônio Carlos Jobim/Tom Jobim, com fonte registrada e preservação dos filtros de duração e versão. Janela de falhas mantém os botões visíveis e limita a área do motivo com rolagem. Motivo e link original da falha passam a persistir na fila.

- Links Spotify (PC e Android): preserva os metadados originais, reaproveita dados completos das playlists e a conexão nos links individuais. Outros catálogos preenchem somente campos ausentes, com origem registrada por campo; links de outros serviços não recebem essa prioridade.

- PC e Android: resumo automático das falhas ao finalizar a fila, com exportação TXT (música, link e motivo), pesquisa e escolha manual de metadados por item e nova tentativa apenas dos itens desse resumo.

- PC e Android: verificações adicionais de créditos de participação, pontuação, versões equivalentes, artista localizado com ISRC, edições de álbum, ano de lançamento e conteúdo explícito/limpo. Dados estruturados de uploads Topic auxiliam a busca sem desativar os filtros de versão e duração.

- Navegação e configurações: reutilização de tema/layout no PC, troca direta de categorias no Android e menos trabalho durante transições e arraste dos controles.

- PC: carregamento de abas sob demanda e preenchimento gradual de playlists grandes.
- PC e Android: busca de playlists com espera curta entre digitações.
- Android: limites de atualizações de progresso/notificação e de cache de capas.
- Comparação de desempenho e diagnósticos reproduzíveis em `docs/OTIMIZACAO.md`.

## 1.0.0-beta.1 — 2026-10-12

Primeira versão beta preparada para distribuição.

- Pesquisa de músicas, metadados, capas e correspondências no YouTube.
- Downloads de áudio, vídeo e imagens, fila, histórico e organização por pastas.
- Álbuns, playlists, importação de TXT/M3U/CSV e controles próprios de qualidade.
- Seleção de mídias em publicações, incluindo vídeo completo ou somente áudio.
- Slowed, Sped Up, Reverb, presets, prévia e manutenção de tom.
- Temas claro/escuro/do sistema, 16 cores e organização das abas.
- Pacotes separados para uso portátil e instalação por usuário no Windows x64.

Limitações: acesso às plataformas pode exigir login/cookies; listas públicas podem ser parciais; a fonte equivalente no YouTube pode diferir da edição original. FLAC convertido de uma fonte com perdas não restaura qualidade lossless. Executáveis sem assinatura digital.

Desinstalador com escolha para manter ou apagar dados pessoais, preservando os downloads.

FFmpeg preparado automaticamente no primeiro uso, diretamente do fornecedor, com progresso, SHA-256 e cache compartilhado; removido dos pacotes portátil e instalador.

- Desinstalador: escolha independente para remover o FFmpeg baixado pelo ONDA, mantendo a opção de preservar configurações; modo silencioso mantém dados e cache.
