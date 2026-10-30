package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject

/** Adapt public PC metadata to the same records rendered by the local queue. */
internal fun RemoteQueueTrack.queueRecord(): JSONObject = JSONObject()
    .put("_queue_id", id).put("title", title).put("artists", JSONArray(listOf(artist)))
    .put("duration_ms", (duration * 1000).toLong()).put("cover_url", cover)
    .put("_recent_rank", recentRank)
    .put("_analysis", when (preparation) { "pending", "preparing" -> "Preparando"; "error" -> "Erro"; else -> "Pronto" })
