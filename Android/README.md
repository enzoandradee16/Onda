# ONDA para Android

## Interface do Android

A navegação principal usa **Pesquisar**, **Downloads**, **Reprodução** e **Mais**. Em Downloads, Em andamento / Concluídos usa o mesmo seletor arredondado de Salvos / Importar em Álbuns e playlists. Reprodução aplica esse estilo a Efeitos / Jukebox infinito e respeita a ordem configurada.

O player compacto acompanha a navegação; toque nele para abrir capa, controles e letras, que também podem ocupar a tela inteira. Efeitos e Jukebox têm filas próprias. As capturas do celular foram recortadas apenas nas barras do sistema e estão em `docs/images/android novo`, na raiz do projeto; a navegação do ONDA foi preservada.

Os dois APKs oficiais usam versão **1.2.1**, código **28**, com a assinatura de produção original. A validação física ARM64 continua pendente. Consulte [o relatório atual](../docs/VALIDACAO-RELEASE-1.2.1.md).

Projeto Android separado da distribuição Windows. Kotlin/Compose fornece a interface e os serviços; Python/Chaquopy executa o motor compartilhado do ONDA. O build copia os módulos necessários de `../Onda`, sem editar o programa de PC.

Versão de desenvolvimento **1.2.1**, conforme `app/build.gradle.kts`, para Android 8 ou superior, ARM64 e x86_64. Kotlin/Compose e o motor compartilhado fornecem busca, downloads, histórico, edição de metadados, imagens e efeitos. Consulte [FUNCIONALIDADES.md](FUNCIONALIDADES.md) e a [auditoria de paridade com o PC](PARIDADE-PC-ANDROID.md).

Resultados e pendências desta compilação: [validation/RESULTADOS.md](validation/RESULTADOS.md).

## Instalar no celular

Use `APK/ONDA-Android-1.2.1-arm64-v8a.apk`, transfira para o celular e permita a instalação pela origem escolhida. Android 8 ou superior, processador ARM64; o APK padrão contém somente ARM64 para reduzir o tamanho. Para emulador x86_64, use `APK/ONDA-Android-1.2.1-x86_64.apk` ou compile com `-Arquitetura x86_64`; para ambas, use `-Arquitetura universal`. O APK distribuído é assinado com a chave de produção ONDA; o script de desenvolvimento gera um APK debug separado. Não precisa instalar Python, FFmpeg ou Termux.

Abra o ONDA, conclua ou feche a configuração inicial. Em Links e fila, cole o link e escolha Baixar agora ou Adicionar à fila. Downloads usam notificações; conceda a permissão quando solicitada. Se precisar confirmar metadados/versão/mídias, abra o app e responda à janela.

No Android 10+, a pasta padrão é Downloads/ONDA. Em Configurações → Downloads é possível escolher outra pasta pelo seletor do sistema. Android 8/9 usa a pasta do aplicativo se nenhuma pasta for escolhida; escolha uma pasta para preservar os downloads ao desinstalar. Histórico permite abrir o arquivo, abrir sua pasta de origem, compartilhar e usar áudio/vídeo nos efeitos. Abrir pasta usa o gerenciador compatível ou o seletor de arquivos do Android; a localização vem do arquivo do histórico, mesmo após mudar a pasta padrão.

Músicas de streaming usam metadados do catálogo: MP3/M4A usam uma versão correspondente no YouTube; FLAC usa Monochrome quando há uma correspondência compatível, sem converter silenciosamente YouTube em FLAC. A API Spotify é opcional para links individuais. Para conectar uma conta, cadastre `http://127.0.0.1:8765/callback` no Spotify Developers e informe seu Client ID. O retorno fica no próprio celular e usa PKCE. As restrições da API e o limite do embed público continuam aplicáveis; CSV do Exportify é uma alternativa.

## Interface e acesso ao YouTube

Abra o menu ☰ para alternar entre as áreas, acessar Configurações e consultar a fila. Os títulos e controles seguem a nomenclatura do programa de PC; seletores foram compactados para o celular. Em Efeitos, o preset selecionado acompanha os sliders e permanece ao trocar de área. Na busca, Ouvir muda para Parar enquanto a prévia está ativa.

Em Configurações → Geral → Idioma, a ordem é Português (Brasil), Español, English, com português como padrão e mudança imediata. Em Links e fila e no Histórico, seletores discretos permitem escolher compacto/completo e o tamanho dos cards, independentemente entre as duas áreas. No Histórico, os controles ficam centralizados junto de Limpar histórico, abaixo da pesquisa.

Se o YouTube exigir verificação, abra Menu → Sessão do YouTube e tente concluir a verificação na janela do próprio app. Toque em Usar esta sessão e tente novamente o download. A sessão é salva apenas no armazenamento privado do ONDA. O login ou a liberação podem ser recusados pelo YouTube em navegador incorporado; nesse caso, importe cookies.txt da sua própria sessão em Configurações → Contas. Nenhum desses caminhos garante remover bloqueios por IP ou exigências adicionais do serviço. Para apagar a sessão, use Remover sessão do YouTube nas configurações.

O ícone da tela inicial e dos aplicativos recentes acompanha o destaque e a aparência escolhidos, incluindo Seguir o sistema. A atualização visual do launcher depende do cache do aparelho; um atalho de versões antigas pode precisar ser recriado. Consulte [ícones e tema](../docs/ANDROID-ICONE.md).

## Compilar no Windows

Requer JDK 17/21, SDK com plataforma Android 36 e Build Tools 36.0.0, e Python 3.11 para preparar as dependências. Se a pasta Portatil estiver ao lado, o script aproveita o Python dela.

