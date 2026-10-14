# Acessibilidade no Android

A interface fornece informações de acessibilidade automaticamente ao Android, sem ativar uma opção no ONDA. Ative TalkBack, acesso por voz ou o serviço desejado nas configurações de acessibilidade do aparelho. A fala depende do serviço e do mecanismo de síntese instalados.

- Menu, fechar avisos e setas de reordenação têm nomes de ação em vez de somente símbolos. Na fila, as setas identificam a música; na configuração de abas, identificam a aba.
- Seletores informam nome, valor e estado expandido/recolhido. Campos de texto mantêm os rótulos dos componentes nativos Compose.
- Caixas de seleção em opções, fila e álbuns expõem a função e o estado, com uma ação por grupo. Controles desativados preservam o estado nativo.
- Barras de velocidade, reverb, posição, duração e zoom têm nomes e valores. As ações de ajuste fornecidas pelo Android permanecem disponíveis.
- O recorte da capa expõe quatro ações acessíveis para mover a imagem. O zoom pode ser alterado pela ação de ajuste; salvar mantém o arquivo original.
- Capas e prévias têm descrições localizadas; títulos de páginas são marcados como cabeçalhos. Avisos finais usam anúncios educados, sem anunciar cada atualização de progresso como alerta.
- Descrições em português, espanhol e inglês acompanham o idioma do ONDA. Nomes de músicas e arquivos são preservados.

## Validação

AccessibilityTest verifica funções, estados, nomes e ações nos três idiomas, incluindo ajuste de barras e recorte sem gestos. AccessibilityPlatformTest consulta a árvore AccessibilityNodeInfo entregue pelo Android. Testes de fila, idiomas e recorte verificam regressões. A consulta da árvore nativa é executada separadamente para evitar interferência de seu estado global nos testes Compose. Logs em diagnosticos/resultados/accessibility-*.log registram os resultados e as tentativas iniciais.

A validação automática usa emulador Android API 36. Ela não substitui uma sessão de uso com uma pessoa utilizando TalkBack em aparelho físico, nem representa certificação de acessibilidade. Estas mudanças são da interface Android; a interface Windows/Tk possui uma integração diferente com leitores de tela.


### Confirmação de uso com TalkBack

Em 2026-10-14, o usuário confirmou que o TalkBack funcionou em seu teste. Este é um relato de uso do usuário, adicional aos testes automáticos; não implica cobertura de todos os aparelhos, telas ou idiomas.
