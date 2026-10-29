# Validação local — ONDA 1.2.4

Data: 28/10/2026. Versões: Windows 1.2.4.0; Android 1.2.4, código 31.

## Auditoria e correções

- Corrigido o volume do miniplayer: o gesto agora atualiza os parâmetros do áudio, além do slider.
- Finalizações de preparação pertencentes a uma operação antiga são ignoradas. Cancelamentos válidos voltam a faixa ao estado pendente e liberam a preparação seguinte.
- Falhas temporárias na obtenção de capas não ficam memorizadas no cache de fundos; uma capa inválida não mantém o fundo do álbum anterior.
- Duplo clique restrito às músicas das filas de reprodução, preservando a interação dos demais componentes de arraste.
- Removido o componente EffectsMiniPlayer.qml e seus caminhos obsoletos; mantido o miniplayer unificado.
- Removidos imports duplicados, imports sem uso e variáveis descartadas. Importações de diagnóstico continuam verificando a disponibilidade das dependências.
- Não foram removidos os motores de áudio, a interface legada e os utilitários de empacotamento necessários à compatibilidade e aos testes.

## Testes executados

| Grupo | Resultado |
| --- | --- |
| Descoberta completa dos testes Python | 1.151 encontrados; 727 executados sem falhas; 424 condicionais ignorados |
| Reprodução, letras, restauração e transições Qt | 70 testes aprovados |
| Interface Qt em janela Windows, miniplayer, filas e navegação | 47 testes aprovados |
| Android JVM | 87 testes aprovados, sem falhas |
| Android debug e APK de instrumentação | Compilação concluída |
| Análise estática Python de produção | Sem nomes indefinidos ou imports sem uso identificados pelo Pyflakes |

Os grupos possuem cobertura sobreposta; seus totais não devem ser somados como testes únicos. Os testes condicionais incluem interfaces opcionais e integrações externas. As capturas do Swirl foram verificadas com a plataforma Windows: a captura offscreen não reproduziu a animação.

## Pacotes e limites

Os APKs ARM64 e x86_64 são conferidos quanto à versão, arquitetura, assinatura original, alinhamento de 16 KB, ferramentas nativas e licenças. O portátil, instalador e desinstalador Windows passam pelos respectivos autotestes. Manifestos e hashes acompanham os sete pacotes.

O emulador não estava acessível por ADB nesta rodada; testes de instrumentação não foram executados. Não houve validação em celular físico. O executável Windows não possui assinatura Authenticode.

Preparação para rascunho da release no GitHub, sem publicação. Os manifestos registram o commit e os hashes dos fontes utilizados; os APKs preparados anteriormente foram conferidos contra os mesmos fontes Android e compartilhados antes de associá-los ao commit final. Chaves de assinatura, credenciais, cookies, perfis pessoais e o ambiente Testes não integram os pacotes.
