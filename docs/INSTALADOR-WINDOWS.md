# Instalador próprio do ONDA

A versão 1.2.0 inclui um instalador Windows com interface própria em WPF: cores escuras, verde-água, ondas vetoriais e a frase **“Sua ONDA começa aqui.”**. Há seleção de pasta, opção de atalho, progresso real e abertura do aplicativo ao terminar.

O seletor de idioma aparece desde a abertura, com **Português (Brasil)**, **Español** e **English**, nessa ordem. Português é o padrão. A troca é imediata e preserva a pasta e a opção de atalho. Títulos, botões, descrições acessíveis, mensagens de validação, progresso, erros e conclusão usam 40 textos do instalador por idioma, em um catálogo compartilhado de 70 textos com o desinstalador. Durante a instalação o seletor fica desativado, mantendo o mesmo idioma até a conclusão. O mecanismo embutido e as confirmações do desinstalador usam o idioma escolhido. Essa seleção não modifica a preferência de idioma do aplicativo.

## Funcionamento

O arquivo `Onda-1.2.0-Setup-Windows-x64.exe` reúne a interface e o mecanismo Inno Setup embutido. O mecanismo continua responsável pela instalação dos arquivos, registro do desinstalador, atalhos, atualização e reversão em caso de falha. Mantém o AppId original e reconhece a pasta de uma instalação anterior do mesmo usuário. A interface usa o WPF do .NET Framework presente no Windows; o instalador não baixa um runtime de interface.

O conteúdo embutido tem SHA-256 conferido antes da execução e é extraído em uma pasta temporária exclusiva, com acesso restrito ao usuário atual e ao sistema. A interface exibe progresso recebido do mecanismo local e só informa sucesso após a conclusão e a presença do launcher na pasta escolhida. Erros mantêm a janela aberta, permitem nova tentativa e oferecem o log quando disponível. A instalação pode ser fechada antes de começar; durante a instalação, pode ser minimizada e a janela aguarda a conclusão para fechar. Não é necessário apagar configurações ou baixar novamente o aplicativo para atualizar.

O destino padrão continua sendo `%LOCALAPPDATA%\Programs\Onda`, com instalação por usuário. O usuário pode escolher outra pasta local com permissão de escrita. As opções `/SILENT` e `/VERYSILENT` continuam encaminhadas ao mecanismo original, com preservação dos argumentos e códigos de saída. O desinstalador continua com as confirmações existentes para dados pessoais e ferramentas baixadas.

## Construção

O frontend usa `Installer.cs`, `InstallerText.cs`, `InstallerStrings.xml`, `Installer.xaml` e `Installer.manifest`, compilados com o compilador C# do Windows e as bibliotecas WPF do sistema. O número de versão é gerado a partir de `Onda/app_version.py`. O arquivo resultante contém todos os recursos necessários ao instalador.

```powershell
python empacotamento/build_installer.py --bundle CAMINHO_DO_PORTATIL --output PASTA_DE_SAIDA
```

`prepare_release.py windows` usa esse construtor automaticamente. `--work` permite uma pasta de trabalho nova; `--release-output` permite montar uma pasta candidata sem substituir uma release existente. `--allow-uncommitted` registra alterações locais nos manifestos, incluindo arquivos novos e excluindo os removidos; `--base-commit` identifica o commit de base. O portátil exclui caches e intermediários de compilação do Qt que não são necessários em execução.

## Testes isolados

```powershell
python empacotamento/build_installer.py --bundle CAMINHO_DO_PORTATIL --output PASTA_DE_AUDITORIA --audit
python empacotamento/test_installer.py --audit PASTA_DE_AUDITORIA --bundle CAMINHO_DO_PORTATIL --output PASTA_NOVA_DE_RESULTADOS
```

O teste recusa uma receita com o AppId de produção ou atalhos pessoais. Usa outro AppId, dados sintéticos e atalhos dentro do projeto. Confere os arquivos instalados, executa o autoteste do launcher Qt, verifica instalação nova, atualização a partir do mecanismo clássico, atalhos, desinstalação com preservação dos dados e retorno de falha quando o destino é um arquivo. O primeiro ensaio encontrou intermediários do Qt que impediam a instalação em caminhos longos; esses arquivos foram removidos do empacotamento antes da revalidação.

As nove verificações de integração passaram, com comparação dos arquivos de fontes por instalação (205 na preparação final). O runtime sem intermediários Qt também aprovou 119 casos de versão, interface e regressões, incluindo seis integrações reais de mídia executadas separadamente com FFmpeg/FFprobe.

