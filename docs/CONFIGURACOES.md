# Organização das configurações

## Preferências usadas nas novas janelas — 1.2.0

**Downloads → Formato de álbuns e playlists:** esse formato e as qualidades MP3/M4A da mesma categoria fornecem a seleção inicial da janela de download da pesquisa no PC. Escolher outro valor nessa janela afeta somente a faixa confirmada.

**Aparência → Minimizar ONDA ao abrir o miniplayer:** ativada minimiza a principal e mantém o miniplayer visível; desativada abre o miniplayer sem minimizar a principal. Alterações são aplicadas na próxima abertura do player. Não controla o botão de minimizar do próprio miniplayer.

O seletor de idioma do instalador é independente da preferência de idioma do aplicativo.

PC e Android usam a ordem de categorias definida em `Onda/settings_schema/layout.json`.

| Categoria | Ordem dos grupos |
| --- | --- |
| Geral | Idioma, lembrar configurações, avisos, exportar/importar, restauração |
| Aparência | Tema, separações, destaque, espaçamento, fontes, fila, histórico, ordem das abas |
| Downloads | Formato/qualidade, destino, organização/nomes, arquivos existentes, playlists, metadados/versão, execução/agendamento |
| Imagens | Formato, dimensões, proporção |
| Áudio | Prévias nas pesquisas, prévias dos efeitos, continuar prévia em outras abas |
| Contas | Spotify, YouTube e cookies |
| Ferramentas | Cache, atualização do ONDA, ferramentas de download |

As opções comuns seguem a mesma ordem relativa; controles exclusivos de um sistema ficam no grupo correspondente. Os atalhos nas abas principais continuam usando as mesmas preferências. Nenhuma preferência salva é redefinida por esta reorganização.

A pesquisa e a restauração por categoria seguem essa distribuição. O índice Android de pesquisa fica em `Celular/app/src/main/assets/settings_search.json` e deve acompanhar mudanças nos controles.

## Paridade dos controles

O contrato `common_options` do arquivo compartilhado lista os controles presentes nas duas versões. Testes conferem as categorias e a existência desses controles. Formatos, duração de prévias e tamanhos máximos das imagens usam as mesmas opções.

No PC, animar avisos usa uma transição de cor; o Android usa a animação de entrada e saída própria da plataforma. Mostrar ações antes das listas também funciona no PC. Confirmar a versão é aplicado no início de cada download, inclusive com execução paralela; a escolha automática continua tendo prioridade.

Os controles de Spotify e cookies ficam em Contas nas duas versões. No PC, a proteção de credenciais usa o Windows e os arquivos de cookies importados ficam restritos à sessão. Não são copiados para fila salva ou exportação de configurações.

Diferenças necessárias: fontes disponíveis no sistema, seletor de pastas, proteção das credenciais e limite de execução simultânea (PC: 1–15; Android: 1–4). A pasta e a preparação manual de FFmpeg são controles específicos do PC.
