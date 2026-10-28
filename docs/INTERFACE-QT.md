# Interface Qt do ONDA para Windows

## Interface atual — 1.2.3

Guia revisado em 27/10/2026. Para os recursos completos, consulte o [inventário](INVENTARIO-FUNCIONALIDADES.md).

A pesquisa abre a escolha de formato ao solicitar Baixar agora: MP3, M4A, FLAC ou original, com qualidade compatível, padrão salvo e confirmação para iniciar ou enfileirar. Cancelar não cria uma tarefa. O componente `DownloadFormatPopup.qml` usa a fila de decisões do controlador e impede a exibição simultânea do diálogo genérico.

`MiniPlayer.qml` implementa os dois miniplayers; `EffectsMiniPlayer.qml` configura o modo Efeitos. As janelas são independentes da principal, com área de arraste em todo o cabeçalho. As letras consultam explicitamente o player correspondente, mesmo ao trocar a aba principal. A abertura consulta a preferência atual no controlador Qt.

Execute `Portatil/Onda.exe`. Todas as áreas visíveis usam Qt Quick/QML: catálogo, links, fila, álbuns e playlists, histórico, conversor, imagens, efeitos, Jukebox, metadados, configurações e diálogos. Não existe incorporação de janelas Tk nem processo de interface auxiliar.

## Estrutura

- `qt_desktop_ui.py`: inicialização, ícone, runtime e instância única.
- `qt_workspace_ui.py`: controlador Qt, preferências existentes, fila e tarefas assíncronas, confirmações, atalhos, clipboard, bandeja e progresso no Windows.
- `qt_models_ui.py`: listas com atualização individual das linhas.
- `qt_operations_ui.py`: adaptadores para os motores existentes de busca, playlists, áudio, imagens e ferramentas.
- `qt_jukebox_ui.py` e `qt_graph_ui.py`: reprodução e visualização do Jukebox.
- `qml/`: componentes, telas e diálogos Qt Quick.
- `settings_schema/desktop.json`: opções e padrões extraídos das configurações existentes, sem executar a interface antiga.

As tarefas de download continuam executando `engine.py` em processos isolados, com o mesmo protocolo de eventos e respostas. Exportação de efeitos usa `effects_worker.py`. Conversões e edições locais reutilizam os serviços Python compartilhados. Esses processos não criam janelas Tk.

O código da interface anterior permanece no projeto para compatibilidade e comparação; ele não é iniciado pelo portátil Qt. O Android permanece no sistema de interface existente.

## Dependências e compilação

O portátil inclui PySide6 Essentials e Shiboken em `_runtime/qt`. Não exige instalação separada de Python ou Qt. FFmpeg usa o mecanismo existente de preparação e cache. As licenças originais dos componentes acompanham o pacote.

Para executar pelo código:

```powershell
& '.\Portatil\_runtime\python\python.exe' -m pip install --target '.venv/qt-packages' -r 'Onda/requirements-qt.txt'
& '.\Portatil\_runtime\python\pythonw.exe' 'Onda/qt_desktop_ui.py'
```

O launcher existente aceita `/define:QT_UI`. Sem essa definição, continua iniciando a interface anterior. A pasta `Portatil` contém o runtime, o Qt, os fontes e o executável; mantenha-os juntos.

## Validação

`test_qt_workspace.py` cobre configuração, listas, escolhas, cancelamento, leitura e edição, conversão real, imagens, recorte, efeitos, todas as telas e diálogos, e download pelo motor real em servidor HTTP local. `test_qt_jukebox.py` cobre análise, reprodução, equalizador e visualização. Não são necessários serviços públicos para executar esses testes.

## Reprodução e fila

- No Jukebox, adicione arquivos ou resultados de pesquisa à fila. Use Tocar, Próxima ou escolha um tempo por faixa; Manual mantém o comportamento infinito até uma troca manual. A fila de reprodução vale para a sessão atual.
- O temporizador do Jukebox usa tempo corrido e reduz o áudio nos últimos 15 segundos, sem modificar o volume escolhido nem o equalizador.
- Em Links/Fila, Desfazer recupera até dez remoções, limpezas, cancelamentos e mudanças de ordem. Não apaga arquivos nem volta o progresso de downloads em andamento. Aguarde o término de um cancelamento antes de desfazê-lo.
- No Conversor, Detectar silêncio analisa o áudio abaixo de −45 dB por ao menos 0,3 segundo. A remoção opcional corta somente as extremidades; pausas internas e o arquivo original são preservados. A análise é reutilizada enquanto tamanho e data do arquivo permanecem iguais.

Na pesquisa de músicas, Adicionar à fila permite escolher entre downloads e reprodução no Jukebox. As duas filas mostram capa e metadados disponíveis. Em Links/Fila, o menu Mais ações reúne movimentação, prioridade, nova tentativa, cancelamento, limpeza, falhas e detalhes; os controles principais continuam visíveis.