`--self-test ARQUIVO.json` verifica o frontend e a integridade do mecanismo embutido sem instalar. `--render-preview ARQUIVO.png [configure|installing|done]` renderiza a própria árvore WPF para conferir visual e layout sem executar uma instalação. Isso é renderização do componente, não captura da área de trabalho. A janela nativa também foi aberta e seus controles inspecionados pela árvore de acessibilidade; a captura nativa da ferramenta continuou falhando por timeout.

`/LANG=brazilianportuguese`, `/LANG=spanish` e `/LANG=english` selecionam o idioma por linha de comando; as formas `pt-BR`, `es` e `en` também são normalizadas para o mecanismo embutido. Por exemplo: `--render-preview ingles.png configure /LANG=english`. O autoteste percorre os três idiomas e verifica as telas, mensagens, marcadores de substituição e a preservação das opções. Os testes de integração usam instalação em inglês, modo clássico em português e atualização em espanhol, com atalhos de desinstalação traduzidos.

A preparação final fica em `diagnosticos/resultados/release-1.2.0-final/`; rodadas anteriores ficam em `diagnosticos/resultados/custom-installer/` e `diagnosticos/resultados/installer-languages/`. O Windows continua sem assinatura Authenticode. A nova interface não altera os limites da validação Android descritos no relatório de release.

## Desinstalador próprio — 1.2.0

A janela usa o mesmo estilo do instalador e os textos do protótipo: **“Até a próxima ONDA.”**, **“Obrigado por fazer parte dessa ONDA.”**, **“Desinstalar o ONDA?”**, **“O aplicativo será removido deste computador.”**, **“Pasta instalada”**, **“Apagar configurações, fila e histórico”**, **“Remover ferramentas baixadas (FFmpeg)”**, **“Downloads e arquivos pessoais serão preservados.”**, **“Desinstalar ONDA”** e **“Cancelar”**.

As duas opções começam desativadas. São independentes e afetam apenas os arquivos conhecidos do ONDA; dados e ferramentas são compartilhados com o portátil no mesmo PC. Músicas, vídeos, imagens, cookies e ferramentas pessoais não são removidos. A limpeza de ferramentas usa uma lista de arquivos do cache de FFmpeg, sem apagar pastas de forma recursiva. Diretórios redirecionados são recusados na limpeza.

O idioma inicial acompanha a instalação e pode ser trocado entre português, espanhol e inglês sem alterar as opções marcadas nem o idioma do app. Depois de confirmar, os controles ficam desativados enquanto o mecanismo trabalha. Erros mantêm a janela disponível, com acesso ao log; a conclusão só aparece após o mecanismo sinalizar o término e a remoção do launcher. Uma limpeza parcial informa o problema em vez de declarar sucesso completo.

`Desinstalar ONDA.exe` é instalado junto ao aplicativo, registra a entrada de desinstalação do Windows e o atalho traduzido, preservando o AppId original. O mecanismo Inno continua responsável pela transação, pelos arquivos e pelo registro. A interface verifica pasta registrada, arquivos de mecanismo e sua própria integridade; executa uma cópia temporária privada para permitir remover o executável instalado. A cópia temporária é limpa ao fechar e o log permanece disponível. A remoção silenciosa normal continua pelo mecanismo original e mantém dados e ferramentas.

O construtor compila `Uninstaller.cs` e `Uninstaller.xaml`, usando o catálogo compartilhado, e inclui o executável no mecanismo embutido do instalador. Não é necessário no portátil nem baixa dependências de interface. `--self-test` valida idiomas/estados/padrões seguros; `--render-preview` renderiza a janela sem remover nada. Comandos automatizados de remoção de testes existem apenas na compilação de auditoria.

```powershell
python empacotamento/test_uninstaller.py --audit PASTA_DE_AUDITORIA --output PASTA_NOVA_DE_RESULTADOS
```

As sete verificações direcionadas cobrem idiomas/estados, cancelamento real da janela, as quatro combinações de limpeza, rejeição de integridade adulterada e preservação de mídias, cookies e ferramentas pessoais. O registro de produção é comparado antes e depois. Os testes com payload completo também cobrem instalação nova, atualização, atalhos, abertura do Qt instalado e remoção silenciosa compatível. Relatórios em `diagnosticos/resultados/uninstaller-1.2.0/`.
