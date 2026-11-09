# Validação local do ONDA 1.2.6

Preparação local em 3 de novembro de 2026. O pacote usa o commit 5715398 e as alterações locais de versão e documentação. A revisão também incluiu ce78113, a base da 1.2.5.

- Windows x64 com versão informativa 1.2.6 e versão numérica 1.2.6.0.
- Android ARM64 e x86_64 com versão 1.2.6 e código 34. Ambos os APKs passaram nas verificações de assinatura de produção, integridade, arquitetura e alinhamento ZIP de 16 KB.
- PC com 88 testes aprovados e um ignorado na suíte selecionada. Android com 106 testes unitários aprovados.
- Autotestes do portátil, do instalador e do desinstalador registrados no manifesto.
- A rodada não incluiu instalação em aparelho ARM64 ou no BlueStacks, nem validação manual de reprodução online. Os executáveis Windows não têm assinatura Authenticode.
- Os pacotes de fontes de terceiros da 1.2.5 foram reaproveitados após a verificação de dependências e hashes.

A release foi preparada localmente. Nenhuma tag ou release foi publicada.
