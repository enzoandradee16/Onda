package br.com.onda.mobile

import org.json.JSONObject
import java.net.URI

internal fun effectiveDownloadOptions(value:JSONObject):JSONObject {
    val result=JSONObject(value.toString())
    if(result.optString("_operation").isNotBlank()) return result
    val url=result.optString("url")
    val host=runCatching {URI(url).host.orEmpty().lowercase().trimEnd('.')}.getOrDefault("")
    val social=result.optBoolean("social_best_quality",false) && listOf("instagram.com","tiktok.com","kwai.com","kwai-video.com","kw.ai","kuaishou.com").any {host==it || host.endsWith(".$it")}
    val simple=result.optBoolean("simple_download_ui",false)
    val catalog=url.startsWith("spotify:") || host in listOf("open.spotify.com","spotify.com","www.spotify.com","spotify.link","music.apple.com","itunes.apple.com","deezer.com","www.deezer.com","link.deezer.com","deezer.page.link")
    if(social || simple) {
        result.put("height",JSONObject.NULL).put("fps",JSONObject.NULL)
        if(social) result.put("mode","social").put("audio_quality",JSONObject.NULL).put("normalize_volume",false).put("review_metadata",false).put("playlist",false)
        else if(result.optString("mode")!="photos" || catalog) {
            result.put("mode",if(catalog) "mp3" else "video").put("audio_quality",if(catalog) "320 kbps" else JSONObject.NULL)
        }
        if(social || result.optString("mode")=="photos") result.put("image_options",JSONObject().put("format","Original").put("width",0).put("height",0).put("keep_ratio",true))
    }
    return result
}
