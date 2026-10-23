# Validação adicional de release — 23/10/2026

Esta rodada complementa `REVISAO-2026-10-23.md`. O desktop foi validado a partir do commit `a17122a`; o Android foi recompilado com as correções adicionais descritas abaixo. Os resultados desta rodada substituem a limitação anterior de que os testes instrumentados Android só haviam sido compilados.

## Correções encontradas no Android em execução

- **Retomar reprodução com efeitos:** o comando Play da sessão de mídia consultava uma fotografia do player que podia continuar indicando reprodução depois de pausar e buscar outra posição. O serviço agora consulta o estado atual do controlador, e a pausa publica imediatamente o estado de mídia. O teste existente de pausa, busca e retomada reproduziu a falha antes da correção e passou depois dela.
- **Navegar durante uma transição da Jukebox:** o controlador descartava comandos enquanto uma transição estava ativa. Agora conserva atomicamente o pedido mais recente e o executa após a transição em andamento, mantendo a mesma saída de áudio. Limpar a fila ou remover o destino também cancela pedidos pendentes correspondentes. O teste de próxima faixa seguida de anterior reproduziu a falha e passou após a correção.

Os testes de interface foram atualizados para a navegação atual por “Mais”, o menu de ações do histórico e o player compacto/expandido compartilhado. Comparações de arquivos usam caminhos canônicos para reconhecer `/data/data` e `/data/user/0` como o mesmo arquivo. O teste de downloads paralelos desativa deliberadamente a detecção de duplicatas de sua mídia sintética repetida; essa detecção abria corretamente uma confirmação e impedia o segundo download. O teste de mídia também limpa sua fila temporária no início e no final para evitar interferência entre classes.

## Windows

Foi preparado um pacote portátil de diagnóstico separado, com o launcher original compilado, o runtime privado e 204 arquivos atuais do aplicativo. Os hashes desses arquivos foram registrados e comparados com a instalação de diagnóstico.

- O launcher portátil e o launcher instalado passaram no autoteste Qt/QML de 800 × 800, usando renderização por software.
- A suíte executada com o Python e os módulos do pacote reportou **153 casos: 149 aprovados e 4 ignorados**, sem falhas ou erros. Inclui os 71 testes Qt, 45 regressões e verificações do motor compartilhado. Os quatro casos ignorados não são contados como aprovados.
- Consultas reais anônimas passaram em Deezer, Apple/iTunes, Spotify público, LRCLIB e metadados do YouTube. Foram conferidos resultados, título, capa quando aplicável e duração do vídeo de referência. Isso valida essas operações no momento da execução, não todas as possibilidades de download dos serviços.
- O instalador foi compilado com a receita do projeto e identificação, destino e perfil exclusivos para diagnóstico. Instalação silenciosa: código 0; os 204 arquivos conferiram; o launcher instalado passou no autoteste. Desinstalação silenciosa: código 0; removeu o launcher e preservou as configurações e o download sintéticos. Ficaram diretórios com caches Python criados pela execução.
- A janela Qt nativa foi aberta em um perfil separado e a árvore de acessibilidade ficou disponível. A captura de janela e a geometria de clique da ferramenta falharam; portanto, **a navegação visual manual completa no Windows não foi validada**.

## Android

O usuário habilitou o ADB no BlueStacks existente. Foram usados Android 11/x86_64 e apenas os pacotes `br.com.onda.mobile.uitest` e `br.com.onda.mobile.uitest.test`. A instalação de produção `br.com.onda.mobile` não foi substituída, limpa nem desinstalada.

A compilação final debug, os **72 testes JVM** e o Lint passaram. O Lint reportou **0 erros, 73 avisos e 3 sugestões**, sem baseline para ocultá-los.

A bateria instrumentada selecionada terminou com **45 casos aprovados em 13 classes**. Na rodada conjunta, 44 passaram e um teste ainda usava ações antigas do editor; após atualizar esse fluxo, os cinco casos de `AdvancedFeatureTest` foram reexecutados e passaram. Os casos já aprovados das demais classes não foram repetidos sem necessidade.

| Classe | Casos |
| --- | ---: |
| PlaybackParityUiTest | 7 |
| JukeboxMediaTest | 5 |
| AdvancedFeatureTest | 5 |
| BatchMetadataUiTest | 2 |
| AccessibilityTest | 2 |
| AndroidShellTest | 5 |
| PreferenceRecoveryTest | 2 |
| ToolsStorageTest | 2 |
| StoreOptimizationTest | 4 |
| MobileRuntimeTest | 3 |
| MetadataOverwriteTest | 3 |
| VideoConverterTest | 2 |
| LiveCatalogTest | 3 |

Essa bateria exercita o FFmpeg nativo, conversão, edição e publicação de mídia sintética, preservação dos originais, downloads paralelos por HTTP local, recuperação de preferências, controles de reprodução e notificações, troca de faixas, acessibilidade, navegação e consultas reais a catálogos e metadados online. Não corresponde a todos os testes instrumentados existentes no repositório.

Comandos de construção, executados em `Android/` com o JDK e o cache Gradle locais:

```powershell
./gradlew.bat --offline --console=plain '-Ponda.buildPython=E:/Projetos/Onda/Portatil/_runtime/python/python.exe' '-Ponda.abis=x86_64' '-Ponda.isolatedUiTest=true' :app:assembleDebug :app:assembleDebugAndroidTest :app:testDebugUnitTest :app:lintDebug
```

Cada classe foi executada separadamente para isolar seu processo, pelo comando abaixo, substituindo `CLASSE` pelo nome da tabela:

```powershell
adb -s 127.0.0.1:5555 shell am instrument -w -e liveNetwork true -e liveSpotify true -e liveYoutube true -e class br.com.onda.mobile.CLASSE br.com.onda.mobile.uitest.test/androidx.test.runner.AndroidJUnitRunner
```

## Pacotes oficiais e limites

Os sete arquivos existentes em `Release/1.2.0-rc2` conferiram em tamanho e SHA-256 com o manifesto, e a integridade dos ZIPs foi verificada. Entretanto, o manifesto identifica o commit **`d26e575`**: esses pacotes **não contêm as correções de `a17122a` nem desta rodada**. Antes de distribuir a versão oficial é necessário gerar os pacotes finais a partir do código corrigido e conferir seus manifestos e assinaturas.

Ainda ficam pendentes um aparelho físico ARM64, a validação visual completa no Windows e o teste dos pacotes finais de distribuição. A execução em BlueStacks usa um APK debug x86_64 isolado; não comprova o comportamento do APK release assinado em todas as versões de Android. Nenhum release foi publicado nesta rodada.

Logs, manifestos e pacotes temporários ficam em `diagnosticos/resultados/release-a17122a/`, ignorado pelo Git. Os principais registros são `packaged-tests.json`, `launcher-test.json`, `installer-verification.json`, `installer-uninstall.log`, `live-results.json`, `existing-release-check.json`, `android-ui-results.json`, `android-final-results.json`, `android-AdvancedFeatureTest-final.log`, os logs por classe e `android-final-build.log`.
