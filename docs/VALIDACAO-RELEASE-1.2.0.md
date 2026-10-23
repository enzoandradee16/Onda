# Preparação da release oficial ONDA 1.2.0

Data: 23/10/2026. Destino exclusivo: `Release/1.2.0`. As pastas das versões anteriores são preservadas. A publicação no GitHub não faz parte desta preparação.

## Conteúdo

- Portátil e instalador Windows x64, com versão de produto 1.2.0 e versão numérica 1.2.0.0.
- APKs release separados ARM64 e x86_64, pacote `br.com.onda.mobile`, versão 1.2.0 e código 27. O incremento de 26 para 27 permite atualizar a pré-release com o mesmo nome interno de versão.
- Fontes do aplicativo a partir do commit identificado em SOURCE_MANIFEST.json.
- Fontes de terceiros e das ferramentas nativas Android, reaproveitadas da RC2 após conferir hashes dos arquivos e a ausência de alterações nos registros e receitas locais dessas dependências.
- Notas, instruções de publicação, avisos de terceiros, MANIFEST.json, SOURCE_MANIFEST.json e SHA256SUMS.txt.

## Verificações desta preparação

- Os dois APKs foram recompilados a partir do código corrigido, alinhados e assinados com a chave de produção original. A chave e sua senha permanecem fora do projeto e dos pacotes.
- `apksigner verify` e `zipalign -c -P 16` verificam assinatura e alinhamento. O certificado esperado é SHA-256 `0edd6f5de88fc24b7a45212b51ba7d428030302459e9ed8d619d7dbc29fb81b3`.
- Os APKs são conferidos quanto a pacote, versão, código 27, ABI e ausência da flag debuggable. Os hashes dos três executáveis nativos de cada ABI são comparados com `Android/nativebuild/SHA256SUMS.txt`; o módulo Python de versão também é conferido dentro do APK.
- Os **72 testes JVM da variante release passaram**. O Lint release terminou com **0 erros, 73 avisos e 3 sugestões**.
- O portátil foi montado em uma pasta nova, com o runtime privado existente e os arquivos atuais do aplicativo. O launcher foi recompilado; seu autoteste Qt/QML de 800 × 800 passou com renderização por software.
- Os **3 testes de versão passaram** usando o runtime do novo pacote. Os metadados do launcher e do instalador indicam 1.2.0/1.2.0.0.
- O instalador agora usa uma interface própria WPF, com a frase “Sua ONDA começa aqui.” e o mecanismo Inno Setup embutido. A identidade de instalação e as regras de atualização e desinstalação são preservadas. O executável funciona sem arquivos externos ao lado dele.
- As **9 verificações de integração do novo instalador passaram**, incluindo instalação nova em caminho longo com espaços e acentos, atualização sobre o instalador clássico, criação e remoção de atalhos, abertura do Qt instalado, preservação de configurações e mídia sintéticas e propagação de falhas. Foram comparados 204 arquivos de fontes em cada instalação. Tudo usa outro AppId e atalhos dentro do projeto; a instalação pessoal não é alterada. Consulte `INSTALADOR-WINDOWS.md`.
- Arquivos intermediários de compilação Qt (`objects-*`, `.obj`, `.pdb`, `.lib` e `.exp`) foram excluídos da distribuição; causavam falha de instalação em caminhos longos e não são necessários ao runtime.
- O runtime filtrado foi revalidado com **119 casos aprovados** de versão, Qt e regressões. Na primeira execução, 113 passaram e seis integrações de mídia foram ignoradas por localização das ferramentas; esses seis passaram em uma execução separada com o caminho do FFmpeg/FFprobe e permissão de execução corretos. Não restaram casos ignorados ou com falha nessa seleção após a revalidação.
- A montagem final confere os fontes do portátil contra os arquivos atuais, a integridade dos ZIPs e os hashes dos sete artefatos.

## Validação funcional anterior do mesmo código corrigido

A rodada descrita em [VALIDACAO-RELEASE-2026-10-23.md](VALIDACAO-RELEASE-2026-10-23.md) aprovou **149 testes do pacote Windows, com 4 ignorados**, e **45 testes instrumentados Android** em BlueStacks/Android 11/x86_64, usando o pacote debug isolado `.uitest`. A preparação posterior acrescenta versão, documentação, o novo instalador Windows e botões separados para os filtros de downloads Android. Os APKs foram recompilados com esse ajuste e assinados novamente; os 45 testes instrumentados se referem à rodada anterior, e não a uma nova execução dos APKs finais assinados.

Também passaram consultas públicas reais de catálogos, letras e metadados online. Esses resultados não garantem disponibilidade futura de serviços externos.

## Limites

O Windows permanece sem assinatura Authenticode. Ainda não houve teste dos APKs finais em aparelho físico ARM64, nem atualização da instalação pessoal com estes pacotes. A conferência visual completa no Windows permanece pendente; o autoteste Qt passou, mas a ferramenta de captura da janela falhou na rodada anterior. A preparação oficial identifica a versão e os arquivos distribuíveis e não elimina essas limitações conhecidas.

Os logs locais ficam em `diagnosticos/resultados/release-1.2.0-*.log`, `diagnosticos/resultados/release-1.2.0/`, `diagnosticos/resultados/custom-installer/` e `Android/build/release-1.2.0/`. São ignorados pelo Git. O script `empacotamento/prepare_release.py` monta os pacotes em etapas e recusa substituir uma pasta existente. A atualização do instalador usa primeiro uma pasta candidata nova, com cópia de segurança da preparação anterior fora de `Release`, e só depois atualiza os arquivos da 1.2.0.
