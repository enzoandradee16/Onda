package br.com.onda.mobile

import java.net.URI
import java.net.URLDecoder
import java.net.URLEncoder
import org.json.JSONObject

internal fun sourceKey(value:String):String {
    val text=value.trim()
    if(Regex("spotify:(track|album|playlist):[A-Za-z0-9]+").matches(text))return text
    return runCatching {
        val uri=URI(text)
        val host=(uri.host ?: "").lowercase().removePrefix("www.").removePrefix("m.")
        val path=(uri.rawPath ?: "").trimEnd('/')
        val query=(uri.rawQuery ?: "").split('&').filter {it.isNotEmpty()}.map {
            val pair=it.split('=',limit=2)
            URLDecoder.decode(pair[0],"UTF-8") to URLDecoder.decode(pair.getOrElse(1){""},"UTF-8")
        }
        if(host=="open.spotify.com") {
            Regex("(?:/intl-[^/]+)?/(track|album|playlist)/([A-Za-z0-9]+)").matchEntire(path)?.let {return "spotify:${it.groupValues[1]}:${it.groupValues[2]}"}
        }
        if(host in setOf("youtu.be","youtube.com","music.youtube.com")) {
            var video=if(host=="youtu.be")path.trimStart('/') else query.firstOrNull {it.first=="v"}?.second.orEmpty()
            if(video.isEmpty() && listOf("/shorts/","/embed/","/live/").any {path.startsWith(it)})video=path.split('/').getOrElse(2){""}
            if(video.isNotEmpty())return "youtube:video:$video"
            query.firstOrNull {it.first=="list"}?.second?.let {return "youtube:playlist:$it"}
        }
        if(host=="deezer.com") {
            Regex("(?:/[a-z]{2})?/(track|album|playlist)/(\\d+)").matchEntire(path)?.let {return "deezer:${it.groupValues[1]}:${it.groupValues[2]}"}
        }
        if(uri.scheme !in setOf("http","https") || host.isEmpty())return text
        val filtered=query.filterNot {it.first.lowercase() in setOf("si","fbclid","gclid","igsh","igshid") || it.first.lowercase().startsWith("utm_")}
            .sortedWith(compareBy({it.first},{it.second})).joinToString("&") {URLEncoder.encode(it.first,"UTF-8")+"="+URLEncoder.encode(it.second,"UTF-8")}
        uri.scheme+"://"+uri.rawAuthority+(uri.rawPath ?: "")+(if(filtered.isNotEmpty()) "?$filtered" else "")
    }.getOrDefault(text)
}

internal fun jobSource(config:JSONObject):String {
    if(config.optBoolean("playlist"))runCatching {
        val uri=URI(config.optString("url"))
        val host=uri.host.orEmpty().lowercase().removePrefix("www.").removePrefix("m.")
        if(host !in setOf("youtu.be","youtube.com","music.youtube.com"))return sourceKey(config.optString("selected_catalog_url").ifBlank {config.optString("url")})
        val query=uri.rawQuery.orEmpty().split('&')
        query.firstOrNull {it.startsWith("list=")}?.substringAfter('=')?.let {return "youtube:playlist:"+URLDecoder.decode(it,"UTF-8")}
    }
    return sourceKey(config.optString("selected_catalog_url").ifBlank {config.optString("url")})
}

internal fun duplicateJob(first:JSONObject,second:JSONObject):Boolean =
    first.optString("_operation").isBlank() && second.optString("_operation").isBlank() &&
    jobSource(first).isNotBlank() && jobSource(first)==jobSource(second) &&
    first.optString("mode").equals(second.optString("mode"),true) && first.optBoolean("playlist")==second.optBoolean("playlist") && first.optString("playlist_title")==second.optString("playlist_title") &&
    listOf("audio_quality","height","fps").all {key->first.cleanString(key)==second.cleanString(key)} &&
    listOf("format","width","height","keep_ratio").all {key->first.optJSONObject("image_options")?.cleanString(key)==second.optJSONObject("image_options")?.cleanString(key)}

/** Compute once per insertion instead of reparsing every queued URL for each track. */
internal data class QueueDuplicateKey(val source:String,val mode:String,val playlist:Boolean,val group:String,val options:List<String?>)
internal fun queueDuplicateKey(config:JSONObject):QueueDuplicateKey? {
    if(config.optString("_operation").isNotBlank())return null
    val source=jobSource(config);if(source.isBlank())return null
    return QueueDuplicateKey(source,config.optString("mode").lowercase(),config.optBoolean("playlist"),config.optString("playlist_title"),
        listOf("audio_quality","height","fps").map {config.cleanString(it)} + listOf("format","width","height","keep_ratio").map {config.optJSONObject("image_options")?.cleanString(it)})
}
