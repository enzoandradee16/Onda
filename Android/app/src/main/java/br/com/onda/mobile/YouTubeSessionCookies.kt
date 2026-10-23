package br.com.onda.mobile

internal fun youtubeCookieEntries(headers:List<String>):LinkedHashMap<String,String> {
    val entries=linkedMapOf<String,String>()
    headers.forEach {header->header.split(';').forEach {pair->
        val parts=pair.trim().split('=',limit=2)
        if(parts.size==2 && Regex("[A-Za-z0-9_!#$%&'*+.^`|~-]+").matches(parts[0]) && parts[1].none {it=='\r' || it=='\n' || it=='\t'})entries.putIfAbsent(parts[0],parts[1])
    }}
    return entries
}
internal fun hasYouTubeLogin(entries:Map<String,String>):Boolean = listOf("SID","SAPISID","__Secure-1PAPISID","__Secure-3PAPISID").any {!entries[it].isNullOrBlank()}
internal fun youtubeCookieFile(entries:Map<String,String>):String = "# Netscape HTTP Cookie File\n"+entries.entries.joinToString("\n") {
    val hostOnly=it.key.startsWith("__Host-")
    "${if(hostOnly)"www.youtube.com\tFALSE" else ".youtube.com\tTRUE"}\t/\tTRUE\t0\t${it.key}\t${it.value}"
}+"\n"

internal fun isYouTubeCookieFile(file:java.io.File):Boolean {
    if(!file.isFile || file.length()>2*1024*1024)return false
    return runCatching {
        val lines=file.readLines()
        lines.firstOrNull()?.removePrefix("\uFEFF") in setOf("# Netscape HTTP Cookie File","# HTTP Cookie File") && lines.any {line->
            val fields=line.removePrefix("#HttpOnly_").split('\t')
            val host=fields.firstOrNull().orEmpty().removePrefix(".").lowercase()
            fields.size==7 && (host=="youtube.com" || host.endsWith(".youtube.com"))
        }
    }.getOrDefault(false)
}
