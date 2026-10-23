# Preparação da fila e oportunidades de otimização

## Implementado no Android

Efeitos prepara as duas próximas faixas enquanto a atual toca. Os renders antecipados são sequenciais e identificados por arquivo, velocidade, reverb e preservação de tom. Na troca, usa o arquivo pronto ou aguarda o mesmo render em andamento, em vez de iniciar outro. Arquivos preparados fora da janela são descartados; parâmetros diferentes não reutilizam o áudio antigo. A janela de duas faixas limita o uso adicional de armazenamento, mas o custo real depende da duração das músicas.

## Oportunidades encontradas, ainda não implementadas

1. **Retentativas de pré-processamento com espera:** falhas de render podem ser novamente tentadas pelo ciclo de 100 ms. Registrar a falha e usar um intervalo evita consumir CPU repetindo o mesmo trabalho.
2. **Prioridade da reprodução atual:** suspender preparação antecipada durante um render solicitado pelo usuário pode reduzir disputa por CPU em celulares mais lentos. Hoje o render atual e o antecipado podem coexistir.
3. **LRCLIB com cache persistente:** o cache Android de letras é mantido no ViewModel e a busca compartilhada usa rede. Persistir por identidade da gravação, com expiração e invalidação, evita repetir consultas ao reabrir o aplicativo.
4. **Extração de cor da capa compartilhada:** barra compacta, cartão e janela de letras podem calcular a cor separadamente. Coil reutiliza imagens, mas um cache da cor por identidade da capa evita novas leituras de pixels.
5. **Metadados e capas em lote:** o Android limita leituras de informações a duas simultâneas; leitura de tags e capa ainda abre o arquivo em etapas separadas. Consolidar a extração reduz I/O nas filas grandes.
6. **Download de áudio reutilizável:** a obtenção online em jukebox.fetch_audio pode baixar novamente uma faixa usada antes. Um cache com identidade de catálogo/URL, validação e política de espaço pode poupar rede e espera sem misturar as filas das duas abas.
7. **PC — cache de áudio processado:** o PC inicia o processamento na reprodução através de PreviewPlayer. Uma camada de cache por arquivo e parâmetros pode reduzir o custo de repetir uma faixa; precisa preservar a resposta imediata aos ajustes e o comportamento de streaming.

São oportunidades identificadas por revisão de código, sem medição comparativa de tempo ou promessa de ganho numérico. A validação do novo comportamento em aparelho continua necessária.
