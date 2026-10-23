# Fila, biblioteca e ferramentas

## Formato por música e miniplayers no PC — 1.2.0

Na pesquisa, Baixar agora abre formato e qualidade, com a preferência de Álbuns e playlists selecionada. MP3 e M4A oferecem os bitrates compatíveis; FLAC e áudio original não mostram bitrate de recodificação. A janela preserva a faixa escolhida mesmo se a lista de pesquisa mudar. Confirmar baixa ou adiciona à fila; Voltar/Esc cancela. A seleção explícita não é substituída pelo modo simplificado de downloads e não altera as preferências globais.

Efeitos e Jukebox compartilham o desenho do miniplayer, mantendo controles, filas, volume e letras independentes. Ambos permanecem visíveis ao minimizar o ONDA. A opção de minimizar ao abrir está em Aparência. O cabeçalho inteiro, incluindo capa e dados da faixa, permite arrastar; os botões de fixar, restaurar, minimizar e fechar continuam interativos.

Os recursos abaixo estão disponíveis no Windows e no Android. Agendamento, retomada automática da fila e verificação de atualização ao abrir são opcionais; a retomada de arquivos interrompidos vem ativada. A fila já existente continua preservada.

## Fila e downloads

- **Downloads simultâneos:** escolha de 1 a 15 no PC ou de 1 a 4 no Android. No PC, os valores mais altos aumentam o consumo de memória, CPU e rede; reduza se houver lentidão. As perguntas de versão, metadados e duplicados continuam sendo apresentadas uma por vez.
- **Retomar arquivos interrompidos quando possível:** mantém os arquivos parciais de cada tarefa e solicita a continuação ao servidor. Depende do suporte da origem; URLs temporárias ou servidores sem retomada podem exigir novo download.
- **Retomar fila ao abrir o ONDA:** inicia os pendentes ao abrir o app. Quando o agendamento está ativado, a janela de horários é respeitada.
- **Mover acima / abaixo / Próximo:** muda a ordem dos itens pendentes. Os downloads em andamento continuam; a ordem é salva para a próxima abertura.
- **Normalizar volume dos próximos downloads:** checkbox que aplica normalização em duas passagens, com alvo de −16 LUFS e pico verdadeiro de −1,5 dBTP, aos arquivos de áudio compatíveis. Áudios em silêncio são preservados. Não modifica o volume de vídeos.

No PC, essas opções ficam em **Configurações → Geral**, e o checkbox de normalização também está em **Links e fila**. No Android, ficam em **Configurações → Downloads**. Itens já adicionados guardam suas opções de processamento; escolha a normalização antes de adicionar novos itens.

## Exibição da fila e do histórico

Em **Links e fila**, os controles discretos da própria aba alternam entre compacto e completo e ajustam o tamanho dos cards. O modo completo mostra capa, artista, álbum, duração e demais informações disponíveis. Imagens e dados são carregados em segundo plano; fontes sem esses dados mantêm as informações básicas do item.

No **Histórico**, Limpar histórico, visualização e tamanho ficam lado a lado, centralizados abaixo da pesquisa. Os tamanhos da fila e do histórico são independentes. No PC, **Ctrl + roda do mouse** ajusta os cards da aba ativa. As opções de exibição também ficam em Aparência; ative Lembrar configurações para mantê-las ao reabrir.

## Idioma e reinício

A ordem é **Português (Brasil) | Español | English**, com português como padrão. No PC, **Reiniciar** aparece abaixo de Idioma apenas enquanto há uma mudança pendente. Voltar ao idioma atual remove a pendência. A fila é preservada no reinício; operações em andamento precisam terminar antes. No Android, idioma e aparência são aplicados imediatamente. O nome ONDA e os nomes originais de músicas, artistas, álbuns e arquivos não são traduzidos.

## Editar um áudio já baixado e importar letra

No **Histórico**, use **Editar áudio / letra** na lista do Windows ou **Editar metadados** nos cards de áudio compatíveis. O arquivo é aberto na aba de edição das duas versões.

O checkbox **Editar metadados** permite alterar título, artistas, álbum, gênero, data e capa. Desmarque para conservar esses dados. **Normalizar volume** é independente: pode ser usado sozinho. **Ouvir original** e **Ouvir normalizado** permitem comparar uma prévia de até 20 segundos antes de salvar.

Importe uma letra **TXT ou LRC**, de até 1 MB. A letra é incorporada nas tags; um LRC também é salvo ao lado da cópia. A exibição sincronizada depende do player. O ONDA não busca letras automaticamente.

**Salvar cópia editada** mantém o arquivo original. A cópia recebe o sufixo “ - Editada”. No PC, fica ao lado do original; no Android, usa a pasta de destino configurada. Tags não alteradas e a capa existente são preservadas. São aceitos MP3, M4A, FLAC, WAV, OGG e OPUS. A normalização recodifica o áudio; em formatos com perdas, isso representa uma nova compressão. Exportar em FLAC não recupera qualidade que a fonte já perdeu.

## Agendar downloads

