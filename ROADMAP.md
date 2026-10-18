# Roadmap do ONDA

Recursos selecionados para futuras versões, organizados em uma sequência sugerida de implementação. Os itens marcados foram implementados na 1.1.4 ou no código da 1.1.5; os demais ficam para versões futuras. O portátil local e o APK 1.1.5 já incluem as correções e o alto contraste. O portátil também inclui as configurações de desempenho e suas últimas melhorias; o instalador e os arquivos da pasta Release não foram atualizados nesta rodada. Os itens desmarcados não representam funcionalidades concluídas. As etapas podem mudar conforme testes, necessidades e limitações das plataformas, sem compromisso de prazo ou versão.

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

- [x] **Reconhecimento de links copiados — PC e Android (1.1.5):** identificar links compatíveis e pedir confirmação antes de baixar, sem repetir avisos para o mesmo link na sessão. Preferência ativada por padrão; no Android, a verificação ocorre com o aplicativo em primeiro plano.

## 3 — Biblioteca, playlists e origem

- [x] **Atualizar uma playlist já baixada — PC e Android (1.1.5):** recarregar a coleção pela origem, comparar com arquivos locais, histórico e a conferência anterior persistida, indicar faixas novas e oferecer Adicionar ausentes à fila. Não inclui automaticamente itens presentes, duvidosos ou já na fila; não inicia downloads sem a ação do usuário. Implementado e testado no código; pacotes ainda não atualizados.
- [x] **Conferir playlist × arquivos locais — PC e Android (1.1.5):** conferir a pasta escolhida e os arquivos registrados no histórico completo; distinguir Presente, Ausente, Revisar e Na fila com motivo e caminho. Usar origem registrada ou metadados consistentes (título, artistas, álbum e duração), sem confirmar apenas pelo nome do arquivo. Android usa o seletor de pastas e as permissões de acesso existentes. Compartilha o motor de comparação com o PC; pacotes ainda não atualizados.
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

- [x] **Mostrar ou ocultar abas — PC e Android (1.1.5):** escolher individualmente as abas visíveis, preservar as essenciais e salvar a preferência.
- [x] **Controles simplificados de download — PC e Android (1.1.5):** ocultar opções de formato e qualidade sem alterar o espaçamento. Respeitar o formato definido em Downloads e utilizar a qualidade máxima compatível.
- [x] **Qualidade máxima para redes sociais — PC e Android (1.1.5):** opção independente dos controles simplificados, ativada por padrão para Instagram, TikTok e Kwai.
- [x] **Seleção automática de mídias — PC e Android (1.1.5):** selecionar todas as fotos e vídeos por padrão, permitir desmarcar individualmente, alternar entre selecionar e desmarcar todas e desativar o comportamento nas configurações.
- [x] **Atalhos personalizáveis — PC (1.1.5):** editar ou desativar os atalhos de ações e navegação pela janela Atalhos, também acessível em Aparência; validar conflitos, preservar combinações de edição de texto e do sistema, salvar preferências e restaurar padrões.
- [x] **Pesquisa nas configurações — PC e Android:** localizar opções pelo nome e pela descrição e abrir a categoria correspondente.
- [x] **Modo de alto contraste — PC e Android (1.1.5):** disponível em Aparência, com fundo preto, textos brancos, destaque amarelo, contornos visíveis e seleção contrastante. No PC, reforça bordas e foco; mantém os textos de estado existentes. Preferência salva pelo sistema atual; incluído no portátil e no APK locais. Funcionamento no portátil confirmado pelo usuário.
- [x] **Limpeza de cache pelo aplicativo — PC e Android:** mostrar o espaço ocupado e permitir uma limpeza seletiva, preservando downloads, trabalhos ativos e parciais necessários para retomada.

- [x] **Configurações de desempenho — PC (1.1.5):** nova categoria Desempenho com downloads simultâneos (controle existente compartilhado), threads por conversão limitadas à quantidade de processadores lógicos detectados, prioridades Baixa/Normal/Acima do normal e limiar de RAM livre para iniciar novos downloads. Valores de threads salvos acima da capacidade detectada são ajustados automaticamente. A fila aguarda e retoma automaticamente quando há memória disponível; Parar cancela a espera sem perder os itens. Preferências persistidas e restauráveis, com textos em português, inglês e espanhol. Não reserva RAM nem impõe um percentual exato de CPU; mudanças de threads/prioridade valem para novas tarefas. Implementado, testado e incluído no portátil local atualizado, com autoteste de inicialização aprovado.

- [x] **Identificação do processo no Windows — PC (1.1.5):** o iniciador executa o runtime incluído dentro do próprio Onda.exe, identificando o processo principal como Onda em vez de Python. Abertura da interface, ícone, argumentos e subprocesso auxiliar validados; tarefas auxiliares continuam usando o interpretador incluído. Iniciador do portátil atualizado; o instalador receberá a mudança na próxima compilação.

- [ ] **Ícone consistente nas janelas — PC (parcial na 1.1.5):** a janela principal agora recebe o mesmo ícone do executável antes de aparecer, mantendo os ícones funcionais dos diálogos. Testes de interface e mudanças de tema passaram. O portátil foi atualizado e passou no autoteste de inicialização. Falta conferir visualmente o comportamento no Gerenciador de Tarefas e na barra de tarefas, incluindo recriação de janelas, e validar o próximo instalador recompilado.

## Correções recentes — 1.1.5

- Formato das configurações respeitado no modo simplificado, no PC e Android.
- Cor do texto do campo “Máximo de itens por playlist” corrigida nos temas escuros do PC.
- Descrição de “Ferramentas e atualizações” atualizada no Android, com traduções.
- Ícone principal alinhado ao executável desde a abertura; validação dos pacotes ainda pendente, conforme item acima.
- Validação das correções iniciais: 18 testes focados do PC aprovados. Alto contraste e atalhos também passaram nos testes focados; APK de distribuição compilado e assinado com o certificado original.
- Desempenho: testes de espera/retomada por RAM, cancelamento, persistência, conversão real, detecção de processadores lógicos e prioridade Acima do normal aprovados. Portátil sincronizado com os arquivos atuais e inicialização validada.
- Nenhum instalador novo, commit, push ou publicação foi feito nesta rodada.

## Critérios para implementar

- Manter as interfaces simples; usar menus de contexto e opções avançadas quando fizer sentido.
- Preservar fila, histórico, arquivos e preferências existentes durante atualizações.
- Conferir a identidade das músicas por origem e metadados, sem depender apenas do nome do arquivo. Distinguir gravações e edições diferentes.
- Oferecer alternativas ao arrastar para usuários de teclado, TalkBack e outros mecanismos de acessibilidade.
- Traduzir textos e descrições acessíveis em português, espanhol e inglês.
- Validar filas grandes, cancelamento, falhas e persistência nas plataformas afetadas.
- Ao concluir um item, marcar a caixa e registrar sua versão no changelog. Implementações parciais devem indicar claramente o que ainda falta.
