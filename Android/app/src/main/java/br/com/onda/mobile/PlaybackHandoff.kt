package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject
import java.net.URI

/** A portable catalog reference contains no private files or cached audio URLs. */
internal fun handoffRecord(record: JSONObject?): JSONObject? {
    record ?: return null
    if (record.optBoolean("_jukebox_direct")) return null
    if (record.has("_local_source") && !record.optBoolean("_catalog_source") && !catalogHandoffUrl(record.optString("source_url"))) return null
    val source=record.optString("source_url")
    if(source.isNotBlank() && !catalogHandoffUrl(source))return null
    val title = record.optString("title").trim()
    val artists = record.optJSONArray("artists") ?: return null
    if (title.isBlank() || title.length > 500 || artists.length() !in 1..20) return null
    val names = (0 until artists.length()).map { artists.opt(it) as? String ?: return null }
    if (names.any { it.isBlank() || it.length > 200 }) return null
    return JSONObject().put("title", title).put("artists", JSONArray(names)).apply {
        if(source.isNotBlank())put("source_url",source)
        val cover=record.optString("cover_url")
        val coverUri=runCatching {URI(cover)}.getOrNull()
        val host=coverUri?.host.orEmpty()
        if(cover.length<=2048 && coverUri?.scheme=="https" && coverUri.userInfo==null && coverUri.port==-1 && listOf("scdn.co","dzcdn.net","mzstatic.com").any {host==it || host.endsWith(".$it")})put("cover_url",cover)
        for (key in listOf("album", "isrc")) {
            val value = record.opt(key)
            if (value is String && value.length <= 500) put(key, value)
        }
        val duration = record.optDouble("duration_ms", 0.0)
        if (duration.isFinite() && duration in 0.0..86400000.0) put("duration_ms", duration)
    }
}

internal fun catalogHandoffUrl(value:String):Boolean {
    if(value.length>2048)return false
    val uri=runCatching {URI(value)}.getOrNull() ?: return false
    return uri.scheme=="https" && uri.userInfo==null && uri.port==-1 && uri.host in listOf(
        "open.spotify.com","deezer.com","www.deezer.com","music.apple.com","itunes.apple.com"
    )
}
