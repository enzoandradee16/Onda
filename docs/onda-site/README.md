# Site do ONDA

Site estático, sem dependências de compilação, para GitHub Pages. Branch de publicação: `gh-pages`, pasta `/`.

Abra com um servidor HTTP local, por exemplo `python -m http.server 8765`, e acesse `http://localhost:8765`.

`index.html`: estrutura; `style.css`: visual responsivo; `app.js`: navegação, traduções e consulta da última release pública; `assets/`: marca e capturas reais. Português é o padrão; seletor na ordem português, espanhol e inglês.

Os links dos pacotes são obtidos da API pública do GitHub. Em caso de falha ou pacote ausente, apontam para a página da última release. Nenhum token é enviado ao navegador. As notas completas permanecem no GitHub. O site não publica nem altera releases do aplicativo.

Licença: GPL-2.0, conforme LICENSE.
