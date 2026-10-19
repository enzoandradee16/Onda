# Validação local ONDA 1.1.7 — 19/10/2026

- 131 testes PC aprovados nas áreas de Jukebox, equalizador, histórico, biblioteca, fila, conversão, preferências e integração de interface. Cinco falhas iniciais por ausência do FFmpeg no PATH do ambiente foram resolvidas ao repetir os casos afetados com o caminho configurado.
- 42 testes unitários Android aprovados. Compilações release ARM64 e x86_64 concluídas com lint vital.
- Autoteste do portátil 1.1.7 aprovado: inicialização, nove abas, dependências e ferramentas locais. Executável e instalador Windows 1.1.7.0; sem assinatura Authenticode.
- Dois APKs Android 1.1.7/código 25, sem flag debuggable, com arquitetura e assinatura de produção verificadas. Certificado preservado.
- Sem novo teste manual em aparelho/emulador ou instalação/upgrade do instalador nesta preparação. Transições musicais continuam dependendo da faixa e exigem avaliação auditiva.
- Revisão estática sem nomes indefinidos. Imports de diagnóstico mantidos intencionalmente; removidos imports duplicados/sem uso e estado morto da interface.
- Saturação PCM otimizada preservando arredondamento e limites de 16 bits; retenção desnecessária do PCM em Base64 removida da fila de sincronização Android.
- Empacotamento confere fontes, arquitetura, ferramentas nativas, integridade dos ZIPs e SHA-256. Rascunho no GitHub; publicação posterior manual.
