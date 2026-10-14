# Validação ONDA 1.1.0 — 14/10/2026

Pacotes locais preparados; não houve commit, push, tag nem publicação nesta etapa. Windows 10/11 x64; Android 8+ ARM64, versionCode 18.

## Resultados desta preparação

- PC: 374 testes passaram em 60 módulos isolados, sem casos ignorados. Incluem idiomas, janelas, fila, histórico, capas, metadados e seleção/conversão de vídeo.
- Android: 5 testes unitários e 21 casos instrumentados distintos passaram no emulador API 36. As rodadas de 20 e 5 casos repetem quatro testes; não são 25 casos distintos. Incluem idiomas/janelas, fila, identificação online do link Spotify, histórico, runtime e ícones.
- Lint Android: zero erros, 62 avisos e 2 sugestões. Os avisos permanecem registrados no relatório; não foram tratados como erros ocultos.
- Ícones Android: 64 combinações de cor/aparência e 128 verificações de cores em dia/noite, unicidade do launcher e recentes. Trocar tema preservou atividade/processo e entradas de compartilhamento e retorno Spotify. APK cresceu 75.909 bytes; sem novas permissões. Detalhes em docs/ANDROID-ICONE.md no pacote de fontes.
- Catálogos EN/ES compartilhados, com chaves e marcadores equivalentes; português permanece padrão e a ordem é Português (Brasil), Español, English. Aviso público de álbum Spotify e contagem da lista também traduzidos.
- Portátil: autodiagnóstico aprovado, sete abas, imports e ferramentas disponíveis. Fontes do runtime sincronizados; launcher e instalador com versão de arquivo 1.1.0.0.
- APK: assinatura de produção validada; certificado SHA-256 `0edd6f5de88fc24b7a45212b51ba7d428030302459e9ed8d619d7dbc29fb81b3`. versionName 1.1.0/code18, ARM64, minSdk26/targetSdk35, sem flag debuggable.
- Atualização de produção no emulador: APKs 1.0.0/code16 e 1.1.0/code17 atualizados por cima para 1.1.0/code18, com abertura pelo novo alias do launcher, processo ativo, sem flag debuggable e buffer de crash vazio. Aberturas frias de 1,372 s e 1,359 s nessas execuções; não constituem benchmark de aparelho físico. O snapshot anterior do emulador foi restaurado.
- Fontes nativas/terceiros reaproveitadas da release 1.0.0, após conferência dos hashes, pois não houve atualização de dependências/ferramentas. Os binários nativos do APK são conferidos contra Celular/nativebuild/SHA256SUMS.txt.
- Pacotes ZIP submetidos à verificação de integridade. SHA256SUMS.txt e MANIFEST.json registram os artefatos; SOURCE_MANIFEST.json registra os arquivos de fontes correspondentes.

## Limites

Não foi executado um novo ciclo completo em aparelho físico nesta preparação. As capturas enviadas pelo usuário mostram as novas interfaces; elas não substituem uma bateria formal de testes. Não foram testadas todas as plataformas, regiões, sessões, aparelhos ou execução prolongada em segundo plano. A troca de componentes no caminho específico Android 8–12 não foi executada em aparelho físico; fabricantes podem atualizar o cache/atalhos do launcher de formas diferentes.

A instalação/desinstalação Windows em máquina limpa não foi repetida nesta rodada. O portátil foi testado, e o instalador foi recompilado e teve sua versão conferida. Windows permanece sem Authenticode; o APK usa a mesma chave de produção da 1.0.0.

Os fontes incluem alterações locais ainda não commitadas. Antes de publicar, envie a árvore correspondente ao GitHub e crie v1.1.0 sobre o commit correspondente. O manifest registra o commit-base, sem alegar que ele já contém as alterações. Não reutilize a tag v1.0.0.

FFmpeg Windows não é redistribuído: é preparado diretamente do fornecedor no primeiro uso. Cookies, credenciais, chaves, configurações pessoais, mídias, caches e repositório Git não entram nos pacotes de fontes.


### Correção de persistência da fila e do histórico

Visualização e tamanho dos cards são preservados em ambas as plataformas, inclusive com Lembrar configurações desativado. Teste novo no PC abre processos separados para gravar e restaurar Compacto/Completa nas duas janelas, com salvamento geral ligado e desligado. Oito testes direcionados de PC passaram (incluindo sete regressões existentes). No Android, quatro testes de QueueDisplayTest passaram, incluindo a restauração das duas visualizações e tamanhos após recarregar OndaStore; cinco testes unitários e a compilação release também passaram. Evidência: display-persistence-build.log e display-persistence-android-tests.log em diagnosticos/resultados. Os totais anteriores acima correspondem à validação anterior; não representam uma nova execução completa após esta correção.


### Salvamento ativado por padrão no PC

Lembrar configurações inicia ativado; a desativação manual é mantida separadamente em remember.json sem guardar as opções da sessão. Restaurar esse ajuste retorna ao novo padrão ativado. Testes direcionados cobrem primeira abertura, desativação, restauração e processos separados do portátil para tema, cor, escala de fonte, formato/qualidade, playlists, escolha automática, pitch, simultaneidade e dimensões de imagens. Evidência: diagnosticos/resultados/remember-default-tests.log. Android já usava esse padrão e seu APK não foi alterado nesta etapa.


