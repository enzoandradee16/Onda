# Verificação de downloads — 24/10/2026

## Conclusão

O link TikTok informado (https://vt.tiktok.com/ZSg9jRoa3/) baixou integralmente no Windows, tanto com yt-dlp 2026.08.19 quanto com 2026.10.21. O usuário confirmou que o problema ocorre no Android. Não foi possível reproduzir a falha nativa: nenhum aparelho estava conectado, e o emulador local estava sem driver de virtualização. Portanto, o problema no celular **ainda precisa ser confirmado após instalar o APK atualizado**, e a causa exata não está comprovada.

## Ajustes no Android

- Um extrator baixado anteriormente só é carregado se for mais novo que o embutido no APK. ZIP inválido ou de versão antiga não substitui o motor atual; nenhum arquivo de sessão é apagado.
- yt-dlp atualizado de 2026.8.19 para 2026.10.21.
- gallery-dl atualizado de 1.32.16 para 1.32.17.
- Redes sociais deixam de inicializar a conta de catálogo Spotify, que não é necessária nesse caminho.
- Todos os formatos de redes sociais passam pelo mesmo worker compartilhado usado no PC, incluindo opções efetivas de qualidade, validação e tratamento de erros. Antes, os formatos de áudio tinham um caminho separado no adaptador Android.
- Acrescentado teste que verifica esse encaminhamento nos oito formatos internos (social, fotos, vídeo/MKV, MP4, original, MP3, M4A e FLAC).

Isso atualiza e alinha o motor, mas não constitui prova de correção da falha específica do aparelho.

## Downloads reais

25 transferências completas bem-sucedidas, com arquivos inspecionados pelo FFprobe quando aplicável. Algumas são variações do mesmo link ou comparações entre versões do extrator; não representam 25 serviços diferentes.

| Origem | Variações concluídas |
| --- | --- |
| TikTok fornecido | Link curto e completo; modo automático, MP4, MKV, áudio original, MP3, M4A e FLAC |
| Outro vídeo TikTok | Vídeo público completo |
| Fotos TikTok | Imagens originais e conversão em vídeo com áudio |
| YouTube | Vídeo MP4 e áudio MP3 |
| URL Shorts | Extração de áudio M4A a partir de uma URL com rota /shorts/ |
| Instagram | Reel e carrossel com três imagens |
| X/Twitter | Vídeo público do Brooklyn Nets |
| Kwai | Vídeo público |

Três tentativas reais não concluíram: duas no mesmo vídeo antigo do YouTube, reportado como indisponível, e uma publicação antiga do X sem mídia disponível ao extrator. Outras publicações desses serviços baixaram. Houve ainda um erro **no roteiro de teste**, que enviou o identificador interno `mkv` em vez de `video`: repetido corretamente, o download MKV passou. Esse erro não veio da interface do aplicativo.

## Matriz automatizada

256 testes executados com o motor do portátil e repetidos com os extratores atualizados: 222 aprovados, 34 ignorados. Os ignorados exigem interface gráfica ou ambiente específico, e não devem ser contados como aprovados.

Cobertura: seleção de formatos de áudio/vídeo, áudio original, limites de resolução/FPS, imagens e carrosséis, fotos com música, seleção de mídia mista, links diretos e páginas HTML, redirecionamentos, retomada HTTP Range, duplicatas, publicação de arquivos, pastas de playlists, filas simultâneas, cookies separados por serviço, recuperação HTTP 403, encaminhamento Android, validação de catálogo e importação de FLAC. Alguns desses cenários usam servidores locais ou respostas simuladas; não houve validação externa de todos os provedores ou de playlists completas.

O FFmpeg de teste foi restaurado na pasta Android/build/download-audit-tools usando o instalador do projeto e verificação SHA256. yt-dlp e gallery-dl novos foram inicialmente instalados em uma pasta isolada; o runtime do PC foi mantido para comparação.

## Adaptador Android

Três testes de integração executaram o Python do adaptador com o TikTok real: automático, MP4 e MP3. As ferramentas nativas foram substituídas por executáveis Windows, e a publicação foi simulada removendo o arquivo após a entrega. Esses testes validam o fluxo do adaptador, **não** ABI ARM64, SELinux, MediaStore, permissões ou a rede do celular.

## Compilação e testes Android

72 testes JVM aprovados. Testes instrumentados compilaram, sem execução no dispositivo. APKs mantidos em 1.2.0, versionCode 27 já configurado no projeto, assinados com a chave original.

## Evidências

- diagnosticos/resultados/downloads-2026-10-24/downloads-reais.json
- diagnosticos/resultados/downloads-2026-10-24/testes-extratores-atualizados.json

Fontes oficiais das versões: https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.21 e https://pypi.org/project/gallery-dl/1.32.17/.

## Substituição do extrator antigo

O Android agora remove o ZIP de extrator em cache quando ele é antigo, da mesma versão do APK ou inválido. Uma atualização realmente mais nova é mantida e passa a ter prioridade. Downloads futuros continuam substituindo o ZIP anterior por troca atômica, após a verificação do pacote. Se o sistema negar a limpeza do cache, o APK usa seu extrator normalmente. Validação adicional: 12 testes do adaptador e seleção de versão aprovados, incluindo preservação de arquivos de sessão.
