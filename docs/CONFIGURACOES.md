# Configurações do ONDA

Referência de uso revisada para **1.2.4**, em 27/10/2026. O [inventário completo](INVENTARIO-FUNCIONALIDADES.md#sec-22) relaciona campos, fontes e diferenças entre plataformas.

## Onde encontrar cada opção

| Categoria | Controles principais |
| --- | --- |
| Geral | Idioma, lembrar configurações, avisos, transferência e restauração de preferências |
| Aparência | Tema, destaque, bordas do Preto puro, fontes, espaçamento, cards e ordem/visibilidade de abas |
| Downloads | Destino, formatos, qualidade, correspondência de metadados/versões, organização, duplicados, retomada, concorrência e agendamento |
| Imagens | Formato, dimensões e proporção |
| Áudio | Letras, animação da letra, transição entre músicas e duração das prévias de pesquisa |
| Contas | Spotify, sessão do YouTube e cookies |
| Ferramentas | Atualização do ONDA, verificação/atualização de ferramentas e cache |
| Desempenho | Limpeza automática de temporários; no PC, threads, prioridade e reserva de RAM |

A distribuição exata depende da plataforma. O schema Qt está em `Onda/settings_schema/desktop.json`; a interface Android em `Android/app/src/main/java/br/com/onda/mobile/SettingsWindow.kt` e componentes relacionados. `Onda/settings_schema/layout.json` conserva contratos de organização antigos e não deve ser usado sozinho como lista de controles atuais.

## Pesquisa de configurações

Digite uma palavra no campo de pesquisa. Os resultados indicam **Configurações → categoria**, permitindo localizar a opção na aba correspondente. Certos controles só aparecem quando aplicáveis, como bordas/separações no tema Preto puro.

O índice Android está em `Android/app/src/main/assets/settings_search.json`. Ao alterar controles, confira o índice e a implementação visível: o índice ainda pode conter textos históricos sem opção correspondente na tela.

## Aparência e idioma

Instalações novas usam **Preto puro + Verde-Água**. As preferências existentes não são substituídas por esse padrão. Também existem Claro, Escuro, Seguir o sistema e Alto contraste, 16 cores de destaque, fontes e espaçamento.

A janela rápida de Aparência fica acessível pelo botão próprio; no Android, é um ícone ao lado de Configurações. As configurações completas oferecem também ordem/visibilidade das áreas e tamanhos dos cards.

Português (Brasil), Español e English ficam em Geral. Android aplica a mudança imediatamente; no PC, reinicie pelo controle oferecido quando houver mudança pendente. O idioma do instalador é independente do idioma salvo no aplicativo.

## Downloads e reprodução

- **Downloads simultâneos:** PC de 1 a 15; Android de 1 a 4.
- **Retomar arquivos interrompidos:** tenta aproveitar dados parciais quando o servidor permite.
- **Retomar fila ao abrir:** inicia pendentes ao abrir; é diferente de apenas recuperar a fila salva.
- **Formato de álbuns e playlists:** no PC, fornece a seleção inicial da janela de download por música. Alterar o formato nessa janela vale somente para a solicitação confirmada.
- **Somente Wi-Fi:** exclusivo do Android, com política de pausar ou concluir downloads ativos ao perder Wi-Fi.
- **Prévias de pesquisa:** duração configurável; o catálogo pode fornecer um trecho menor.
- **Efeitos e Jukebox:** reprodução integral, filas e posições próprias. Não há mais ajustes de duração de prévia dos efeitos nem controles para continuar Efeitos/Jukebox em outras abas. Navegar não encerra a reprodução; iniciar o outro player pausa o anterior.
- **Transição:** tempo de sobreposição configurável, aplicado aos caminhos compatíveis de troca de faixa.

No PC, **Minimizar ONDA ao abrir o miniplayer**, em Aparência, controla a janela principal na próxima abertura do miniplayer. Não altera o botão de minimizar do próprio player. O Android usa barra compacta e player expandido dentro do app.

## Persistência, contas e restauração

Lembrar configurações controla as preferências gerais. Idioma, dados de fila/histórico e sessão de reprodução têm persistência própria; restaurar configurações não apaga os arquivos baixados.

Exportar/importar configurações usa JSON e transfere preferências compatíveis. Não inclui contas, tokens, cookies, caminhos de pastas, fila, histórico ou mídias. A restauração pode ser seletiva por categoria ou geral.

Spotify e cookies ficam em Contas. Credenciais Windows usam proteção DPAPI; Android usa proteção do sistema. Não compartilhe arquivos de dados ou cookies. Disponibilidade de plataformas e permissões da conta continuam valendo.

## Cache e atualização

A limpeza automática remove caches descartáveis antigos, respeitando proteção de arquivos recentes/em uso e parciais interrompidos. A limpeza manual e a consulta de tamanho ficam nos controles de cache; operações em andamento podem impedir a limpeza.

No PC, atualizar o ONDA abre o download oficial. No Android, o APK é baixado dentro do aplicativo; depois, o usuário confirma a instalação pelo sistema. Veja [o guia de recursos avançados](../RECURSOS-AVANCADOS.md#atualizações-e-transferência-de-preferências).

**Situação das ferramentas**, em Ferramentas, mostra a última verificação, versões/disponibilidade e resultado da tentativa de atualização. Use Verificar ferramentas para atualizar o relatório local. Uma falha em um componente não oculta os demais; reinício pendente é informado. Consulte [estados e preparação](CLAREZA-DE-ESTADOS.md).
