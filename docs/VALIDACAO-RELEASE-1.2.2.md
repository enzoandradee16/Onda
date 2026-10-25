# Validação do ONDA 1.2.2

Preparação em 25/10/2026, no fuso America/Sao_Paulo. Os resultados desta preparação são registrados também em MANIFEST.json; os pacotes são listados com tamanho e SHA-256.

## Aplicativo

- PC: 187 testes de regressão e 8 testes de histórico, filtros e plataformas aprovados; a suíte de localização de 5 testes também foi executada novamente.
- Android: 74 testes JVM aprovados. Testes instrumentados recentes cobriram Downloads simplificado, busca e filtros, remoção em lote e novas tentativas, navegação de filas grandes, adicionar links e iniciar downloads, tamanho dos cards, preferências, histórico e ícones de plataforma e de imagens. Capturas da tela simples foram revisadas nos temas claro e Preto Puro.
- As correções anteriores de Aparência, interruptores e pesquisa de configurações também passaram em testes instrumentados.
- Site: verificação de sintaxe JavaScript e referências de imagens; revisão anterior em três idiomas, dois temas, três larguras e sete rotas, incluindo os links de download e a ampliação das capturas.

## Pacotes de distribuição

A preparação exige os autotestes do launcher, instalador e desinstalador Windows; verifica a integridade dos ZIPs e a igualdade dos fontes distribuídos com o inventário local. Os APKs devem passar na verificação da assinatura original e do alinhamento de 16 KB, com versão 1.2.2/código 29, pacote de produção e ABI correta. As ferramentas ffmpeg, ffprobe e qjs são comparadas aos hashes nativos do projeto.

Os arquivos de fontes de terceiros são reutilizados da release 1.2.1 somente após a verificação de integridade e das versões atuais dos extratores. Chaves, cookies, configurações pessoais, diretório Testes e pacotes locais não entram no arquivo de fontes do ONDA.

## Limites

O ambiente de execução Android usado foi BlueStacks com Android 11/x86_64. Não houve teste em aparelho físico ARM64 nesta preparação. Os executáveis Windows não possuem assinatura Authenticode. Os autotestes do instalador não equivalem a uma instalação interativa em todas as versões do Windows.

O rascunho não publica a release nem altera versões anteriores.
