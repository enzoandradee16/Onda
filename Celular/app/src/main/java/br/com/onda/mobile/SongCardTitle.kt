package br.com.onda.mobile

/** Remove an artist prefix only when metadata confirms it. Keep hyphens in song names. */
internal fun songCardTitle(title:String,artist:String):String {
    val name=title.trim()
    if(artist.isBlank())return name
    for(separator in listOf(" - "," – "," — ")) {
        val prefix=artist.trim()+separator
        if(name.startsWith(prefix,ignoreCase=true))return name.substring(prefix.length).trim().ifBlank {name}
    }
    return name
}