Ative **Agendar downloads** e informe **Começar** e **Parar**, no formato HH:MM. A janela é diária e pode atravessar a meia-noite, por exemplo 22:00–07:00. Os horários precisam ser diferentes.

No Windows, o PC precisa estar ligado e o ONDA aberto. O aplicativo verifica a janela a cada 15 segundos. Ao terminar o horário, interrompe a fila e deixa os itens pendentes para continuar quando possível.

No Android, o agendamento usa WorkManager com conexão de rede. Economia de bateria, limites do sistema e ações como Forçar parada podem atrasar ou impedir a execução. Não é um alarme de horário exato. O usuário pode continuar a fila manualmente; a janela limita a execução agendada.

## Atualizações e transferência de preferências

**Verificar atualização do ONDA** consulta as Releases oficiais do projeto e compara a versão do instalador Windows ou APK Android. A consulta ao abrir é opcional. Se houver uma versão mais recente, o botão abre o download oficial no navegador. A instalação permanece sob controle do usuário e do sistema; o ONDA não executa instaladores silenciosamente. Só são detectadas versões publicadas com número superior ao atual.

**Exportar configurações** salva um JSON com as preferências compatíveis entre as plataformas: aparência, formato/qualidade, organização, limite de playlist e opções avançadas de fila/agendamento. **Importar configurações** aplica essas preferências no outro ONDA. Contas, tokens, cookies, histórico, fila, arquivos e caminhos de pastas não são transferidos. Recursos específicos de uma plataforma permanecem locais.

## Conferência rápida

1. Escolha dois downloads simultâneos, adicione três mídias autorizadas e confira dois itens processando enquanto o terceiro aguarda.
2. Interrompa uma mídia, tente novamente e confira a mensagem de retomada quando o servidor oferecer suporte.
3. Mova um pendente para Próximo, reabra o app e confira a ordem.
4. No histórico, edite apenas o título de uma cópia com capa, importe LRC e confira original, cópia e letra em um player compatível.
5. Compare a prévia original e normalizada. Faça uma cópia usando somente o checkbox de normalização.
6. Configure uma janela curta e confira início, parada e itens pendentes. No Android, mantenha o teste sem economia de bateria e aceite possíveis atrasos do sistema.
7. Exporte as preferências, importe na outra plataforma e confira que nenhuma credencial ou pasta foi incluída.


### Salvar a edição no arquivo original

No editor de áudio/metadados, ative **Sobrescrever arquivo original** e use **Salvar no original** para manter o nome e a pasta do arquivo. Desativado, **Salvar cópia editada** continua preservando o original. A opção também vale para normalização e letra quando selecionadas.

No PC, a edição é preparada em um arquivo temporário e substituída ao terminar. No Android, a gravação usa o mesmo URI do histórico, exige permissão de escrita e mantém uma cópia de segurança durante a substituição. Se o original tiver mudado desde a abertura do editor, reabra-o antes de salvar.

### Metadados e capas de coleções

- A aba Metadados abre arquivos locais sem exigir um download ou uma entrada no histórico. O atalho de edição do Histórico continua disponível.
- O editor aceita MP3, M4A, FLAC, WAV, OGG e OPUS; preserva o original por padrão e permite salvar no mesmo arquivo quando há permissão de escrita.
- Álbuns e playlists exibem um cartão com capa, título, artista ou criador e quantidade de músicas; listas sem capa mostram um símbolo de música. A ordem configurada das abas é preservada ao acrescentar Metadados.

### Recuperação da conexão FLAC

- Monochrome: até seis tentativas para transferir a faixa e quatro para consultar o catálogo; espera progressiva e respeito a Retry-After. Recusas HTTP 401/403 recebem somente uma nova solicitação, sem contornar restrições do serviço.
- Quedas durante a transferência retomam os bytes restantes quando o servidor fornece um identificador seguro do arquivo. Se o servidor ignorar a retomada ou mudar o arquivo, a transferência recomeça sem misturar trechos.
- O arquivo só é publicado após a transferência completa e as validações do FLAC. Bloqueios persistentes e indisponibilidade do serviço ainda podem impedir o download.

### Editor de metadados na página

- A aba se chama Editar metadados nas duas versões. No Android, o formulário fica na própria página; o Histórico abre o arquivo nessa aba e os campos são preservados ao navegar entre abas.
- Android: capa em uma área central de destaque, com prévia e Desfazer capa. PC: capa maior na área inferior direita do editor, com rolagem para telas menores.

## Desinstalação no Windows — 1.2.0

Em Aplicativos do Windows ou no atalho Desinstalar ONDA, a janela própria oferece **Apagar configurações, fila e histórico** e **Remover ferramentas baixadas (FFmpeg)**. As duas opções vêm desativadas e são independentes. Dados compartilhados com o portátil só são removidos se você marcar a opção correspondente. Downloads, cookies externos e ferramentas de outras pastas são preservados. Cancelar fecha sem remover; depois de confirmar, aguarde a conclusão. Consulte [o funcionamento e os testes](docs/INSTALADOR-WINDOWS.md).
