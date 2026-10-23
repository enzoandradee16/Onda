# Integração local dos patches — 22/10/2026

Base local: `418601951bc61ab0d33b72e2b56e6db77586032b`.

Os 12 itens do patch ainda estavam pendentes. O patch foi aplicado após `git apply --check`, com estes ajustes:

- ONDA-007: corrigida a remoção do segredo persistido ao limpar os campos. Preservada a preferência explícita do usuário: o botão Remover credenciais aparece somente quando conectado.
- O teste de metadados do instalador lê UTF-8 explicitamente, para funcionar no Windows.
- O `.gitignore` permite versionar `empacotamento/sync_version.py` sem inclusão forçada.

## Validação executada neste computador

- 35 testes direcionados: regressões da fila, credenciais, versão, cookies e traduções; todos aprovados.
- Interface Qt: 63 casos na rodada inicial, 57 aprovados e 6 ignorados por ferramentas indisponíveis naquele momento.
- Preferências, atalhos e controles de fila: 61 casos, 33 aprovados e 28 ignorados pelas condições de integração dos testes.
- Após recuperar o FFmpeg: quatro testes reais de conversão, download por servidor local, exportação de efeitos e botões QML; todos aprovados. Esses casos se sobrepõem à suíte Qt.
- Sintaxe Python, JSON dos catálogos e `git diff --check`: aprovados.
- Portátil: executável abriu a janela em teste isolado/offscreen, com renderizador software. Dependências do runtime importadas com sucesso.

A rodada inicial também teve dois erros, resolvidos: PySide6 ainda estava sendo instalado ao iniciar a primeira classe, e o teste de versão usava a codificação padrão do Windows. A reexecução dos 35 testes direcionados passou integralmente.

Android: alterações de cancelamento da prévia e testes JVM incluídos; sem compilação ou execução Android nesta integração. Não foram feitos testes contra Spotify ou outros serviços externos, nem instalação interativa do instalador.
