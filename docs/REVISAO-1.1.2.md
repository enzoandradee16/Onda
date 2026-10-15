# Validação ONDA 1.1.2 — 2026-10-15

- PC: 420 testes em 64 módulos; zero falhas, 0 ignorados. Inclui interface Tk, FFmpeg, persistência, traduções e as novas ferramentas.
- Android: 11 testes JVM e 26 testes instrumentados distintos aprovados no emulador. A rodada de 25 foi complementada pela suíte de 9, com oito repetições e um teste adicional de organização.
- Casos adicionais: URLs de recursos distintos, parâmetros relevantes, playlists, qualidade, limpeza seletiva de campos, arquivos repetidos, capa inválida sem alterar originais e limites de seleção.
- Organização executada também no motor Python embarcado no Android: contenção de pastas e nomes com disco/faixa.
- Lint Android: {'Warning': 71, 'Hint': 2}. Sem erros; avisos existentes permanecem.
- APK ARM64 de produção: assinatura conferida contra o certificado ONDA; atualização de 1.1.1/code19 para 1.1.2/code20 aceita pelo Android, preservando firstInstallTime. Abertura após atualização executada no emulador.
- Windows: launcher 1.1.2.0, instalador recompilado e autoteste do portátil aprovado. Arquivos ZIP de teste não são incorporados ao instalador nem ao portátil da release.
- Pacotes: integridade ZIP, paridade dos fontes do portátil, ferramentas nativas Android e SHA-256 conferidos durante o empacotamento.

## Limites

Testes Android executados em emulador; não houve teste em aparelho físico nesta rodada. O Windows não possui assinatura Authenticode. Duplicatas usam a origem do link; não há comparação acústica. Histórico Android anterior sem origem não pode ser reconhecido retroativamente.

Preparação não publica a release. As releases anteriores permanecem intactas.
