# Conversor de vídeos

Aba própria no Windows e Android. Escolha um vídeo local, formato MP4/MKV/MOV, qualidade (Equilibrada, Alta qualidade ou Arquivo menor) e resolução máxima (Original, 1080p, 720p ou 480p).

A conversão usa H.264 e AAC, mantém a proporção e não amplia vídeos menores. Exporta a primeira faixa de vídeo real e a primeira faixa de áudio quando presente. Legendas, faixas adicionais e menus não são exportados. Arquivos sem áudio são aceitos.

No PC, escolha um nome novo para a saída. No Android, a cópia é publicada no destino de downloads configurado e entra no histórico. Não substitui os arquivos originais ou saídas existentes. O cancelamento elimina os temporários da conversão.

Não é remux sem perdas: o vídeo é recodificado. A interface não promete reduzir todos os arquivos nem aumentar sua qualidade. O tempo depende da duração, resolução e aparelho. No Android, mantenha o aplicativo aberto durante a conversão; esta primeira implementação não é um serviço de conversão em segundo plano.

Os pacotes da release 1.1.3 previamente preparada não são alterados automaticamente por esta implementação.

## Prévia e opções avançadas

A prévia reproduz o original (aplicativo padrão do sistema no PC e Android). Ela não simula a compressão final. Alguns codecs podem não ser reproduzidos pela prévia Android, mesmo sendo convertíveis.

Bitrate de vídeo automático usa a qualidade selecionada; uma taxa fixa substitui essa qualidade. Também é possível escolher bitrate de áudio, FPS ou remover o áudio. A resolução continua sem ampliar o original. A taxa fixa é um alvo médio, não uma garantia de tamanho exato.

## Extrair áudio

MP3, M4A e AAC extraem a primeira faixa de áudio do vídeo. Ao selecionar esses formatos, aparecem apenas formato e qualidade do áudio (96 a 320 kbps). As opções de vídeo ficam ocultas e não alteram a extração. Vídeos sem áudio são recusados sem criar saída. O original é preservado.
