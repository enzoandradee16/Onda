# Roadmap do ONDA

Recursos selecionados para futuras versões, organizados em uma sequência sugerida de implementação. Os itens marcados foram implementados na 1.1.4; os demais serão considerados para a 1.1.5. Os itens desmarcados não representam funcionalidades concluídas. As etapas podem mudar conforme testes, necessidades e limitações das plataformas, sem compromisso de prazo ou versão.

## 1 — Controle da fila

- [x] **Busca e filtros na fila — PC e Android:** pesquisar músicas e filtrar por estado, como pendentes, em andamento, concluídas e com erro.
- [ ] **Indicador de atividade por item e motivo de espera — PC e Android:** distinguir consulta de metadados, busca de áudio, download, conversão e espera por conexão, horário ou escolha do usuário.
- [ ] **Escolher a ordem de execução — PC e Android:** manter a ordem original ou ordenar por critérios disponíveis, como duração e tamanho estimado.
- [ ] **Arrastar para reordenar — PC e Android:** alterar a ordem com o mouse ou pressionando e arrastando no celular, preservando alternativas acessíveis.
- [ ] **Estimar espaço necessário — PC e Android:** mostrar uma estimativa antes de iniciar e avisar quando o armazenamento disponível parecer insuficiente.

## 2 — Uso diário e execução em segundo plano

- [ ] **Somente Wi-Fi — Android:** permitir que os downloads aguardem uma conexão Wi-Fi e definir o comportamento quando a rede mudar.
- [ ] **Ação ao terminar — PC e Android:** oferecer ações compatíveis com cada plataforma, como som e notificação; no PC, avaliar desligamento com confirmação e contagem regressiva cancelável.
- [ ] **Escolher o comportamento ao fechar — PC:** permitir encerrar ou minimizar para a bandeja do sistema, com acesso para restaurar e sair do aplicativo.
- [ ] **Notificação de progresso — PC:** mostrar o andamento na barra de tarefas e avisar sobre a conclusão da fila.
- [ ] **Controles na notificação — Android:** oferecer ações para controlar a fila e abrir o aplicativo, respeitando as regras de execução em segundo plano do sistema.

## 3 — Biblioteca, playlists e origem

- [ ] **Atualizar uma playlist já baixada — PC e Android:** comparar com a coleção anterior e adicionar as faixas novas ou ausentes, sem baixar tudo novamente.
- [ ] **Conferir playlist × arquivos locais — PC e Android:** identificar músicas presentes, ausentes e casos que exigem revisão.
- [x] **Abrir a origem pelo histórico — PC e Android:** acessar a página original da faixa ou publicação, quando a origem estiver registrada.
- [x] **Ícone da plataforma dos metadados — PC e Android:** mostrar um pequeno ícone da fonte dos metadados e identificar complementações de outros catálogos, sem confundir com a fonte do áudio.

## 4 — Arquivos locais e integração

- [ ] **Letra sincronizada — PC e Android:** importar e acompanhar letras LRC durante a reprodução. Avaliar separadamente a busca automática de letras, suas fontes e permissões.
- [ ] **Conversão de áudio em lote — PC e Android:** converter vários arquivos locais com escolha de formato, qualidade e destino, preservando metadados quando o formato permitir.
- [x] **Conversão de vídeos — PC e Android:** aba Conversor com MP4, MKV e MOV, H.264/AAC, qualidade e resolução máxima, progresso e cancelamento. Preserva o original e exporta o vídeo com a primeira faixa de áudio. Disponível na 1.1.4; remux sem recodificação e outros codecs ficam para evolução futura.
- [ ] **Arrastar arquivos para o ONDA — PC:** encaminhar arquivos locais ao editor, conversor ou efeitos, conforme o tipo e a escolha do usuário.
- [ ] **Fila por arrastar links — PC:** receber links arrastados do navegador e oferecer sua inclusão na fila.
- [ ] **Integração com Compartilhar — PC:** avaliar o registro e o empacotamento necessários para receber links ou arquivos pelo compartilhamento do Windows.

## 5 — Personalização, acessibilidade e manutenção

- [ ] **Atalhos personalizáveis — PC:** permitir alterar combinações, detectar conflitos e restaurar os padrões, preservando a edição de texto e o uso de diálogos.
- [x] **Pesquisa nas configurações — PC e Android:** localizar opções pelo nome e pela descrição e abrir a categoria correspondente.
- [ ] **Modo de alto contraste — PC e Android:** melhorar contraste, bordas, seleção e foco; não depender apenas da cor para comunicar estados.
- [x] **Limpeza de cache pelo aplicativo — PC e Android:** mostrar o espaço ocupado e permitir uma limpeza seletiva, preservando downloads, trabalhos ativos e parciais necessários para retomada.

- [ ] **Configurações de desempenho — PC:** criar uma nova aba "Desempenho" nas configurações para escolher quanto processamento o ONDA pode usar e ajustar o consumo de CPU e RAM conforme a quantidade de downloads e os recursos disponíveis. Prever controles de paralelismo, threads de conversão e uso de memória, permitindo priorizar menor consumo ou maior desempenho; avaliar limites tecnicamente viáveis, sem prometer reservar RAM ou garantir um percentual exato de CPU.

- [ ] **Identificação do processo no Windows — PC:** ajustar o empacotamento para o aplicativo aparecer com nome e ícone do ONDA no Gerenciador de Tarefas, em vez de ser identificado como Python. Validar o agrupamento da janela, o iniciador e os processos auxiliares nas versões instalada e portátil, preservando o runtime incluído e a compatibilidade das atualizações.

- [ ] **Ícone consistente nas janelas — PC:** investigar e corrigir a aparição temporária do ícone padrão do Tkinter no Gerenciador de Tarefas e na barra de tarefas. Aplicar o ícone do ONDA antes da exibição das janelas e conferir diálogos, janelas auxiliares, recriação de janelas e mudanças de tema, nas versões instalada e portátil.

## Critérios para implementar

- Manter as interfaces simples; usar menus de contexto e opções avançadas quando fizer sentido.
- Preservar fila, histórico, arquivos e preferências existentes durante atualizações.
- Conferir a identidade das músicas por origem e metadados, sem depender apenas do nome do arquivo. Distinguir gravações e edições diferentes.
- Oferecer alternativas ao arrastar para usuários de teclado, TalkBack e outros mecanismos de acessibilidade.
- Traduzir textos e descrições acessíveis em português, espanhol e inglês.
- Validar filas grandes, cancelamento, falhas e persistência nas plataformas afetadas.
- Ao concluir um item, marcar a caixa e registrar sua versão no changelog. Implementações parciais devem indicar claramente o que ainda falta.
