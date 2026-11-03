# Validação local — ONDA 1.2.5

Preparação local em 3 de novembro de 2026. Nenhum arquivo, tag ou release foi criado no GitHub nesta preparação.

## Versões e distribuição

- Windows: versão informativa 1.2.5, versão numérica 1.2.5.0; portátil completo e instalador x64.
- Android: versão 1.2.5, código 33; APKs ARM64 e x86_64 com a assinatura de produção usada nas versões anteriores.
- APKs verificados com apksigner e zipalign, incluindo alinhamento de 16 KB, arquitetura, nome, versão e integridade ZIP.
- A pasta Release/1.2.5 contém os pacotes, fontes, avisos, relatório e SHA256SUMS.txt. Ela é ignorada pelo Git e aponta para o armazenamento local externo ao checkout.
- O código-fonte é uma fotografia do checkout local, incluindo a preparação ainda não commitada. SOURCE_MANIFEST.json registra os arquivos e seus hashes; o commit-base é registrado em MANIFEST.json.

## Testes executados

- 145 testes do PC aprovados, sem falhas ou testes ignorados, abrangendo versão, streaming, fila, preparação, sessão, controle remoto, imagens, cache e exportação.
- Áudio real via HTTP, saída PCM nativa, transições, busca de posição e continuidade durante preparação de efeitos; abertura de arquivo local enquanto streaming toca.
- Autoteste do executável portátil aprovado. Nove telas do pacote final abertas sem avisos QML.
- Autotestes do instalador e desinstalador aprovados em português, inglês e espanhol.
- Nove verificações de instalação Windows em ambiente de auditoria isolado: instalação nova, atualização, atalhos, abertura do programa instalado, preservação de arquivos e propagação de falhas.
- Sete verificações do desinstalador isolado, incluindo cancelamento, combinações de limpeza de dados/ferramentas e rejeição de um backend adulterado. A instalação normal não foi alterada por esses testes.
- 106 testes unitários Android aprovados, sem falhas ou testes ignorados.
- 13 testes instrumentados de reprodução aprovados no BlueStacks 5: reordenação durante preparação e atualizações da lista, remoção por gesto, próxima faixa preparada sem rede, pausa e transições com sobreposição real de áudio.
- Um teste adicional com a playlist real https://open.spotify.com/playlist/3QVBmvKuaiT3uuGlFsWCMA aprovado no Android, enviando a coleção para reprodução com uma fila existente, confirmando áudio ativo e capa individual diferente da capa da playlist.
- O roteiro desse teste foi atualizado para rolar nas listas antes de clicar nos controles carregados sob demanda.
- APK oficial x86_64 instalado por atualização sobre 1.2.5-rc/código 32 no BlueStacks, sem desinstalar; abertura da versão 1.2.5/código 33 confirmada.
- Consulta real da playlist no PC: capas individuais de aruarian dance, Digital Love e Amore mio aiutami - Main Theme; decodificação online de aruarian dance no início e aos 45 segundos. A imagem da capa de aruarian dance foi inspecionada e corresponde ao álbum, sem mosaico.
- Arquivos de fontes de terceiros verificados contra seus hashes; binários nativos ARM64 conferidos contra o inventário de compilação. Os arquivos de fontes nativos foram preservados integralmente da distribuição anterior verificada.

## Limites da validação

- O APK ARM64 foi compilado, assinado e verificado; não foi instalado em um aparelho ARM64 físico nesta preparação.
- A captura da janela por controle do computador não foi concluída. A exibição foi coberta pelos testes de interface e a capa retornada foi inspecionada separadamente; não há captura visual completa da janela nesta rodada.
- Os executáveis Windows não possuem assinatura Authenticode.
- Serviços externos podem mudar, bloquear consultas ou limitar acesso. Os testes reais representam os resultados obtidos nesta preparação, não uma garantia para todo conteúdo ou provedor.
- Fontes originais e licenças de terceiros acompanham a distribuição. O modelo opcional de remoção de fundo é obtido no primeiro uso e não está incluído nos pacotes.

Os relatórios estruturados da compilação e da validação estão resumidos em VALIDACAO.json na pasta da release.
