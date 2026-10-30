# Reprodução remota PC ↔ Android

Implementação de teste atualizada em 30/10/2026. O computador reproduz a música e aplica os efeitos; o Android representa essa reprodução no player, na fila e na sessão de mídia do sistema. Não há transmissão de áudio para o celular.

## Conectar

1. Atualize o portátil e o APK com os pacotes desta implementação. O Android verifica a compatibilidade do PC ao parear.
2. Conecte o PC e o celular à mesma rede local confiável.
3. No PC, abra **Reprodução → Controle remoto → Ativar controle remoto**.
4. No Android, abra **Mais → Controlar ONDA no PC**.
5. No painel **Dispositivos**, selecione o computador encontrado e digite o código de seis dígitos exibido nele. Se ele não aparecer, use **Conectar computador** e informe o endereço completo, incluindo a porta.
6. Ao conectar, o Android abre o player remoto. A reprodução local do celular fica parada na posição salva.

Se o Windows solicitar acesso à rede para o ONDA, permita na rede privada usada no teste. Redes de convidados podem impedir a comunicação entre aparelhos. Não é necessário encaminhar portas no roteador.

## Controles integrados

- A barra inferior mostra a capa, a música, o artista, os tempos e a indicação **Reproduzindo no computador**.
- Tocar na barra abre o player expandido, com posição ajustável, ordem aleatória, repetição, controles e acesso à fila. A página Reprodução também passa a mostrar o PC conectado.
- O acesso a dispositivos aparece no player local e no remoto. O painel abre de baixo para cima, destaca o dispositivo atual e concentra o volume do computador. O atalho Bluetooth abre os ajustes do telefone.
- A fila vem do computador. É possível reproduzir uma faixa, removê-la e movê-la para cima ou para baixo. Filas grandes usam páginas de 100 músicas e a ação **Carregar mais**.
- A fila do computador usa a página e o painel normais do Android, com **Fila / Tocado recentemente**, animação das abas, reordenação por arraste e gesto de remover. A barra abre a página da fila; o player expandido abre o painel por baixo.
- A pesquisa da fila e da página Reprodução usa o catálogo e as contas do PC. Os resultados podem ser adicionados individualmente; álbuns e playlists também oferecem **Adicionar todas à fila**. O celular envia identificadores de resultados, sem enviar arquivos ou preparar áudio localmente.
- Em Reprodução, os controles remotos ajustam ativação dos efeitos, preset, velocidade, reverb, manter tom, Jukebox infinito, variação e transição suave. Alterações no PC aparecem no celular. Os sliders enviam o valor ao soltar, evitando iniciar uma preparação por movimento.
- A notificação e a tela bloqueada usam uma sessão de mídia remota, com metadados, capa, posição e comandos encaminhados ao PC. A apresentação dos controles depende da versão do Android.
- Os botões de volume controlam o computador enquanto a sessão remota está selecionada.
- Fechar a tela de pareamento, recolher o player ou minimizar o ONDA não encerra a conexão. O serviço mantém o controle e a notificação em segundo plano.

## Desconectar e reconectar

- No player, abra **Dispositivos → Este telefone**, ou use a ação de desconectar na notificação. O áudio continua no PC; a música local do celular não é retomada automaticamente. Essa seleção não transfere músicas entre os aparelhos.
- **Desativar e desconectar**, no PC, encerra o servidor e invalida a sessão.
- Em interrupções breves, o Android tenta recuperar a conexão. Após cerca de 90 segundos sem resposta, encerra a sessão para evitar manter o serviço indefinidamente.
- As credenciais ficam somente em memória e permitem retornar a um PC pareado durante a mesma sessão. Se o processo Android for encerrado pelo sistema ou pelo usuário, ou o servidor do PC reiniciar, faça um novo pareamento. Apenas nome e endereço do último dispositivo ficam salvos; **Esquecer dispositivo** remove esse registro e a credencial da memória.
- Iniciar uma reprodução local no Android também encerra o controle remoto.

## Limites atuais

Descoberta automática por UDP na porta 45847, somente enquanto o painel está aberto. O PC responde apenas quando o controle remoto está ativado, sem transmitir código, credencial ou metadados de músicas. Bloqueios de broadcast ou da porta não impedem o pareamento manual. Ainda não há QR Code, envio de arquivos locais do telefone ou exportação de áudio pelo remoto. A persistência em segundo plano está sujeita às restrições de bateria e execução da versão do Android utilizada.

O transporte usa HTTP em uma rede local confiável e não deve ser exposto à internet. O servidor exige pareamento e credencial por sessão, limita conexões simultâneas, tamanho dos pedidos, tentativas de pareamento e comandos pendentes. Não fornece acesso remoto a arquivos ou execução de comandos do sistema.

## Implementação e testes

`remote_control.py` fornece estado, fila paginada, capa e comandos. `qt_remote_ui.py` executa os comandos na thread da interface, resolve as faixas por identificadores estáveis e impede que uma busca atrasada altere a música seguinte. As capas são reduzidas e transmitidas apenas quando mudam, sem revelar caminhos locais.

No Android, `RemotePlaybackRuntime` mantém uma única conexão e fila de comandos. `RemotePlaybackService` publica a sessão de mídia e a notificação. `RemotePlaybackSurface` integra a barra, o player expandido e a fila; `RemoteControlWindow` cuida apenas do pareamento.

Os testes automatizados cobrem o protocolo HTTP local, autenticação, paginação, capas, comandos idempotentes, busca e remoção por identidade, encaminhamento à thread Qt, validação de endereços e cálculo da posição com velocidade alterada. Compilar e testar localmente não substitui validar a notificação, a tela bloqueada e a recuperação de rede em um celular físico.
