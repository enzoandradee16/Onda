# Correção de resolução e FPS em vídeos

Validação em 13/10/2026 (horário de São Paulo). Correção compartilhada entre Windows e Android; sem publicação de release.

## Causa e comportamento

O seletor filtrava somente a altura e o FPS dos formatos disponíveis. Isso podia excluir um vídeo vertical (720 × 1280 não é 1280p) ou a única fonte fornecida pela publicação, causando `Requested format is not available` antes de qualquer conversão.

A seleção agora considera o lado menor do vídeo, prefere formatos nativos dentro dos limites e permite uma fonte disponível quando não existe opção compatível. Após o download, FFprobe confere o arquivo real; FFmpeg reduz resolução e/ou FPS somente se necessário. Não há ampliação de resolução nem aumento intencional de FPS. A redução é informada nos detalhes. O original de trabalho é substituído apenas após sucesso e conferência da conversão; falhas não publicam um arquivo fora dos limites.

Aplicado ao caminho principal (incluindo Kwai e YouTube), aos streams resolvidos de Instagram/TikTok e aos vídeos diretos de publicações. Vídeos sem áudio também são aceitos. Áudio original e publicações originais não recebem conversão de resolução.

## Testes

- 28 testes do motor, seleção, estimativas, recuperação e conversões: aprovados.
- Redes sociais: 35 testes aprovados e sete testes opcionais de interface ignorados nesta rodada.
- Matriz local de seleção: todas as seis resoluções e cinco opções de FPS em MP4/MKV, com fontes representativas de Kwai, Instagram, TikTok e YouTube, incluindo dados ausentes, vídeos verticais e vídeos sem áudio.
- Matriz online: 60 combinações por plataforma, total de 240 seleções aprovadas usando metadados reais das quatro publicações abaixo.
- Downloads online completos: uma publicação de cada plataforma, pedindo no máximo 480p e 24 fps. Todos concluídos e conferidos com FFprobe.
- Android API 36 com tradução ARM64: teste nativo aprovado, convertendo MP4 vertical e MKV horizontal de 60 fps para lado menor 480 e 24 fps; áudio AAC preservado e segunda execução sem reconversão.
- APK release compilado e assinatura verificada. Portátil e instalador PC atualizados.

| Plataforma | Publicação testada | Arquivo final |
| --- | --- | --- |
| Kwai | https://kwai-video.com/p/9MC9uCVz | 480 × 852, 24 fps |
| Instagram | https://www.instagram.com/reel/Chunk8-jurw/ | 480 × 854, 24 fps |
| TikTok | https://www.tiktok.com/@patroxofficial/video/6742501081818877190 | 480 × 852, 24 fps |
| YouTube | https://www.youtube.com/watch?v=FGBhQbmPwH8 | 192 × 144, 12,5 fps; qualidade nativa dentro dos limites |

As escolhas de resolução e FPS são limites máximos. Uma fonte menor ou mais lenta é preservada; não é ampliada para preencher o valor escolhido. Se for necessário converter, o processamento pode demorar mais. Os 240 casos online verificam seleção; os quatro downloads completos verificam transferência e saída real, não 240 transferências. Testes Android desta correção foram no emulador; não em aparelho físico.

Evidências locais não versionadas: `diagnosticos/resultados/resolucao-fps/`.

A preparação da release permanece interrompida. A numeração 1.0.0/versionCode 16 já havia sido aplicada antes da interrupção e foi preservada nos builds locais. O APK corrigido está em `Celular/APK/ONDA-Android-1.0.0-arm64-v8a.apk`; não foi publicado, enviado ou marcado como release oficial.
