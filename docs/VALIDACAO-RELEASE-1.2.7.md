# Validação do ONDA 1.2.7

Verificações realizadas em 9 de novembro de 2026.

- Windows x64: versão 1.2.7 / 1.2.7.0. Autotestes de inicialização, instalador e desinstalador aprovados; interface em português, inglês e espanhol.
- PC: 41 testes específicos de entrada de reprodução e fila aprovados nesta preparação.
- Android ARM64 e x86_64: versão 1.2.7, código 35, pacote br.com.onda.mobile. Assinatura original, arquitetura e alinhamento de 16 KB verificados nos APKs atuais.
- Android: 106 testes unitários aprovados na última compilação. Dois testes específicos de continuidade durante preparação/falha e transição de streaming passaram anteriormente no BlueStacks. As últimas alterações visuais foram compiladas, sem nova inspeção visual no emulador.
- Pacotes ZIP conferidos quanto à integridade; fontes do aplicativo e hashes correspondem ao estado local usado na preparação. Fontes de terceiros reaproveitadas após validação das versões e hashes.
- Não houve novo teste em aparelho ARM64 físico nem instalação completa nesta preparação. Os executáveis Windows não têm assinatura Authenticode.

