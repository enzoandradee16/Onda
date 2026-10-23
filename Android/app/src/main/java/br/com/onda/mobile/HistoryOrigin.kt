package br.com.onda.mobile

internal fun historyOrigin(value:String):String {
    val source=value.trim()
    Regex("(spotify|deezer):(track|album|playlist):([A-Za-z0-9_-]+)").matchEntire(source)?.let {
        val (platform,kind,id)=it.destructured
        return (if(platform=="spotify") "https://open.spotify.com/" else "https://www.deezer.com/")+kind+"/"+id
    }
    Regex("youtube:(video|playlist):([A-Za-z0-9_-]+)").matchEntire(source)?.let {
        return "https://www.youtube.com/"+(if(it.groupValues[1]=="video") "watch?v=" else "playlist?list=")+it.groupValues[2]
    }
    return runCatching {java.net.URI(source).let {if(it.scheme in listOf("http","https") && !it.host.isNullOrBlank() && it.userInfo==null)source else ""}}.getOrDefault("")
}
