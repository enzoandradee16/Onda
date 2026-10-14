# Histórico de versões

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
