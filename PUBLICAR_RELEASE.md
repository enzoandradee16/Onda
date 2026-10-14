# Publicação do ONDA 1.0.0

Os pacotes preparados ficam em `Release/1.0.0`. A preparação local não publica a release.

1. Revisar e enviar o código-fonte correspondente, incluindo os arquivos novos, para o GitHub.
2. Criar a tag `v1.0.0` sobre o commit correspondente aos pacotes. Não reutilizar tags antigas.
3. Criar a release `ONDA 1.0.0`, usando `RELEASE_NOTES.md`. Desmarcar pré-release e marcar como versão mais recente.
4. Anexar os seis pacotes listados nas notas, `SHA256SUMS.txt`, `MANIFEST.json`, `VALIDACAO.md` e os avisos de terceiros.
5. Conferir arquivos, hashes e vínculo com o código antes de publicar.

O AppId Windows e a chave Android foram preservados. O APK usa versionCode 16. Executáveis Windows sem Authenticode; o APK é assinado com a chave ONDA. Não anexar configurações pessoais, cookies, credenciais, chaves privadas, mídias ou a pasta de desenvolvimento inteira.

O desinstalador mantém as escolhas independentes de configurações e cache de ferramentas; os downloads são preservados. O FFmpeg Windows continua preparado no primeiro uso e não é redistribuído nos pacotes.
