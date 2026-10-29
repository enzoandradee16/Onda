# Validação local — ONDA 1.2.4

Data: 29/10/2026. Windows 1.2.4.0; Android 1.2.4, código 31.

## Resultados da revisão final

| Grupo | Resultado |
| --- | --- |
| Descoberta completa Python | 1.154 encontrados; 728 executados sem falhas; 426 condicionais ignorados |
| Reprodução, filas, restauração, áudio e interface Qt | 45 testes aprovados em janela Windows |
| Android JVM | 87 testes aprovados |
| Código dos testes de interface Android | Compilação x86_64 concluída |
| Portátil | Autoverificação de inicialização aprovada |

Os grupos possuem cobertura sobreposta e não devem ser somados como testes únicos. A suíte Qt confere abertura e fechamento da fila sem navegar, identidade da faixa após reorganização, acionamento da reprodução, limpeza da fila, shuffle, restauração silenciosa, precisão dentro da batida e animações de conteúdo e indicador. Os testes do modelo antigo de filas separadas foram preservados e adaptados à fila unificada.

## Alterações verificadas

- Restauração da posição em segundos e da fase da música; a sessão permanece pausada ao reabrir. A posição é preservada quando o cache precisa ser preparado novamente.
- Encerramento do serviço Android preserva a posição, sem confundir o fechamento do aplicativo com o comando explícito Parar.
- Reprodução Android reorganizada, fila independente da página de origem, player expandido com fila inferior e gesto de remoção de cards.
- Animações de abertura da fila e troca entre Fila e Tocado recentemente; as abas mantêm estados de rolagem separados no Android.
- Imagens e carrosséis com prévia integrada; no PC, imagem centralizada. Conversão real preserva o original.
- Conversor Android organizado em cards, sem Prévia do original nas duas versões. Opções de imagem visíveis, com Formato e Tamanho máximo juntos.
- Fontes Modern e Legacy ajustadas no Android, sem mudar a seleção do PC. Letras com duração em minutos e segundos.

## Pacotes e limites da validação

Os dois APKs de produção são conferidos quanto à versão, arquitetura, assinatura original, alinhamento de 16 KB, ferramentas nativas e licenças. Portátil, instalador e desinstalador Windows passam pelos respectivos autotestes. Os manifestos identificam o commit e os hashes dos fontes e pacotes.

Não há dispositivo conectado ao ADB na revisão final: os testes de interface Android foram compilados, mas não executados nesta rodada. Não houve validação em celular físico. Os testes Python usam serviços simulados ou servidores locais; não constituem nova verificação de todos os serviços externos de download. Os executáveis Windows não possuem assinatura Authenticode.

Preparado para rascunho no GitHub, sem publicação. Chaves, credenciais, cookies, perfis pessoais e o ambiente Testes ficam fora dos arquivos distribuídos.
