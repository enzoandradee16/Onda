# ONDA Windows 1.0.0-beta.2 / Android 1.0.0-alpha.2

Atualização de testes para Windows 10/11 x64 e Android 8 ou superior, ARM64.

## Novidades

- FLAC de links de Spotify, Deezer e Apple Music baixado diretamente do Monochrome, quando disponível, sem abrir páginas com anúncios.
- Correspondência por artista, título, versão, duração e ISRC; confirmação de versões ambíguas e opção de maior similaridade.
- Possibilidade de solicitar novos downloads enquanto outros estão em andamento, respeitando o limite de 1 a 4 downloads simultâneos.
- Correção da barra de progresso após conclusão e dos textos de estado do arquivo.
- Ajustes na instalação do ambiente Python de desenvolvimento.
- Android: FFmpeg, codecs e QuickJS compilados a partir de fontes registrados, com pacote de fontes nativos e acesso às licenças pelo menu.
- Android: retirada do pacote de suporte nativo antigo, reduzindo o tamanho e eliminando sua extração na inicialização.

## Qual arquivo baixar?

- `Onda-1.0.0-beta.2-Portable-Windows-x64.zip`: extraia tudo e abra Onda.exe; Python e Node incluídos. FFmpeg preparado automaticamente no primeiro uso com internet.
- `Onda-1.0.0-beta.2-Setup-Windows-x64.exe`: instalação por usuário, com atalhos e desinstalador.
- `ONDA-Android-1.0.0-alpha.2-arm64-v8a.apk`: aplicativo Android assinado com a chave de produção ONDA.
- `Onda-1.0.0-beta.2-Fontes.zip`: código-fonte e scripts de construção das duas plataformas.
- `Onda-1.0.0-beta.2-Fontes-nativos-Android.zip`: fontes completos e receitas das ferramentas nativas Android.
- `Onda-1.0.0-beta.2-Fontes-de-terceiros.zip`: fontes Python e avisos das dependências.
- `SHA256SUMS.txt` e `MANIFEST.json`: integridade, versões e situação da validação/assinatura.

## Observações

Esta é uma pré-release. Os executáveis Windows não têm assinatura Authenticode. A assinatura Android é independente; confira o manifesto.

O acervo FLAC é limitado e depende de terceiros. Confirmar o codec não comprova a origem anterior nem a masterização sem perdas. MP3/M4A de músicas de catálogo continuam usando uma versão equivalente do YouTube; converter áudio com perdas para FLAC não recupera qualidade perdida. Plataformas podem exigir login/cookies ou bloquear acesso.

APK com uma chave diferente da versão instalada não pode atualizar por cima dela. Preserve a chave de produção para as próximas versões; desinstalar uma versão anterior pode apagar dados locais.

Use conteúdo que você tenha autorização para baixar. Não compartilhe cookies, credenciais ou chaves privadas ao relatar problemas.
