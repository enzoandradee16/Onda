# Atividade no Discord — Windows

Em **Configurações → Geral**, ative **Mostrar atividade no Discord**. A opção começa desativada. O Discord para computador precisa estar aberto e permitir o compartilhamento de atividades nas suas próprias configurações de privacidade.

O ONDA mostra a música e o artista. A capa e o álbum aparecem quando há uma imagem pública disponível; capas locais não são enviadas. A presença acompanha a posição, a velocidade e as trocas de faixa. Ao pausar, mostra a pausa e remove o contador; ao parar, desativar a opção ou encerrar o ONDA, limpa a atividade.

O aplicativo não solicita token, senha, Client Secret, autorização de bot ou acesso a mensagens. A identificação pública da aplicação ONDA é `1567209385833537706`. O nome e o ícone da aplicação são definidos no Discord Developer Portal pelo responsável pelo ONDA.

A integração usa o protocolo local [RPC over IPC do Discord](https://docs.discord.com/developers/topics/rpc), com canais nomeados do Windows e `SET_ACTIVITY` do tipo Listening. A comunicação usa QLocalSocket, sem esperas bloqueantes e sem bibliotecas adicionais. Atualizações de faixa e posição são agrupadas em intervalos de pelo menos cinco segundos; parar ou desativar limpa imediatamente. Se o Discord estiver fechado ou a conexão cair, o ONDA tenta reconectar em segundo plano.

A primeira implementação é exclusiva do PC. Ela não transfere áudio ao Discord: somente informações da reprodução. Configurações de privacidade do Discord e suporte do cliente podem afetar como a atividade é exibida.
