# Conectar ao Instagram

No Windows e no Android, abra **Configurações → Contas → Conectar ao Instagram**. Entre na sua conta na página do Instagram, conclua as verificações solicitadas e escolha **Usar esta sessão**. Depois tente baixar a publicação novamente.

A sessão fica no dispositivo, separada das sessões do YouTube, TikTok e Kwai. **Atualizar sessão do Instagram** reabre o login; fechar a janela sem salvar conserva a sessão anterior. **Desconectar Instagram** remove os cookies salvos e encerra a sessão no navegador próprio do ONDA. Isso não desconecta o Instagram em outros aplicativos ou navegadores.

No Windows, a janela usa Microsoft Edge WebView2 Runtime. Não exige que o usuário utilize Edge, Chrome ou Firefox como navegador principal. Se o runtime não estiver instalado, escolha **Instalar WebView2** para baixar o instalador oficial da Microsoft pelo navegador. Execute o arquivo baixado e clique em **Já instalei · Tentar novamente** no ONDA. O restante do aplicativo continua funcionando sem esse componente. Os componentes do host e sua licença acompanham o ONDA.

No Android, a janela utiliza o WebView do sistema. Mantenha Android System WebView atualizado. A importação manual de cookies continua disponível para os demais casos.

O ONDA não salva a senha digitada. Os cookies salvos pelo ONDA ficam criptografados: DPAPI da conta do Windows no PC e AES-GCM com chave no Android Keystore no celular. Os extratores recebem a sessão em memória, sem gerar um arquivo de cookies em texto. A sessão da versão anterior é migrada automaticamente. Ao fechar a tela de login no Android, os cookies do navegador integrado são removidos. Os cookies continuam sendo dados de acesso sensíveis. Não compartilhe esses arquivos. A aceitação do login, eventuais desafios e a disponibilidade de vídeos restritos dependem do Instagram e da conta.
