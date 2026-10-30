# Guias do ONDA

Referências de uso revisadas para **1.2.4**, em 27/10/2026.

## Uso atual

| Guia | Conteúdo |
| --- | --- |
| [Inventário completo](INVENTARIO-FUNCIONALIDADES.md) | Funcionalidades, diferenças PC/Android, limitações, configurações e índice técnico |
| [Reprodução unificada](REPRODUCAO-UNIFICADA.md) | Efeitos e Jukebox na mesma tela, fila, processamento e migração de sessões |
| [Reprodução remota — teste](CONTROLE-REMOTO.md) | Player, fila e notificação Android para controlar o ONDA PC na rede local |
| [Recursos avançados](../RECURSOS-AVANCADOS.md) | Downloads, retomada, edição, letras, agendamento, cache e atualização |
| [Configurações](CONFIGURACOES.md) | Categorias, busca, aparência, persistência e opções específicas |
| [Ferramentas e clareza dos estados](CLAREZA-DE-ESTADOS.md) | Verificação de ferramentas, cobertura de coleções e falhas de preparação por faixa |
| [Jukebox](JUKEBOX.md) | Reprodução, filas, equalizador, letras e restauração de sessão |
| [Links e fila](FILA-SEPARADA.md) | Organização das telas no PC e em Downloads no Android |
| [Atalhos PC](ATALHOS-PC.md) | Teclado, menus, filas e navegação |
| [Interface Qt](INTERFACE-QT.md) | Estrutura da interface Windows atual |
| [Uso e desenvolvimento PC](../Onda/README.md) | Ambiente, execução, ferramentas e empacotamento |
| [Manual Android](../Android/README.md) | Instalação, navegação, armazenamento, compilação e atualização |
| [Funcionalidades Android](../Android/FUNCIONALIDADES.md) | Recursos atuais por área |

## Planejamento

- [Ideias futuras](IDEIAS-FUTURAS.md): controle entre PC e Android, Spotify e MusicBrainz + AcoustID. Propostas ainda não implementadas.

## Relatórios históricos e validações

Documentos de revisão, paridade e resultados de testes registram uma versão e uma execução específicas. Descrições antigas de botões, caminhos e recursos ausentes não substituem os guias acima. Atualizar documentação não significa reexecutar os testes descritos.

- [Validação 1.2.3](VALIDACAO-RELEASE-1.2.3.md).
- [Comparação histórica PC × Android](../Android/PARIDADE-PC-ANDROID.md).
- [Paridade de reprodução em 23/10/2026](PARIDADE-ANDROID-2026-10-23.md).
- [Navegação e configurações: implementação anterior](NAVEGACAO.md).
- [Filas grandes e sessão YouTube: implementação anterior](ANDROID-FILAS-GRANDES.md).

## Referências técnicas

Os contratos e fontes citados nos guias prevalecem ao investigar um comportamento. Arquivos de defaults e índices de busca podem conservar chaves ou textos legados sem controle visível atual. Consulte a interface Qt/Compose e o controlador correspondente antes de concluir que uma opção está disponível.
