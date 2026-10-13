# Revisão e otimização do ONDA — 12/10/2026

## Escopo e método

Varredura dos **139 arquivos próprios de código e configuração**, somando 16,899 linhas. O [inventário completo](inventario-revisao.json) registra cada arquivo e o método de validação. Abrange Python do PC, motor compartilhado, adaptador Android, Kotlin, testes, scripts, manifesto, recursos XML, Gradle, launcher C# e instalador Inno Setup.

Todos os Python foram analisados por AST e compilação sintática. Foram examinados imports/referências, loops, persistência, cancelamento, processamento de mídia, interfaces e composição dos pacotes. Os caminhos com trabalho repetido receberam revisão aprofundada e testes de regressão. Kotlin e recursos passaram pelo compilador e Android lint; PowerShell passou pelo parser. Bibliotecas de terceiros e suas cópias geradas não foram reescritas; foram examinadas como dependências e pelo tamanho dos pacotes. O inventário não significa teste manual de cada função nem auditoria do código-fonte de todas as dependências.

## Alterações no PC

- Capas da pesquisa agora são reduzidas pelo Pillow já disponível, preservando proporções. Isso elimina um processo FFmpeg por miniatura. Cache limitado a 48 miniaturas evita repetir downloads e conversões ao retornar à mesma capa; não afeta a capa de alta resolução gravada no áudio.
- Eventos de título da fila são persistidos uma vez por lote de eventos da interface. Teste com 100 títulos confirma uma gravação e restauração dos 100 nomes; antes, esse caminho gravava a fila inteira em cada evento.
- Pesquisa do histórico aguarda 180 ms após digitar e cancela a busca anterior. Resultados iguais não recriam a tabela e preservam a seleção. Consultar sem filtro evita uma condição de texto desnecessária no SQLite.
- Removido import sem uso em metadados e imports sem uso dos testes. Imports diagnósticos e helpers reexportados foram preservados depois de conferir os chamadores.
- Corrigidas comparações dos testes para aceitar caminhos Windows curtos e completos equivalentes. O destino dos arquivos no programa não foi alterado.

## Alterações no Android

- APK padrão ARM64: **128.3 MB → 77.1 MB**, redução de **39.9%** (51.2 MB). Medidas são do APK, não do tamanho instalado. Emulador x86_64 continua disponível por compilação separada; `-Arquitetura universal` inclui ambas as arquiteturas quando necessário.
- Retiradas ferramentas de inspeção/preview Compose não utilizadas. Excluídos sete módulos exclusivos do PC do motor distribuído no Android: appearance, interface_fonts, library, reset_settings e três seletores Tk. Os 28 módulos compartilhados restantes não importam tkinter.
- Adicionar um item atualiza a fila em memória sem consultar novamente fila e histórico inteiros. Lotes usam transação e atualizam a fila uma vez. Remoções usam uma transação; alterações do histórico não recarregam a fila. Atualizações sem mudança são ignoradas.
- Recarregar a fila preserva progresso e mensagem em memória. Configurações salvas são decodificadas uma vez na inicialização; enfileirar não decifra a credencial Spotify que será injetada pelo serviço na execução.
- Conferência de correspondências indexa retornos por URL uma vez, em vez de procurar novamente em todos os retornos para cada faixa. Teste com 2000 músicas preserva ordem, itens não conferidos e a primeira correspondência de URLs repetidas.
- Filtros de playlists, histórico e fila da pesquisa são reaproveitados enquanto seus dados não mudam. O serviço indexa os IDs do lote em conjunto para evitar procura linear a cada comparação.
- Depois de publicar e registrar um arquivo com sucesso, a cópia intermediária criada pelo ONDA é removida. Isso se aplica somente à pasta privada padrão e a exportações MediaStore/SAF. Entradas externas e fontes FileProvider do Android 8/9 são mantidas. Dados antigos existentes não foram apagados.
- Resolvidos erros de lint: observação do estado ativo na tela, opt-in explícito da API Media3 e escape do caminho SDK. O override público de teclado mantém uma supressão localizada e comentada para a anotação interna da ponte AndroidX. A extração nativa fica definida pelo Gradle, sem declaração duplicada no manifesto.
- Builds agora registram a arquitetura como entrada da preparação nativa, garantindo que trocar de ARM64 para x86_64 regenere as ferramentas corretas.

## Alteração compartilhada

SVG passa a incorporar o PNG uma única vez, eliminando a duplicação entre `href` e `xlink:href`. Dimensões, transparência e prévia continuam cobertas por testes. A economia depende da imagem; quando o conteúdo incorporado domina o arquivo, aproxima-se da metade do tamanho.

## Validação

- **PC: 271 testes, todos aprovados, sem testes ignorados**, com UI Tk e FFmpeg ativados; 51,586 segundos nesta execução. Inclui renderização de efeitos, tags/capa, publicação, duplicados, playlists e as novas regressões de histórico/fila/miniaturas.
- **Android: 24 testes instrumentados aprovados** no emulador Android API 36 x86_64, em 69,604 segundos. Classes StoreOptimizationTest, MobileRuntimeTest e NavigationTest: fila, rollback, exportação, credenciais fictícias, download local, efeitos nativos, navegação, teclado, temas/fontes, avisos e seleções.
- Android lint: **zero erros**, 41 avisos e 2 observações. Permanecem avisos como versões de dependências, target SDK, contextos de aplicação e gravação síncrona de credenciais. Não foi usado um baseline para ocultar erros.
- APK final recompilado em ARM64, assinatura validada, versionName `1.0.0-alpha.1`, versionCode `14`. Arquivo SHA256SUMS atualizado. O APK testado no emulador usa x86_64 com o mesmo código; o APK ARM64 precisa de teste final no aparelho real.
- Portátil Windows atualizado e diagnóstico `Onda.exe --self-test` aprovado: seis abas, Python, Node e ferramentas de mídia disponíveis. Instalador recompilado com Inno Setup.
- `git diff --check` aprovado. Nenhum commit, push ou publicação foi feito nesta revisão.

## Limites e próximos testes

Não foi medida taxa de quadros, bateria ou memória em aparelho físico; os ganhos comprovados são tamanho do APK, eliminação de trabalho repetido e regressões funcionais. Buscas, logins e downloads reais de cada plataforma precisam de teste com a conexão/conta do usuário. Bloqueios externos não são resolvidos por otimização.

O tamanho do runtime Windows permanece praticamente igual: Python, Node, decodificadores e extratores continuam necessários às funcionalidades atuais. Não há uma redução percentual comprovada do espaço instalado no PC. Arquivos pessoais, preferências e downloads existentes foram preservados.

## Pacotes atualizados

- `Celular/APK/ONDA-Android-1.0.0-alpha.1.apk` — ARM64; SHA-256 `252a23cf6cfd333a96189b5687c63763fb738fb4930079cba0d9c6df6356d410`.
- `Portatil/Onda.exe` — launcher existente com os módulos atualizados ao lado.
- `Instalador/Onda-Setup.exe` — instalador Windows recompilado.
