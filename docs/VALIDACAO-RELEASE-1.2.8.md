# Validação do ONDA 1.2.8

- Windows: versão 1.2.8 / 1.2.8.0. Portátil aprovado no autoteste de inicialização.
- Componente Windows de conexão: aprovado no autoteste de acesso a cookies HttpOnly fictícios em perfil separado. O formulário do Instagram também foi carregado no protótipo WebView2, sem autenticação real.
- PC e motor compartilhado: 36 testes específicos aprovados e 5 ignorados. Cobertura de seleção independente de cookies, encaminhamento aos downloads, sessão Android e extratores sociais.
- Android: versão 1.2.8, código 36; 109 testes unitários aprovados.
- BlueStacks: quatro testes instrumentados aprovados, cobrindo a rejeição de sessão sem login, a preservação do Instagram ao remover cookies do YouTube, a leitura do cofre pelo Python e o carregamento com captura da área renderizada do formulário real. O APK isolado chama-se ONDA Testes.
- Login real, desafios do Instagram e acesso a vídeos restritos precisam ser confirmados com a conta do usuário. Nenhuma senha ou sessão pessoal foi utilizada nos testes.

- Proteção: migração DPAPI testada com cookies fictícios, sem arquivo de texto residual; compatibilidade C# → DPAPI → Python e exclusão na desconexão aprovadas.
