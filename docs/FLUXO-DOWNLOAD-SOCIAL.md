# Downloads de Instagram, TikTok e Kwai

O tipo da publicação é consultado antes de aplicar o formato selecionado:

- **Somente fotos:** baixa imagens, mesmo que MP3, MP4 ou MKV esteja selecionado. As opções da aba Imagens continuam sendo aplicadas às fotos.
- **Somente vídeos:** MP3 extrai o áudio; MP4 ou MKV baixa o vídeo. Os demais formatos de áudio continuam disponíveis. Se Fotos estiver selecionado, usa MP4 automaticamente.
- **Fotos e vídeos:** abre a seleção das mídias. Cada vídeo permite escolher MP4/MKV ou somente áudio em MP3/M4A/FLAC/original. Fotos permanecem imagens.
- **Uma única foto:** abre a escolha entre Só foto e Foto com música · MP4. A segunda opção aparece quando os dados da publicação fornecem uma URL de áudio acessível. Sem áudio fornecido, a janela informa a limitação e permite baixar a foto.

O MP4 usa a imagem inteira, sem corte, e o áudio fornecido pela plataforma. Quando os dados do Instagram informam início/fim do trecho, esse intervalo é aplicado. Caso contrário, utiliza a duração do áudio disponível. Não busca outra música para substituir uma trilha ausente.

A implementação é compartilhada pelo PC e Android. A música é transferida pela sessão da plataforma, incluindo cookies configurados, e a montagem acontece localmente com FFmpeg. O arquivo só é publicado após a conversão terminar; as regras de duplicados permanecem válidas. O arquivo original do usuário é preservado.

## Verificação

- PC: 281 testes aprovados, incluindo janelas Tk e FFmpeg. A execução coleta ciclos de objetos Tk na thread principal entre testes para evitar a coleta desses objetos por threads de miniaturas.
- Android: MediaChoiceTest e MobileRuntimeTest, 5 testes aprovados no emulador API 36 x86_64. Incluem seleção MP3/MKV, foto sem música disponível, publicação mista com foto e áudio extraído e foto com música exportada como MP4 contendo os dois streams.
- Android lint sem erros; APK final ARM64, versão 1.0.0-alpha.1.

Os testes usam dados de publicação controlados e um servidor HTTP local, além de conversão real. Não comprovam acesso a todos os posts reais. Disponibilidade, login, URLs expiradas, música não exposta e bloqueios de conexão continuam dependendo de cada plataforma.
