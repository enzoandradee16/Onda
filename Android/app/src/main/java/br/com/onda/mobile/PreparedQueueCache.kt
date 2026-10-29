package br.com.onda.mobile

import java.io.File
import org.json.JSONObject

internal fun preparationAhead(settings:JSONObject):Int=settings.opt("playback_prepare_ahead")?.toString()?.takeIf {it in listOf("1","2","3","5")}?.toInt() ?: 2

/** Persist cache references, never a running job or a second copy of the beat graph. */
internal fun preparedQueueReference(model:JSONObject)=JSONObject().apply {
    listOf("cache","source","title","media_title","media_artist","album","cover_url").forEach {key->if(model.has(key))put(key,model.get(key))}
}
internal fun restoreQueueModel(row:JSONObject):JSONObject?=runCatching {
    val reference=row.optJSONObject("_prepared_cache") ?: return null
    val base=File(reference.getString("cache"))
    if(!File(base,"audio.wav").isFile)return null
    val model=JSONObject(File(base,"analysis.json").readText())
    if((model.optJSONArray("beats")?.length() ?: 0)<2 || model.optJSONArray("neighbors")==null)return null
    reference.keys().forEach {model.put(it,reference.get(it))}
    model.put("media_cover",row.optString("_cover")).put("cached",true)
}.getOrNull()
