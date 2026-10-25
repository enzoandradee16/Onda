package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.util.Locale

internal data class PlatformIdentity(val key:String="",val label:String="")
private val platformDefinitions by lazy {
    val rows=JSONArray(OndaStore.context.assets.open("platforms.json").bufferedReader().use {it.readText()})
    (0 until rows.length()).map {rows.getJSONObject(it)}
}
internal fun identifyPlatform(source:String="",name:String=""):PlatformIdentity {
    val alias=name.trim().lowercase(Locale.ROOT)
    for(row in platformDefinitions) {
        val aliases=row.getJSONArray("aliases").let {a->(0 until a.length()).map {a.getString(it)}}+listOf(row.getString("key"),row.getString("label"))
        if(alias.isNotBlank() && aliases.any {it.lowercase(Locale.ROOT)==alias})return PlatformIdentity(row.getString("key"),row.getString("label"))
    }
    val value=source.trim()
    Regex("^(spotify|deezer|youtube):(?:track|album|playlist|video):",RegexOption.IGNORE_CASE).find(value)?.let {return identifyPlatform(name=it.groupValues[1])}
    val host=runCatching {URI(value).let {if(it.scheme?.lowercase(Locale.ROOT) in listOf("http","https") && it.userInfo==null)it.host?.lowercase(Locale.ROOT)?.trimEnd('.') else null}}.getOrNull().orEmpty()
    if(host.isBlank())return PlatformIdentity()
    for(row in platformDefinitions) {
        val domains=row.getJSONArray("domains")
        if((0 until domains.length()).any {host==domains.getString(it) || host.endsWith("."+domains.getString(it))})return PlatformIdentity(row.getString("key"),row.getString("label"))
    }
    return PlatformIdentity("link",host.removePrefix("www."))
}
