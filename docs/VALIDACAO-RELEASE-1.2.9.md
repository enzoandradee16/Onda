# Validação do ONDA 1.2.9

## Verificações de 10/11/2026

- Windows: abertura do aplicativo, instalador e desinstalador aprovados nos autotestes do pacote final.
- PC: sete testes direcionados aprovados para redimensionamento, espaçamento de capa/título, controles, configurações e continuidade da música ao selecionar outra na pesquisa.
- Android: 109 testes unitários aprovados, sem falhas, erros ou testes ignorados.
- APKs ARM64 e x86_64: integridade ZIP, arquitetura, versão 1.2.9, código 37, assinatura de produção e alinhamento de 16 KB conferidos.
- Fontes de terceiros: versões e hashes dos arquivos conferidos antes do empacotamento.
- READMEs e notas: informações do produto, sem observações sobre rascunhos ou etapas internas de preparação.

## Instalação e desinstalação no Windows

Nove testes do instalador e sete do desinstalador foram aprovados nesta sessão. Os relatórios da pasta `release-1.2.9-manual-20261110-140218` foram preservados. O conteúdo do aplicativo e do runtime foi comparado por SHA-256 com o pacote final e é idêntico; somente a documentação do pacote foi atualizada.

Os cenários incluem instalação nova, abertura do aplicativo instalado, atualização, atalhos, preservação dos dados, cancelamento, remoção opcional de dados/ferramentas e rejeição de componente adulterado. O registro da instalação de uso diário foi preservado.

## Limites

Não foi executada uma nova rodada de testes instrumentados nem um teste físico ARM64 nesta preparação. Os testes de interface anteriores permanecem documentados nos relatórios locais. Os resultados não garantem todos os fluxos de reprodução nem a disponibilidade dos serviços externos.
