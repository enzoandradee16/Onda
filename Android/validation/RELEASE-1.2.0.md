# APKs Android 1.2.0

- versionName 1.2.0, versionCode 26, pacote br.com.onda.mobile.
- Builds release ARM64 e x86_64 concluídos, incluindo lint vital.
- APKs sem a flag debuggable, alinhados com zipalign para páginas de 16 KB.
- Assinaturas verificadas com apksigner; certificado original preservado: SHA-256 0edd6f5de88fc24b7a45212b51ba7d428030302459e9ed8d619d7dbc29fb81b3.
- Atualização de produção 1.1.7/code25 para 1.2.0/code26 validada no emulador x86_64 API 36 usando install -r. firstInstallTime preservado, sem desinstalação, e atividade iniciada com processo ativo.
- ARM64: compilação, manifesto, arquitetura, alinhamento e assinatura verificados. Esta rodada não inclui teste em aparelho físico.
- APKs e hashes ficam em Celular/APK. Nenhuma publicação no GitHub foi realizada nesta preparação.

## Ajustes visuais e arraste entre páginas — somente x86_64

Navegação horizontal animada, mantendo os gestos dos sliders; capas das listas maiores; concluídos recentes abaixo dos downloads ativos; controles e layout do Jukebox aproximados das referências. Seis testes instrumentados de interface aprovados no emulador, incluindo navegação nas duas direções e alteração dos dois sliders sem sair da página. APK x86_64 release recompilado, alinhado e assinado novamente com o certificado original. ARM64 não recompilado nesta rodada.

### Timer da Jukebox

- Timer na barra de reprodução e no menu: parar ou avançar pela fila a cada 1 a 180 minutos.
- Conta somente durante reprodução, reinicia ao trocar de faixa e reduz volume nos últimos 10 segundos. Sem próxima música, desliga o timer e mantém a faixa atual.
- 46 testes unitários passaram, incluindo pausa, mudança de faixa e reinício da contagem.
- APKs x86_64 e arm64-v8a gerados com a mesma versão 1.2.0 e assinatura original.

### Refinamento da Jukebox

- Timers independentes de parada e troca, utilizáveis simultaneamente.
- Preparação serial ao adicionar músicas à fila; reprodução reaproveita o modelo preparado. Erros e nova tentativa aparecem por faixa.
- Transição gradual opcional com sobreposição real das faixas e duração configurável de 1 a 10 segundos.
- Análise compara quatro beats de continuação: harmonia, timbre e proporção da faixa média do espectro. É uma aproximação acústica sensível à voz, sem separação vocal ou reconhecimento de palavras.
- Análises antigas são atualizadas uma vez a partir do PCM em cache, sem baixar novamente.
- Grafo mostra todas as conexões reais na cor do tema, destaca as utilizadas e acompanha o trajeto efetivamente ouvido.
- Validação: 25 testes do motor Python, 47 testes unitários Android e 4 testes direcionados no emulador (preparação serial, reprodução/trocas seguidas/serviço, grafo e gestos).
- Referência consultada: https://github.com/EternalBox/EternalJukebox/blob/master/_web/files/jremix.js . O site indicado retornou HTTP 502; foi consultado o código público, sem adicionar suas dependências ao ONDA.

### Crossfade contínuo

- O mixer compartilhado sobrepõe PCM das duas faixas, mantendo uma única saída no PC e no Android.
- Duração configurável de 1 a 10 segundos em Áudio. Trocas manuais e pelo timer usam o mesmo fluxo.
- Metadados e progresso mudam quando os primeiros frames da nova faixa chegam à reprodução; o grafo respeita fragmentos dos beats durante a mistura.
- Validação: mistura PCM e duração exata, continuidade da posição da faixa de entrada, troca automática no PC com uma única saída e troca no Android preservando a mesma instância AudioTrack.

### Ajustes de interface e letras

- Seleção LRC no Android aceita provedores sem MIME específico; leitura compartilhada aceita UTF-8, UTF-16 com BOM e CP1252. Importação válida ativa a letra no PC e arquivos inválidos geram aviso.
- Áudio no PC separa a continuidade dos efeitos e do Jukebox, com controles visíveis e textos ajustados à janela.
- Menus usam cores coerentes de seleção, e a minibarra do PC abre o Jukebox ao clicar fora dos controles.
- Removida a preferência global redundante de confirmar versões do YouTube; seleção manual explícita permanece disponível.
