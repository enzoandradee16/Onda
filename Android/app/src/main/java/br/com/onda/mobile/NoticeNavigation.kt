package br.com.onda.mobile

/** Interpret only explicit settings guidance in canonical (untranslated) notices. */
internal fun noticeDestination(message:String):String? {
    if(message.contains("YouTube",ignoreCase=true) && listOf("Menu → Sessão do YouTube","Atualize a sessão","Abra a sessão do YouTube").any {message.contains(it,ignoreCase=true)})return "Sessão do YouTube"
    if(message.contains("Configurações → Redes sociais",ignoreCase=true))return "Contas"
    if(message.contains("cookies",ignoreCase=true) && listOf("em Configurações","importar cookies","Importar cookies","formato Netscape").any {message.contains(it,ignoreCase=true)})return "Contas"
    if(listOf("atualize o yt-dlp","FFmpeg e ffprobe não encontrados").any {message.contains(it,ignoreCase=true)})return "Ferramentas"
    val path=Regex("""Configurações\s*(?:→|>|/)\s*(Ferramentas|Contas|Aparência|Geral|Downloads|Imagens|Áudio)""",RegexOption.IGNORE_CASE).find(message)
    if(path!=null)return listOf("Ferramentas","Contas","Aparência","Geral","Downloads","Imagens","Áudio").first {it.equals(path.groupValues[1],ignoreCase=true)}
    if(message.contains("Spotify",ignoreCase=true) && listOf(
        "Conectar Spotify","Conecte sua conta Spotify","reconecte sua conta",
        "Spotify Client ID","conectar sua conta","conectar ao Spotify"
    ).any {message.contains(it,ignoreCase=true)})return "Contas"
    return null
}
