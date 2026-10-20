# APKs Android 1.2.0

- versionName 1.2.0, versionCode 26, pacote br.com.onda.mobile.
- Builds release ARM64 e x86_64 concluídos, incluindo lint vital.
- APKs sem a flag debuggable, alinhados com zipalign para páginas de 16 KB.
- Assinaturas verificadas com apksigner; certificado original preservado: SHA-256 0edd6f5de88fc24b7a45212b51ba7d428030302459e9ed8d619d7dbc29fb81b3.
- Atualização de produção 1.1.7/code25 para 1.2.0/code26 validada no emulador x86_64 API 36 usando install -r. firstInstallTime preservado, sem desinstalação, e atividade iniciada com processo ativo.
- ARM64: compilação, manifesto, arquitetura, alinhamento e assinatura verificados. Esta rodada não inclui teste em aparelho físico.
- APKs e hashes ficam em Celular/APK. Nenhuma publicação no GitHub foi realizada nesta preparação.

## Ajustes visuais e arraste entre páginas — somente x86_64

Navegação horizontal animada, mantendo os gestos dos sliders; capas das listas maiores; concluídos recentes abaixo dos downloads ativos; controles e layout do Jukebox aproximados das referências. Seis testes instrumentados de interface aprovados no emulador, incluindo navegação nas duas direções e alteração dos dois sliders sem sair da página. APK x86_64 release recompilado, alinhado e assinado novamente com o certificado original. ARM64 não recompilado nesta rodada.
