# ONDA para Android

**Versão 1.2.9**, para Android 8 ou superior, ARM64 e x86_64.

O ONDA reúne pesquisa, downloads, reprodução, efeitos de áudio, edição de metadados e ferramentas de imagens. A navegação principal usa **Pesquisar**, **Downloads**, **Reprodução** e **Mais**.

## Instalar

- Celulares ARM64: `APK/ONDA-Android-1.2.9-arm64-v8a.apk`.
- Dispositivos e emuladores x86_64: `APK/ONDA-Android-1.2.9-x86_64.apk`.

Transfira o APK para o aparelho e permita a instalação pela origem escolhida. Não é necessário instalar Python, FFmpeg ou Termux. As atualizações usam a assinatura original do ONDA e preservam os dados do aplicativo.

## Reprodução

O player compacto acompanha a navegação. Toque nele para abrir capa, controles, fila e letras; as letras também podem ocupar a tela inteira. Slowed, Jukebox infinito e equalizador compartilham a mesma música e podem funcionar juntos. O equalizador oferece 5, 10 ou 15 bandas.

Sem efeitos, músicas de catálogo podem ser ouvidas por streaming. A reprodução começa com um pequeno buffer e carrega o restante em um cache temporário de até 256 MB, separado dos downloads. Trechos já carregados permitem avançar e retroceder sem nova espera de rede. O cache pode ser limpo nas configurações.

Ao ativar efeitos, a música atual continua até o áudio processado ficar pronto. A fila indica o estado da preparação. O controle remoto permite controlar o ONDA no PC e transferir a reprodução entre os dispositivos na mesma rede.

## Downloads e arquivos

Em **Downloads**, toque em **+**, cole os links e escolha **Baixar agora** ou adicione à lista de downloads. Conceda a permissão de notificações quando solicitada. Se houver uma confirmação de metadados, versão ou mídias, abra o aplicativo e responda à janela.

No Android 10 ou superior, a pasta padrão é Downloads/ONDA. Em Configurações → Downloads, escolha outra pasta pelo seletor do sistema. No Android 8 e 9, escolha uma pasta para preservar os downloads ao desinstalar.

O Histórico permite abrir, compartilhar e usar os arquivos em reprodução ou nos efeitos. A localização permanece associada ao arquivo mesmo após mudar a pasta padrão.

O ONDA oferece MP3, M4A, FLAC e áudio original conforme a fonte e a disponibilidade. FLAC usa uma fonte compatível, sem transformar áudio com perdas em áudio sem perdas.

## Contas e acesso aos serviços

Para conectar sua conta Spotify, configure o Client ID e o retorno `http://127.0.0.1:8765/callback`. A autenticação usa PKCE e o retorno ocorre no próprio celular. O acesso a playlists depende das permissões e dos limites do serviço.

Se o YouTube exigir verificação, abra Mais → Sessão do YouTube, conclua a verificação e toque em **Usar esta sessão**. Se o serviço recusar o navegador incorporado, importe cookies da sua própria sessão em Configurações → Contas. Bloqueios por IP e verificações adicionais continuam sujeitos ao serviço.

O login do Instagram fica em Configurações → Contas. A sessão é protegida no armazenamento privado do aplicativo e pode ser removida nas configurações. A disponibilidade de conteúdo restrito depende das permissões da conta.

## Aparência e idioma

Configurações e Aparência ficam nos ícones do cabeçalho. O tema, a cor de destaque e a fonte podem ser personalizados. O idioma pode ser alterado imediatamente entre Português (Brasil), Español e English.

Ao abrir o teclado, a navegação inferior dá espaço ao conteúdo e o player compacto continua acessível. Abrir a fila fecha o teclado sem apagar a pesquisa.

## Atualizações

Nas configurações, toque em **Verificar atualização do ONDA**. O download continua em segundo plano. Ao terminar, toque em **Instalar atualização** e, na primeira vez, permita a instalação pelo ONDA nas configurações do Android.

O aplicativo confere o pacote, a versão e a assinatura da atualização. O sistema pede confirmação antes de instalar. Se cancelar, a opção permanece disponível para tentar novamente.

## Mais informações

- [Funcionalidades](FUNCIONALIDADES.md)
- [Reprodução unificada](../docs/REPRODUCAO-UNIFICADA.md)
- [Licenças das dependências](THIRD_PARTY_NOTICES_ANDROID.md)
