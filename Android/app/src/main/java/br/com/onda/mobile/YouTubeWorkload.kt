package br.com.onda.mobile

import java.net.URI

internal fun usesYouTube(url:String, mode:String):Boolean {
    val host=runCatching {URI(url).host?.lowercase()?.trimEnd('.')}.getOrNull() ?: return false
    fun belongs(domains:List<String>)=domains.any {host==it || host.endsWith(".$it")}
    if(belongs(listOf("youtube.com","youtu.be","youtube-nocookie.com")))return true
    return mode!="flac" && belongs(listOf("spotify.com","spotify.link","deezer.com","page.link","music.apple.com","itunes.apple.com"))
}
