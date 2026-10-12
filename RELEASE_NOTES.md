# ONDA 1.0.0-beta.1

Primeira beta para Windows 10/11 de 64 bits: músicas, vídeos, imagens, álbuns e playlists em uma interface em português, com metadados, capas, fila e histórico.

Inclui efeitos Slowed/Sped Up/Reverb com prévia, temas claro/escuro/do sistema e 16 cores de destaque.

## Qual arquivo baixar?

- `Onda-1.0.0-beta.1-Portable-Windows-x64.zip`: extraia tudo e abra Onda.exe. Não precisa instalar Python. O FFmpeg é baixado automaticamente no primeiro uso, com internet.
- `Onda-1.0.0-beta.1-Setup-Windows-x64.exe`: assistente de instalação com atalhos e desinstalador.
- `Onda-1.0.0-beta.1-Fontes.zip`: código do ONDA e scripts de construção.
- `Onda-1.0.0-beta.1-Fontes-de-terceiros.zip`: fontes dos componentes Python gallery-dl, Mutagen e yt-dlp; consulte o inventário e os avisos.
- `SHA256SUMS.txt`: hashes para conferir os arquivos.

## Antes de usar

É uma versão beta e os executáveis ainda não têm assinatura digital. Plataformas podem mudar, bloquear acessos ou exigir login/cookies. A correspondência de músicas usa uma fonte equivalente no YouTube; não baixa áudio protegido original de Spotify/Apple Music. Exportar FLAC não transforma uma fonte com perdas em lossless.

Use somente conteúdo que você tenha autorização para baixar. Relate problemas sem compartilhar cookies, credenciais ou dados pessoais.

Desinstalador com escolhas independentes para manter ou apagar dados pessoais e remover as ferramentas baixadas, como o FFmpeg. O padrão é manter ambos. Downloads e ferramentas externas são preservados.

Na primeira abertura, o ONDA prepara o FFmpeg diretamente de gyan.dev (aproximadamente 109 MB), com progresso e verificação de integridade. O download é feito uma vez por PC; nas próximas aberturas é reutilizado. É possível adiar e retomar em Configurações → Ferramentas.
