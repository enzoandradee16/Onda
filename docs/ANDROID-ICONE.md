# Ícone Android e tema — ONDA 1.1.0

O ícone do launcher e dos aplicativos recentes acompanha as 16 cores de destaque e os modos Claro, Escuro, Preto puro e Seguir o sistema. Os recursos são vetoriais: não há conjuntos de PNGs pesados. O aumento medido no APK assinado foi de 75.909 bytes em relação ao candidato anterior.

As variantes reutilizam traços da onda e cores; o modo Sistema usa recursos de dia/noite. O ícone interno continua usando a paleta Compose. O fundo claro do ícone coincide com a superfície clara do app; preto puro usa #000000.

Activity aliases fornecem o ícone do launcher. A MainActivity permanece habilitada para compartilhar links, retornar do Spotify e abrir notificações. As alterações de componentes usam DONT_KILL_APP; Android 13+ permite aplicar a troca em lote, e Android 8–12 habilita a nova entrada antes de desabilitar a anterior. Não são solicitadas permissões novas.

O launcher controla a apresentação final e o cache. Um atalho antigo pode precisar ser recriado após atualizar a versão que introduz aliases. Launchers de fabricantes e temas próprios podem apresentar comportamento diferente; os testes não cobrem todos os aparelhos.

Testes instrumentados conferem as 64 combinações de tema/destaque, pixels das cores em dia/noite, unicidade do launcher, ícone dos recentes, manutenção da atividade e preservação das entradas de compartilhamento e Spotify. A rodada usa emulador API 36; o caminho específico Android 8–12 não foi executado em aparelho físico nesta preparação.

Implementação: LauncherIcons.kt, recursos launcher_wave_*, ic_onda_launcher_* e launcher_colors.xml. Ao alterar a paleta em MainActivity.kt, mantenha os recursos equivalentes e execute LauncherIconTest.

Referência de plataforma: [activity-alias — Android Developers](https://developer.android.com/guide/topics/manifest/activity-alias-element).
