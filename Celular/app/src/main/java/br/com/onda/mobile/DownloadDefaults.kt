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
        else {
            var mode=if(result.optString("mode")=="photos") "photos" else result.optString("simple_download_mode",result.optString("mode","mp3"))
            if(catalog && mode in listOf("photos","social","video","mp4","original")) mode=if(mode=="original") "m4a" else "mp3"
            result.put("mode",mode).put("audio_quality",when(mode) {"mp3"->"320 kbps";"m4a"->"256 kbps";else->JSONObject.NULL})
        }
        if(social || result.optString("mode")=="photos") result.put("image_options",JSONObject().put("format","Original").put("width",0).put("height",0).put("keep_ratio",true))
    }
    return result
}
