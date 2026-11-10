# Validação do ONDA 1.2.8

- Windows: versão 1.2.8 / 1.2.8.0. Portátil aprovado no autoteste de inicialização.
- Componente Windows de conexão: aprovado no autoteste de acesso a cookies HttpOnly fictícios em perfil separado. O formulário do Instagram também foi carregado no protótipo WebView2, sem autenticação real.
- PC e motor compartilhado: 36 testes específicos aprovados e 5 ignorados. Cobertura de seleção independente de cookies, encaminhamento aos downloads, sessão Android e extratores sociais.
- Android: versão 1.2.8, código 36; 109 testes unitários aprovados.
- BlueStacks: quatro testes instrumentados aprovados, cobrindo a rejeição de sessão sem login, a preservação do Instagram ao remover cookies do YouTube, a leitura do cofre pelo Python e o carregamento com captura da área renderizada do formulário real. O APK isolado chama-se ONDA Testes.
- Login real e acesso ao vídeo antes restrito foram confirmados pelo usuário. Nenhuma senha ou sessão pessoal foi utilizada nos testes automatizados; desafios de autenticação não foram automatizados.

- Proteção: migração DPAPI testada com cookies fictícios, sem arquivo de texto residual; compatibilidade C# → DPAPI → Python e exclusão na desconexão aprovadas.

## Revisão complementar

- Reprodução: 28 testes da fila Qt e uma regressão adicional para saída de áudio encerrada aprovados. No Android, 19 testes de preparação/streaming e três verificações finais passaram no BlueStacks: teclado nas duas buscas, avanço de posição durante tela inicial/notificações e reposicionamento PCM.
- As transições do Android foram exercitadas com áudio sintético. Ausência de engasgos no celular físico e desaparecimento do quadrado branco relatado ainda precisam de confirmação do usuário.

- WebView2 ausente: oferta de download oficial e botão de tentar novamente aprovados em português, inglês e espanhol, com ausência simulada do runtime. O instalador da Microsoft não foi executado neste computador, que já possui o runtime.

- Usuário confirmou download autenticado no PC e persistência do login após reiniciar o aplicativo no Android físico.
- Windows: nove verificações do instalador aprovadas; atualização real de 1.2.7 para 1.2.8 preservou configurações, mídia e sessão fictícias. Registro de instalação de produção permaneceu inalterado.
- Aplicativo Windows iniciou com runtime WebView2 indisponível por configuração simulada. Uma máquina limpa sem WebView2 não foi utilizada; o diálogo de erro do componente não teve seu texto inspecionado visualmente.
- Sete testes de cookies/downloads aprovados: troca de contas fictícias, desconexão e continuidade de uma transferência HTTP já iniciada, sem reutilizar a sessão em novas solicitações.
- BlueStacks: três testes adicionais aprovados para digitação, teclado/Voltar, rotação e troca/desconexão do cofre. Corrigida recriação do navegador na mudança de orientação, preservando o formulário.
- Troca entre duas contas reais e desafios de autenticação permanecem sem teste automatizado. Os testes utilizaram sessões fictícias ou formulário sem login.
