# Publicação do ONDA 1.1.1

Pacotes preparados em `Release/1.1.1`. Preparar localmente não cria tag nem publica no GitHub.

1. Revisar e enviar todos os fontes novos e alterados para o GitHub; os pacotes foram gerados da árvore local, confira o estado das mudanças pendentes antes de publicar.
2. Confirmar que o commit corresponde ao `SOURCE_MANIFEST.json` e criar a tag **v1.1.1** nesse commit. Não reutilizar tags antigas.
3. Criar a release com título **ONDA 1.1.1**, usando `RELEASE_NOTES.md`; desmarcar pré-release e escolher versão mais recente, quando a opção existir.
4. Anexar os seis pacotes, `SHA256SUMS.txt`, `MANIFEST.json`, `SOURCE_MANIFEST.json`, `VALIDACAO.md` e os dois avisos de terceiros.
5. Conferir hashes e arquivos antes de publicar. As versões Windows e Android devem ser publicadas juntas.

O AppId Windows e a chave de produção Android foram preservados. APK: versionName 1.1.1, versionCode 19. Windows: versão de arquivo 1.1.1.0, sem Authenticode. A pasta Release/1.0.0 não foi alterada.

Não distribuir cookies, configurações pessoais, credenciais, chaves privadas, mídias ou a pasta de desenvolvimento inteira. O FFmpeg Windows é preparado no primeiro uso e não é redistribuído nos pacotes. Desinstalação mantém as escolhas independentes de dados e cache; downloads são preservados.
