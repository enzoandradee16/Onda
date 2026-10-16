# Validação ONDA 1.1.3 — 2026-10-15

- PC: suíte com interface habilitada: 585 testes descobertos, 552 aprovados, 33 ignorados por condições opcionais, zero falhas.
- Android: 30 testes JVM e 24 testes instrumentados aprovados no emulador ARM64/API 36. Incluem fila grande, navegação, exibição, correspondência, espaçamento, avisos e persistência.
- Lint Android: sem erros; avisos existentes permanecem.
- Atualização: APK 1.1.2/code20 instalado e atualizado para 1.1.3/code21, preservando firstInstallTime. Aplicativo abriu após a atualização. Não é uma auditoria de todos os dados de usuário.
- APK ARM64 alinhado, assinado com o certificado original ONDA e conferido. Não é debuggable.
- Windows: launcher 1.1.3.0 e instalador recompilados; autoteste do portátil aprovado com oito abas. Não foi feita instalação sobre o aplicativo pessoal do usuário.
- Downloads reais: correções de correspondência e HTTP 403 foram testadas com arquivos completos. A playlist testada pelo usuário terminou sem tentativa manual após a recuperação adicional. Não se garante disponibilidade ou ausência de bloqueios das plataformas.
- Empacotamento: verifica integridade ZIP, paridade dos fontes do portátil, ferramentas nativas, hashes e exclusão de credenciais/configurações pessoais.

## Limites

Rodada Android no emulador, sem novo teste em aparelho físico. Windows sem Authenticode. Dependências nativas e fontes de terceiros não mudaram e são reaproveitados com hashes conferidos. Versões publicadas anteriores permanecem intactas.

A release fica em rascunho, sem publicação automática.
