# Preparação da beta 1

Os pacotes locais ficam em `Release/1.0.0-beta.1` e estão ignorados pelo Git. Este procedimento não publica nem muda a visibilidade do repositório automaticamente.

## Antes de tornar público

- Revise README, licença GPL-2.0-only e avisos de terceiros. Não publique credenciais, cookies, configurações pessoais ou mídias baixadas.
- Confira que os pacotes não contêm `_runtime/ffmpeg` nem os executáveis FFmpeg/ffprobe/ffplay. Eles são obtidos diretamente de gyan.dev no primeiro uso, com SHA-256 fixo. A antiga pendência de reunir os fontes do FFmpeg deixou de se aplicar aos pacotes do ONDA, pois eles não o redistribuem.
- O usuário confirmou funcionamento em outro PC. Para validar futuras versões e o novo desinstalador, confira em Windows 10/11 x64 sem Python/FFmpeg/Node instalados: extração portátil, primeira abertura com preparação automática, download autorizado, efeitos, segunda abertura sem novo download, instalação, atualização e desinstalação. A verificação local não substitui esse teste.
- Confira os hashes e leia o relatório local de validação. Executáveis não assinados podem gerar avisos do Windows.

## Enviar documentação

Revise `git diff` e `git status`, adicione os arquivos novos e alterados, faça o commit e o push. Os scripts de empacotamento continuam fora do Git; uma cópia limpa está no ZIP de fontes.

## Criar a release no GitHub

1. Após as verificações, em Settings → General → Danger Zone, altere a visibilidade se quiser tornar o repositório público. Revise o aviso do GitHub antes de confirmar.
2. Abra Releases → Draft a new release.
3. Crie a tag `v1.0.0-beta.1` apontando para o commit enviado, com o título `ONDA 1.0.0-beta.1`.
4. Cole o conteúdo de RELEASE_NOTES.md e marque **Set as a pre-release**.
5. Anexe os quatro pacotes, SHA256SUMS.txt e MANIFEST.json. Não envie a pasta de desenvolvimento inteira.
6. Salve como rascunho, revise e publique quando as verificações anteriores estiverem concluídas.

Não reutilize a mesma tag para pacotes diferentes. Para correções, prepare beta.2 e novos hashes. Não altere o AppId do instalador entre versões.


O desinstalador oferece uma segunda escolha independente para remover o cache de ferramentas baixadas pelo ONDA (%LOCALAPPDATA%\Onda\tools\ffmpeg). O padrão e o modo silencioso mantêm o cache. Somente arquivos conhecidos nas pastas de versão são removidos; ferramentas externas e arquivos desconhecidos são preservados. Verifique manter/apagar configurações e ferramentas separadamente e cancelar em cada pergunta. Reinstale o novo Setup para atualizar o desinstalador de uma instalação existente.