### Auditoria completa dos textos próprios em inglês e espanhol

Catálogos compartilhados: 1.219 entradas por idioma (348 adições). Passaram 33 testes direcionados do PC, 12 instrumentados Android e cinco testes unitários Android. Compilação release/debug e lint passaram sem erros. Verificados os assets dos dois catálogos no APK assinado contra as fontes. Logs: localization-complete-pc-tests.log, localization-complete-android-tests.log, localization-complete-build.log, localization-complete-signature.log e localization-complete-production-upgrade.log em diagnosticos/resultados. O resumo localization-complete-summary.json registra esta rodada; os totais anteriores continuam sendo históricos, sem nova execução da suíte completa. Mensagens de serviços externos e do sistema não são traduzidas automaticamente.


### Acessibilidade Android

Validação em emulador API 36: 13 testes instrumentados distintos passaram em execuções isoladas (2 controles/recorte acessíveis em três idiomas, 8 regressões de fila/idiomas, 1 árvore AccessibilityNodeInfo nativa e 2 regressões do recorte). Cinco testes de catálogo compartilhado e os cinco testes unitários Android passaram. Compilação e lint sem erros. Catálogo compartilhado atualizado para 1.242 entradas por idioma. Resumo: diagnosticos/resultados/accessibility-summary.json.

Execuções combinadas apresentaram timeout do diálogo de recorte após outros cenários; os logs iniciais foram preservados e a validação do recorte foi isolada. A rolagem do teste novo também usa a ação de acessibilidade. Os cenários isolados passaram, incluindo a verificação do arquivo exportado e a preservação do original. Não houve teste de fala com TalkBack em aparelho físico nem nova implementação de leitor de tela na interface Windows/Tk.


## Revisão final antes da publicação — 2026-10-14

Revisados 62 módulos de testes PC: 381 casos na rodada inicial, com uma falha em teste antigo que pressupunha lembrar configurações desativado por padrão. O teste foi corrigido para desativar a opção explicitamente. Os 18 testes afetados passaram, incluindo uma nova regressão; 382 casos distintos verificados no total. A confirmação de atualização agora traduz a pergunta separadamente, preservando o nome do arquivo.

Android: build de produção e debug concluídos, cinco testes unitários aprovados e lint sem erros (62 avisos e duas sugestões). Treze testes de instrumentação distintos passaram; o teste do Histórico foi atualizado para localizar o controle acessível e passou em execução isolada após falhar na rodada combinada. Os registros originais foram preservados. Os testes de acessibilidade da rodada anterior continuam documentados separadamente.

Não foi repetida a fala do TalkBack em aparelho físico nem a instalação/desinstalação Windows em ambiente limpo. Os artefatos seguem em preparação local, sem publicação.


### Confirmação de uso com TalkBack

Em 2026-10-14, o usuário confirmou que o TalkBack funcionou em seu teste. Este é um relato de uso do usuário, adicional aos testes automáticos; não implica cobertura de todos os aparelhos, telas ou idiomas.


## Atualização interna Android

DownloadManager mantém a transferência em segundo plano e seu identificador salvo permite recuperar o estado ao reabrir as configurações. Controles permitem acompanhar, cancelar, descartar e solicitar a instalação. O APK deve ter o mesmo pacote e assinatura e versionCode superior. REQUEST_INSTALL_PACKAGES permite solicitar a instalação; a autorização de origem e a confirmação continuam sendo feitas pelo usuário no Android.

Sete testes instrumentados passaram (cinco do atualizador e dois dos catálogos); cinco testes unitários e build release/debug passaram. PC: dez testes passaram e sete foram ignorados por dependerem do ambiente de interface. Lint: zero erros, 66 avisos e duas sugestões. Logs in-app-update-*. Ainda não há uma release posterior publicada para validar a transferência completa e a instalação de uma nova versão pelo fluxo.


## Menus de contexto no PC

As sete listas Treeview têm menus de contexto: pesquisa, fila, histórico, álbuns/playlists, lista auxiliar da playlist, metadados e escolha de versão (incluindo a variante de escolha de metadados). Cards completos de fila e histórico também expõem o menu nos filhos. Botão direito sobre um item seleciona o alvo preservando uma seleção múltipla existente; sobre área vazia limpa a seleção, e cabeçalhos não abrem ações de item. Shift+F10 e a tecla Menu abrem as mesmas opções. Estados e ações são reaproveitados dos controles das abas.

Passaram 24 testes de PC sem ignorados: nove novos cenários de contexto, sete de cards/fila, seis de tradução e dois de persistência. As verificações incluem copiar, remover, reordenar, estados indisponíveis, cards, teclado, clique direito, menus de janelas auxiliares e rótulos nos dois idiomas. Build release Android e cinco testes unitários passaram para manter os catálogos compartilhados alinhados. Logs: list-context-*.
