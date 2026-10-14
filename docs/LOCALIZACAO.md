# Idiomas da interface

Português (Brasil) (`pt-BR`) é o padrão. Espanhol usa `es` e inglês usa `en`. A ordem dos seletores é Português (Brasil), Español e English. A escolha fica em Configurações → Geral → Idioma. No Android, a interface muda imediatamente. No Windows, a alteração passa a valer ao reiniciar; o botão Reiniciar aparece abaixo do idioma somente enquanto há uma mudança pendente e desaparece se ela for revertida. O idioma é preservado independentemente de “Lembrar configurações”.

O nome do projeto é **ONDA** em qualquer idioma. Não traduzir nomes de músicas, artistas, álbuns, arquivos, caminhos, URLs, identificadores de configurações ou formatos.

## Catálogo compartilhado

`Onda/locales/es.json` e `Onda/locales/en.json` são as fontes compartilhadas das traduções para espanhol e inglês. Os dois catálogos devem ter exatamente as mesmas chaves. As chaves são os textos em português; os valores são as traduções. O Gradle inclui essa mesma pasta nos assets do Android. A distribuição portátil deve copiar a pasta `locales` junto dos módulos Python.

No PC, use `tr` para rótulos e mensagens, `display_var` para variáveis de exibição e `TranslatedCombobox` para escolhas. O combobox mostra traduções, mas seu valor interno continua no idioma canônico. No Android, use `UiText` para textos da interface e `Text` para conteúdo do usuário. `LocalizedTheme` fornece o idioma à composição. Notificações usam `translateUi`.

Templates usam nomes entre chaves, como `{count}`. Preserve exatamente os mesmos nomes na tradução. Valores de estado, mensagem, motivo e tamanho de card podem ser traduzidos dentro do template; dados de músicas e arquivos permanecem originais. Metadados do histórico traduzem cada rótulo separadamente, sem modificar o valor.

Mensagens desconhecidas permanecem no idioma de origem. Isso inclui respostas e erros técnicos fornecidos pelas plataformas e ferramentas externas. Novas mensagens próprias do ONDA devem entrar no catálogo ao serem adicionadas.

## Verificação

`Onda/test_i18n.py` verifica persistência, valores canônicos, marca, templates e integração Tk. `LocalizationTest.kt` verifica o catálogo Android, a troca pelo seletor, a persistência sem lembrar outras preferências e a navegação em inglês. Execute também os testes de navegação, histórico, playlists e metadados ao alterar a integração.

Incluído nos pacotes 1.1.0 preparados localmente. A publicação no GitHub é uma etapa separada.


## Auditoria de inglês e espanhol na preparação 1.1.0

Os catálogos compartilhados possuem 1.219 entradas em cada idioma. A revisão acrescentou 348 entradas por idioma para validações, erros, observações de catálogo, progresso e restauração. O painel de detalhes do PC traduz mensagens ao exibir; as observações e a origem dos metadados são traduzidas sem alterar título, artista ou álbum. Descrições de capas no Android e mensagens nativas do inicializador Windows também respeitam o idioma. O aviso de restauração reflete o novo padrão de salvamento ativado.

`test_localization_completeness.py` verifica paridade, placeholders, chamadas literais de tradução, rótulos de restauração, erros estáticos Python/Android e textos literais UiText. `CompleteLocalizationTest.kt` verifica no Android todas as entradas compartilhadas e mensagens dinâmicas. São verificações estáticas e testes dirigidos; respostas arbitrárias de plataformas, erros de ferramentas externas, janelas do sistema operacional e dados de músicas/arquivos mantêm seu idioma de origem.
