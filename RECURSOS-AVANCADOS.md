# Fila, biblioteca e ferramentas

Os recursos abaixo estão disponíveis no Windows e no Android. As opções novas ficam desativadas por padrão, exceto a retomada de arquivos interrompidos. A fila já existente continua preservada.

## Fila e downloads

- **Downloads simultâneos:** escolha de 1 a 4 nas configurações. As perguntas de versão, metadados e duplicados continuam sendo apresentadas uma por vez.
- **Retomar arquivos interrompidos quando possível:** mantém os arquivos parciais de cada tarefa e solicita a continuação ao servidor. Depende do suporte da origem; URLs temporárias ou servidores sem retomada podem exigir novo download.
- **Retomar fila ao abrir o ONDA:** inicia os pendentes ao abrir o app. Quando o agendamento está ativado, a janela de horários é respeitada.
- **Mover acima / abaixo / Próximo:** muda a ordem dos itens pendentes. Os downloads em andamento continuam; a ordem é salva para a próxima abertura.
- **Normalizar volume dos próximos downloads:** checkbox que aplica normalização em duas passagens, com alvo de −16 LUFS e pico verdadeiro de −1,5 dBTP, aos arquivos de áudio compatíveis. Áudios em silêncio são preservados. Não modifica o volume de vídeos.

No PC, essas opções ficam em **Configurações → Geral**, e o checkbox de normalização também está em **Links e fila**. No Android, ficam em **Configurações → Downloads**. Itens já adicionados guardam suas opções de processamento; escolha a normalização antes de adicionar novos itens.

## Editar um áudio já baixado e importar letra

No **Histórico**, selecione **Editar áudio / letra**. No Windows, o botão abre o editor do arquivo selecionado. No Android, ele aparece nos cartões de áudio compatíveis.

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