```powershell
cd 'E:\Projetos\Onda\Android' # ajuste para a pasta do seu checkout
powershell -ExecutionPolicy Bypass -File '.\Compilar Android.ps1'
```

Antes da primeira compilação em um checkout novo, prepare as ferramentas conforme [nativebuild/README.md](nativebuild/README.md).

Também é possível abrir esta pasta em Android Studio. Configure `local.properties` com `sdk.dir` e, se necessário, passe `-Ponda.buildPython=C:/caminho/python.exe` ao Gradle. `local.properties`, caches, módulos copiados, APKs e chaves não entram no Git.

Para testar, conecte um emulador/aparelho de teste e use `-Testar`. Os testes instrumentados criam mídias sintéticas e credenciais fictícias; não usam arquivos pessoais. Não execute testes em uma instalação com dados importantes.

## Arquitetura

- `app/src/main/java`: telas, fila persistente em SQLite, serviço de download, player Media3, permissões/SAF/MediaStore e Keystore.
- `app/src/main/python/mobile_backend.py`: adaptação das ferramentas, eventos, escolhas, cancelamento e chamadas ao motor.
- `app/src/main/python/shared`: gerado de `../Onda` durante a compilação; não editar.
- `app/src/debug/python` e `app/src/androidTest`: testes reais no Android.
- `nativebuild/`: fontes fixados por hash, scripts de reconstrução, configurações e avisos das ferramentas nativas.
- `native-tools/`: executáveis gerados localmente; não entram no Git.

As preferências, a fila, o histórico, os cookies importados e as credenciais ficam no armazenamento privado do app. Segredos são cifrados com Android Keystore; backups automáticos estão desativados. Arquivos exportados para Downloads/ONDA ou para a pasta escolhida ficam fora dos dados privados. O Android controla a desinstalação e a remoção dos dados privados.

## Distribuição

A versão 1.1.0 usa assinatura de produção. As fontes das ferramentas nativas estão no pacote Fontes-nativos-Android e a reconstrução está descrita em [nativebuild/README.md](nativebuild/README.md). Há testes ARM64 em emulador; compatibilidade e comportamento em segundo plano devem continuar sendo conferidos em aparelhos reais. Veja [THIRD_PARTY_NOTICES_ANDROID.md](THIRD_PARTY_NOTICES_ANDROID.md).

Na pesquisa, Adicionar à fila e Baixar agora alimentam a Fila da pesquisa, visível na mesma área. Ela mostra estado/progresso e usa o serviço da fila geral sem repetir downloads. Tempos são exibidos em minutos:segundos. Em Configurações → Contas, Abrir Spotify Developers abre o painel oficial no navegador; conectar exige Client ID, com aviso acima da janela se faltar.


### Fonte da interface

Em Configurações → Aparência → Fonte da interface, escolha Padrão do sistema, Sem serifa, Serifada, Monoespaçada, Condensada, Cursiva ou Arredondada. A prévia e a interface mudam imediatamente. Ative Lembrar configurações para manter a escolha ao reabrir; restaurar Aparência também restaura a fonte. Esta versão usa fontes nativas do Android, sem baixar arquivos de fontes.


### Enter nos campos

Em Pesquisar músicas, Enter do teclado físico ou a ação Pesquisar do teclado virtual inicia a busca, sem inserir uma linha. Os demais campos são de uma linha. Somente o campo LINKS em Links e fila aceita Enter para separar os links.

O fluxo de fotos, vídeos, posts mistos e foto com música nas redes sociais está descrito em [Downloads sociais](../docs/FLUXO-DOWNLOAD-SOCIAL.md).

## Fila e edição de áudio

Downloads simultâneos, retomada, ordem da fila, edição local de tags/capa/letra, normalização com prévia, agendamento e transferência de preferências: consulte [o guia de recursos avançados](../RECURSOS-AVANCADOS.md).


### FLAC direto no ONDA

Ao escolher FLAC para uma faixa de Spotify, Deezer ou Apple Music, o ONDA consulta o servidor público Monochrome e baixa o arquivo diretamente, sem abrir navegador. A correspondência compara título, artista, versão, duração e ISRC quando disponível. Versões ambíguas pedem confirmação; a opção de maior similaridade automatiza essa escolha. O download mostra progresso, valida o codec e a decodificação completa, aplica metadados/capa e respeita destino, duplicados, playlists e histórico.

O acervo é limitado e a disponibilidade depende do serviço externo. Se não houver FLAC compatível, o ONDA avisa e não converte silenciosamente YouTube em FLAC. MP3/M4A continuam pelo YouTube. A origem anterior dos arquivos no servidor e a masterização não são comprovadas; o registro de origem identifica Monochrome. Links diretos, vídeos e efeitos continuam permitindo conversão para FLAC, que não recupera qualidade perdida.


### Novos downloads durante uma execução

Você pode usar **Baixar agora** enquanto outras mídias estão sendo baixadas. Com vaga no limite de downloads simultâneos, o novo item começa; com todas as vagas ocupadas, aguarda a próxima. Solicitações individuais não iniciam outros itens pendentes que você não pediu para baixar. A fila em execução aceita novos itens sem reiniciar os downloads atuais.


## Atualizações dentro do app

No Android, novas versões podem ser baixadas dentro do ONDA, com progresso e continuidade em segundo plano. Ao terminar, toque em Instalar atualização; na primeira vez, permita a instalação pelo ONDA nas configurações do Android. O sistema pede confirmação e os dados são preservados. O gerenciador de downloads do Android mantém a transferência mesmo com a tela de configurações fechada. Volte às configurações para instalar, cancelar ou descartar o APK. A atualização aceita apenas links da release oficial e confere pacote, versão superior e assinatura igual à instalação atual. Se a instalação for cancelada, o botão permanece disponível.
