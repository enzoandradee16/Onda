# Instalador próprio do ONDA

A versão 1.2.0 inclui um instalador Windows com interface própria em WPF: cores escuras, verde-água, ondas vetoriais e a frase **“Sua ONDA começa aqui.”**. Há seleção de pasta, opção de atalho, progresso real e abertura do aplicativo ao terminar.

## Funcionamento

O arquivo `Onda-1.2.0-Setup-Windows-x64.exe` reúne a interface e o mecanismo Inno Setup embutido. O mecanismo continua responsável pela instalação dos arquivos, registro do desinstalador, atalhos, atualização e reversão em caso de falha. Mantém o AppId original e reconhece a pasta de uma instalação anterior do mesmo usuário. A interface usa o WPF do .NET Framework presente no Windows; o instalador não baixa um runtime de interface.

O conteúdo embutido tem SHA-256 conferido antes da execução e é extraído em uma pasta temporária exclusiva, com acesso restrito ao usuário atual e ao sistema. A interface exibe progresso recebido do mecanismo local e só informa sucesso após a conclusão e a presença do launcher na pasta escolhida. Erros mantêm a janela aberta, permitem nova tentativa e oferecem o log quando disponível. A instalação pode ser fechada antes de começar; durante a instalação, pode ser minimizada e a janela aguarda a conclusão para fechar. Não é necessário apagar configurações ou baixar novamente o aplicativo para atualizar.

O destino padrão continua sendo `%LOCALAPPDATA%\Programs\Onda`, com instalação por usuário. O usuário pode escolher outra pasta local com permissão de escrita. As opções `/SILENT` e `/VERYSILENT` continuam encaminhadas ao mecanismo original, com preservação dos argumentos e códigos de saída. O desinstalador continua com as confirmações existentes para dados pessoais e ferramentas baixadas.

## Construção

O frontend usa `Installer.cs`, `Installer.xaml` e `Installer.manifest`, compilados com o compilador C# do Windows e as bibliotecas WPF do sistema. O número de versão é gerado a partir de `Onda/app_version.py`. O arquivo resultante contém todos os recursos necessários ao instalador.

```powershell
python empacotamento/build_installer.py --bundle CAMINHO_DO_PORTATIL --output PASTA_DE_SAIDA
```

`prepare_release.py windows` usa esse construtor automaticamente. `--work` permite uma pasta de trabalho nova; `--release-output` permite montar uma pasta candidata sem substituir uma release existente. O portátil exclui caches e intermediários de compilação do Qt que não são necessários em execução.

## Testes isolados

```powershell
python empacotamento/build_installer.py --bundle CAMINHO_DO_PORTATIL --output PASTA_DE_AUDITORIA --audit
python empacotamento/test_installer.py --audit PASTA_DE_AUDITORIA --bundle CAMINHO_DO_PORTATIL --output PASTA_NOVA_DE_RESULTADOS
```

O teste recusa uma receita com o AppId de produção ou atalhos pessoais. Usa outro AppId, dados sintéticos e atalhos dentro do projeto. Confere os arquivos instalados, executa o autoteste do launcher Qt, verifica instalação nova, atualização a partir do mecanismo clássico, atalhos, desinstalação com preservação dos dados e retorno de falha quando o destino é um arquivo. O primeiro ensaio encontrou intermediários do Qt que impediam a instalação em caminhos longos; esses arquivos foram removidos do empacotamento antes da revalidação.

As nove verificações de integração passaram, com comparação de 204 arquivos por instalação. O runtime sem intermediários Qt também aprovou 119 casos de versão, interface e regressões, incluindo seis integrações reais de mídia executadas separadamente com FFmpeg/FFprobe.

`--self-test ARQUIVO.json` verifica o frontend e a integridade do mecanismo embutido sem instalar. `--render-preview ARQUIVO.png [configure|installing|done]` renderiza a própria árvore WPF para conferir visual e layout sem executar uma instalação. Isso é renderização do componente, não captura da área de trabalho. A janela nativa também foi aberta e seus controles inspecionados pela árvore de acessibilidade; a captura nativa da ferramenta continuou falhando por timeout.

Os resultados ficam em `diagnosticos/resultados/custom-installer/`. O Windows continua sem assinatura Authenticode. A nova interface não altera os limites da validação Android descritos no relatório de release.
