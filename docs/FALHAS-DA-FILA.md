# Resumo de falhas da fila

PC e Android abrem o resumo ao terminar normalmente uma execução com falhas. Ele considera somente itens que essa execução tentou: sucessos, cancelamentos e falhas antigas fora da execução não entram. Interromper a fila ou fechar o programa não abre a janela automaticamente.

O botão **Falhas da fila** permite reabrir os erros atuais: fica junto ao tempo da fila no PC e no menu do Android.

- **Salvar lista** exporta TXT UTF-8 com nome, link e motivo de cada falha do resumo. O relatório preserva os dados originais mesmo após corrigir os metadados. Não exporta configurações nem credenciais.
- **Escolher metadados/Pesquisar metadados** permite pesquisar Deezer e Apple, selecionar uma música e aplicar ao item que falhou. Vale para itens individuais de áudio; publicações, imagens e um link que representa uma playlist inteira não viram uma faixa de áudio.
- A escolha explícita troca a fonte desse item pelo link público da faixa escolhida. O próximo download consulta novamente os detalhes do catálogo. Formato, qualidade, pasta e agrupamento da playlist são mantidos; o link anterior fica registrado em `failure_original_url`. Escolhas e cache de metadados antigos são removidos para não sobrescrever a nova escolha.
- **Tentar novamente** repete os itens ainda falhos ou preparados no resumo. Não duplica a fila nem repete os já concluídos. Escolher metadados não inicia um download por conta própria.

A pesquisa ocorre em segundo plano. A lista do Android é virtualizada; a exportação e a preparação das novas tentativas também são feitas fora da interface.

Validação: testes de relatório, escopo da execução, cancelamento, preservação das opções e interface Tk com pesquisa simulada, escolha, exportação e nova tentativa. Android: compilação dos fontes e testes JVM de seleção/ordem das falhas e validação de URLs. Nenhum APK novo foi gerado; a interface Android ainda precisa ser conferida no aparelho quando houver autorização para empacotar.
