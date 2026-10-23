# Correções da revisão de 22/10/2026

Base: `418601951bc61ab0d33b72e2b56e6db77586032b` (`master`).

## Alterações implementadas

| Item | Correção | Cobertura de regressão |
| --- | --- | --- |
| ONDA-001 | Execuções imediatas têm escopo por IDs. Novos pedidos ampliam o escopo sem iniciar pendências alheias. Confirmações de espaço e duplicata preservam a seleção. Playlists verificam espaço uma vez por lote. | `test_qt_regressions`: pedidos imediatos, vagas ocupadas, fila global, confirmação, botão Links e lote de playlist. |
| ONDA-002 | Seleção de cookies centralizada por origem, compartilhada pelo desktop Qt e pela interface legada. | `test_download_cookies` e configuração enviada ao worker real do controlador. |
| ONDA-003 | Itens pendentes passam imediatamente a Pausado. Retomadas limpam marcadores antigos e aguardam o encerramento de um worker que ainda está cancelando. | Pausa antes de iniciar, retomada selecionada e retomada durante cancelamento. |
| ONDA-004 | Motivos de pausa manual e por horário são distintos e persistidos. O agendador só retoma suas próprias pausas. | Janela de horário fechando/reabrindo, escopo e persistência dos motivos. |
| ONDA-005 | A conclusão exige trabalho efetivamente iniciado e terminado; uma fila vazia, interrompida ou com itens pausados não dispara a ação de conclusão. | Último item pausado, retomada, fila vazia e parada global. |
| ONDA-006 | Movimento estável em tempo linear; priorização preserva a ordem dos selecionados. | Seleções contíguas, separadas e junto às bordas. |
| ONDA-007 | Limpar credenciais antes persistidas remove o segredo do cofre. Por preferência do usuário, o botão de remoção continua visível somente quando conectado; limpar os campos também remove o segredo persistido. | Reabertura do controlador com cofre simulado e presença do botão no QML. |
| ONDA-008 | Atualizadores Qt e legado usam `Onda/app_version.py`. Gerador sincroniza os metadados Windows. | Release igual à instalada, metadados dos pacotes e geração idempotente. |
| ONDA-009 | Prévia Android tem Job cancelável, ID de backend e geração. Parar, trocar a prévia e fechar a seleção invalidam respostas antigas. | Quatro testes JVM de cancelamento, resposta fora de ordem e erros antigos/atuais. |
| ONDA-010 | Atalhos têm Desativar e Restaurar individuais; Enter inicia a captura por teclado. | Persistência do override e interação real com os controles QML. |
| ONDA-011 | Restauração preserva o estado normal, maximizado ou tela cheia anterior à minimização. | QWindow real, ocultação e minimização. |
| ONDA-012 | 96 entradas adicionadas em cada catálogo EN/ES. Testes listam ausências em conjunto e também cobrem chamadas literais do QML. | Completude, paridade, placeholders e traduções existentes. |

As expectativas antigas dos testes de preferências foram alinhadas ao contrato atual de `confirm_version=False`. Não foram adicionadas dependências ao aplicativo.

## Validação relatada pelo chat de origem (antes da integração local)

- Suíte Python em processos separados, conforme o padrão do projeto: **114 módulos**, **862 casos informados**, **540 aprovados**, **313 ignorados**, **zero falhas de asserção** e **9 erros de ambiente** em 5 módulos.
- Rodada direcionada com Qt habilitado: **51/51 testes aprovados**. Inclui 23 regressões novas do controlador, testes existentes de QML/player/ícones e testes de versão/cookies.
- Kotlin 2.1.21 + coroutines 1.10.2 + JUnit 4.13.2: compilação do controlador de solicitações de prévia e **4/4 testes aprovados**.
- Análise sintática dos arquivos Python e `git diff --check` aprovados.

Os números das rodadas não devem ser somados, pois há testes reexecutados.

### Limites do ambiente

Os nove erros da suíte ampla são os mesmos tipos de dependência do ambiente observados na revisão: cinco casos exigem APIs Windows/DPAPI (`test_clipboard_links`, `test_jukebox`, `test_playlist_account`) e quatro exigem display Tk (`test_enter_search`, `test_interface_fonts`). Os testes Qt usaram Linux/offscreen. O cofre de credenciais foi simulado nos testes de remoção.

Os testes Kotlin executaram a lógica de concorrência na JVM. Não houve build completo do APK, teste instrumentado em aparelho, execução do instalador Windows nem teste real de download nas plataformas externas. Esses passos permanecem como validação de integração antes de distribuir novos binários.

## Versão dos pacotes Windows

A fonte de versão é `Onda/app_version.py`. Ao preparar uma versão nova, atualizar essa constante e executar, a partir da raiz:

```text
python empacotamento/sync_version.py
```

O script atualiza `Launcher.cs` e `Onda.iss`, incluindo a versão numérica de quatro componentes. `build_package.py` também executa essa sincronização. Compilar o launcher e o instalador após sincronizar. O teste `test_app_version` impede divergências nos metadados versionados.

## Repetir as verificações direcionadas

No ambiente Python do desktop, a partir de `Onda`, habilitar `ONDA_QT_TESTS=1` e executar:

```text
python -m unittest test_qt_regressions test_app_version test_download_cookies test_localization_completeness
python -m unittest test_qt_workspace.NativeDesktopTests.test_shortcut_recorder_captures_keys_without_editing_text test_qt_workspace.NativeDesktopTests.test_account_buttons_and_tools_progress_in_qml
```

Em Linux sem display, definir também `QT_QPA_PLATFORM=offscreen`. A suíte ampla deve continuar sendo executada por módulo em processos separados, como orienta o README.

Com o ambiente Android configurado, executar o teste `br.com.onda.mobile.PreviewRequestTest` em `:app:testDebugUnitTest` e a suíte instrumentada antes de distribuir o APK.
