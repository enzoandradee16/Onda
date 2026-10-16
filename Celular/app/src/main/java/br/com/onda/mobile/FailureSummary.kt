package br.com.onda.mobile

import org.json.JSONObject

internal val failureAudioModes=setOf("original","mp3","m4a","flac","wav","opus","ogg","aac")

internal fun repairedFailureConfig(original:JSONObject,record:JSONObject):JSONObject? {
    if(original.optString("mode") !in failureAudioModes || original.optBoolean("playlist"))return null
    val url=record.optString("source_url")
    // Search offers public Deezer and Apple tracks; never turn an arbitrary link into a retry.
    if(!validFailureCatalogUrl(url))return null
    return JSONObject(original.toString()).apply {
        if(!has("failure_original_url"))put("failure_original_url",optString("url"))
        put("url",url);put("queue_info",JSONObject(record.toString()))
        listOf("catalog_record","selected_catalog_url","selected_version","youtube_match").forEach {remove(it)}
    }
}

internal fun failureReportText(rows:List<DownloadItem>,translate:(String)->String):String = buildString {
    append(translate("Falhas da fila"));append("\n\n")
    rows.forEachIndexed {index,item->
        append(index+1);append(". ");append(item.title);append('\n')
        append(item.config.optString("failure_original_url").ifBlank {item.config.optString("url")});append('\n')
        append(translate("Motivo"));append(": ")
        append(translate(item.message.ifBlank {"Motivo não informado"}));append("\n\n")
    }
}

internal fun validFailureCatalogUrl(url:String):Boolean = Regex("https://(?:www\\.)?deezer\\.com/track/[0-9]+|https://music\\.apple\\.com/[a-z]{2}/song/[0-9]+").matches(url)

internal fun finishedFailureIds(attempted:Set<String>,rows:List<Pair<String,String>>,finished:Boolean):List<String> =
    if(finished)rows.filter {it.first in attempted && it.second=="Erro"}.map {it.first} else emptyList()
