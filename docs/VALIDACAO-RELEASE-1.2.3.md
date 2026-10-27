# Validação do ONDA 1.2.3

Preparação em 27/10/2026. Release estável em rascunho, sem publicação automática.

## Verificações executadas
- Regressões do PC: limpeza automática, retomada HTTP com Range e validação de alteração na origem, persistência de filas, efeitos, Jukebox, histórico, traduções, pesquisa de configurações e atualização.
- Interface PC: arraste do corpo do card sem rolar a lista, deslocamento dos vizinhos antes de soltar, inversão de sentido, botões clicáveis e navegação das galerias.
- Android: 81 testes JVM aprovados; rodadas instrumentadas no BlueStacks x86_64 para filas, recuperação e galerias. A última rodada do ícone compacto aprovou os 3 testes, incluindo geometria do conteúdo e arraste dinâmico por toque prolongado.
- Portátil: teste de abertura do pacote Qt com renderização por software aprovado.
- Instalador e desinstalador Windows: autotestes executados durante o empacotamento desta release.
- APKs: pacote, versão 1.2.3, código 30, arquitetura única, bibliotecas nativas, alinhamento de 16 KB e assinatura original conferidos nos dois arquivos finais.
- Pacotes: hashes SHA-256, arquivos ZIP, fontes e avisos de terceiros conferidos.

## Limites da validação
- Os testes instrumentados foram executados em x86_64; não houve execução automatizada do conjunto completo no celular ARM64 físico.
- A retomada de transferências depende do suporte da origem. Consultas e testes locais não garantem disponibilidade permanente de plataformas externas.
- O instalador Windows não tem assinatura Authenticode; os APKs usam a chave original do aplicativo.

Os manifestos da pasta Release/1.2.3 registram o commit e os hashes dos pacotes finais. Scripts, perfis e logs locais permanecem fora do Git.
