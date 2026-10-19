# Jukebox infinito

Disponível no código atual, na aba Reprodução e efeitos → Jukebox infinito, no PC e Android.

- Abra um áudio local ou pesquise/cole um link e escolha a faixa explicitamente. Fontes online são obtidas pelos mecanismos existentes do ONDA e precisam estar disponíveis; não há um servidor Eternal Jukebox integrado.
- A análise local compara pulsos, energia, timbre e conteúdo harmônico. Só permite saltos entre candidatos compatíveis; sem ritmo confiável ou correspondências, repete normalmente.
- Variação controla a frequência dos saltos; Transição suave ajusta a mistura curta nos pontos de mudança. Reprodução normal desativa saltos. Volume, pausa/retomada e tempo ouvido funcionam sem reanalisar.
- A análise e o áudio de trabalho ficam em cache por conteúdo. A limpeza de cache existente preserva arquivos ainda em uso; o original permanece intacto.
- Limite inicial: faixas de 3 segundos a 15 minutos; áudio de trabalho PCM estéreo de 16 bits/44,1 kHz. Pode ocupar mais espaço que o arquivo comprimido.
- Android pausa ao sair de primeiro plano, perder foco de áudio ou desconectar fones. Não utiliza serviço de reprodução em segundo plano.
- Implementação independente: não reproduz exatamente o algoritmo, as conexões ou a naturalidade do site Eternal Jukebox. As transições precisam ser avaliadas ouvindo diferentes faixas.

Traduções: português, inglês e espanhol. As identidades das abas antigas são mantidas para preservar ordem e ocultação. Esta implementação ainda não foi incluída nos pacotes da release 1.1.6.
