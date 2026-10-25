# Site do ONDA

Site estático, sem dependências de compilação, para GitHub Pages. Branch de publicação: `gh-pages`, pasta `/`.

Abra com um servidor HTTP local, por exemplo `python -m http.server 8765`, e acesse `http://localhost:8765`.

`index.html`: estrutura; `style.css`: visual responsivo; `app.js`: navegação, traduções e consulta da última release pública; `assets/`: marca e capturas reais. Português é o padrão; seletor na ordem português, espanhol e inglês.

Os links dos pacotes são obtidos da API pública do GitHub. Em caso de falha ou pacote ausente, apontam para a página da última release. Nenhum token é enviado ao navegador. As notas completas permanecem no GitHub. O site não publica nem altera releases do aplicativo.

Licença: GPL-2.0, conforme LICENSE.


Atualização visual: captura principal da pesquisa de músicas no Windows, no tema preto puro; player e letras no Android e miniplayer no Windows. Layout responsivo com destaque verde e cartões arredondados.

A captura da pesquisa no Android aparece ao lado da captura do PC na abertura. O arquivo `assets/android-search-cropped.png` foi recortado de verdade: 60 pixels do topo e 36 pixels da base foram removidos da imagem original de 576 × 1280, resultando em 576 × 1184. As barras do sistema foram removidas e a navegação do ONDA foi preservada. O clique nas capturas abre um visualizador dentro do site, que pode ser fechado pelo botão, por Esc ou clicando fora da imagem. O Android usa o mesmo arquivo recortado na ampliação; não há recorte por CSS.

Downloads Android separados por arquitetura: ARM64 para aparelhos e x86_64 para emuladores compatíveis. O botão x86_64 procura um arquivo `Android-…x86_64.apk` na última release pública. Se o pacote ainda não estiver publicado (por exemplo, enquanto a release estiver em rascunho), abre a página da release, sem oferecer outro APK no lugar. Não inclui APKs no pacote do site.
