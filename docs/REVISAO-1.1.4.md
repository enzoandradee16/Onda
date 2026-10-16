# Validação ONDA 1.1.4 — 2026-10-16

- PC: 609 testes descobertos; 444 aprovados e 165 ignorados por condições opcionais, sem falhas. Mais 23 testes isolados dos recursos alterados, incluindo interface, aprovados.
- Android: 32 testes JVM aprovados; compilação release e lint sem erros.
- Conversor: formatos de vídeo e áudio, cancelamento, ausência de áudio e preservação do original validados por testes locais. Configurações, busca, filtros, cache e origem têm cobertura específica.
- Windows: launcher e instalador 1.1.4.0 recompilados; autoteste do portátil aprovado com nove abas. Não foi feita instalação sobre o aplicativo pessoal do usuário.
- APK ARM64 alinhado e assinado com o certificado de produção original; versão 1.1.4 / code22.
- Empacotamento: verificação de integridade ZIP, fontes, ferramentas nativas, hashes e exclusão de credenciais/configurações pessoais.

## Limites

A rodada ampla de testes de interface do PC e Android ficou sem concluir e foi interrompida; os testes afetados foram executados isoladamente. Não representa aprovação de toda a suíte instrumentada. Sete testes instrumentados isolados dos recursos alterados passaram no emulador ARM64/API 36.

Sem novo teste em aparelho físico. Windows sem Authenticode. Dependências nativas e fontes de terceiros não mudaram e são reaproveitados com hashes conferidos. Downloads dependem das restrições das plataformas; não houve novo teste de playlist completa nesta preparação.

Conversor para vídeos locais, primeira faixa de vídeo/áudio; não preserva legendas ou todas as faixas. No Android, manter o aplicativo aberto durante conversões. O rascunho não será publicado automaticamente.

Atualização de produção: 1.1.3/code21 → 1.1.4/code22 instalada com sucesso no emulador; firstInstallTime preservado e aplicativo aberto após atualizar. Não é uma auditoria de todos os dados do usuário.
