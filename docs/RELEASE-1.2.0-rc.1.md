# ONDA 1.2.0-rc.1

Pré-release para testar as mudanças de interface e reprodução antes da versão estável.

## Principais mudanças

- Android: nova navegação com Pesquisar, Downloads, Reprodução e Mais; redesign de Configurações, Imagens, Conversor, Editar metadados, Álbuns e playlists e Histórico.
- Coleções salvas no Android, cards com capa e informações organizadas e controles de tamanho e ordem das abas.
- Jukebox no PC e Android: fila, análise antecipada, timers independentes para trocar e parar, transição gradual configurável e melhorias na escolha dos loops e na visualização dos saltos.
- PC: mini barra de reprodução e correção do clique direito no ícone da bandeja.
- Nova marca de onda contínua nas duas versões, com cores dos temas e alto contraste.
- Correções de importação LRC, layout, contraste e leitura de cache nas configurações do Android.

## Pacotes

- Windows 10/11 x64: instalador e portátil. Windows sem assinatura Authenticode.
- Android: APKs x86_64 e arm64-v8a, release sem debug, assinados com a chave original.
- APKs mantêm versão interna 1.2.0, código 26. A reinstalação sobre builds assinadas anteriores com código até 26 preserva os dados. Este RC não usa um identificador de aplicativo separado.
- Fontes do projeto e fontes de componentes de terceiros acompanham os binários.

## Validação e limites

- Última validação Android: 50 testes unitários e lint; testes instrumentados direcionados ao redesign, armazenamento, cache e ícones.
- Portátil: teste isolado de inicialização; correção da bandeja coberta por teste de regressão.
- Assinatura e alinhamento dos dois APKs verificados. Checksums SHA-256 fornecidos.
- A auditoria geral anterior registrou 10 falhas em testes Python de preferências/localização. Não se afirma que a suíte completa esteja aprovada.
- Validar em uso real: atualização de instalação existente, downloads por plataforma, fila, timers, transições e configurações nas duas versões.
- Esta é uma candidata de teste, não uma release estável.
