# Revisão adicional — 22/10/2026

Cinco falhas reproduzidas por testes de regressão e corrigidas no controlador desktop:

1. Retomar uma seleção mista reiniciava downloads concluídos. Agora somente itens retomáveis entram no pedido.
2. Cancelar todos sobrescrevia resultados Concluído e Falhou. Agora preserva resultados terminados e cancela somente trabalhos ativos, pendentes ou pausados.
3. O valor zero de RAM disponível era confundido com uma consulta indisponível. Zero agora bloqueia novos downloads quando há reserva configurada; uma consulta sem resultado continua com o comportamento anterior.
4. A reserva de RAM bloqueava também o reconhecimento de conclusão. Agora a verificação de memória se aplica somente ao início de novos downloads.
5. O aviso de pouca RAM era reenviado a cada verificação. Agora é emitido uma vez por período de espera, reduzindo atualizações desnecessárias da interface. Uma nova falta de memória após recuperação pode emitir novo aviso.

Os testes incluem seleção mista, preservação dos estados finais, memória zerada, conclusão sob pouca memória, supressão de avisos repetidos e recuperação da memória.

Revisados também os fluxos Android de execução da fila e cancelamento da prévia. As cinco correções acima são específicas do controlador desktop. Não foi compilado APK nem validada execução em aparelho.
