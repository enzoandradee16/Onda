package br.com.onda.mobile

import org.json.JSONObject

/** Duplicate tracks remain legal, while unrelated edits retain each card's state. */
internal fun occurrenceKeys(identities:List<String>):List<String> {
    val seen=mutableMapOf<String,Int>()
    return identities.map {identity->
        val occurrence=seen.getOrDefault(identity,0)
        seen[identity]=occurrence+1
        "${identity.length}:$identity:$occurrence"
    }
}

internal fun stableTrackKeys(rows:List<JSONObject>):List<String> = occurrenceKeys(rows.map {row->
    row.optString("_queue_id").ifBlank {row.optString("source_url")}.ifBlank {
        listOf(row.optString("id"),row.optString("title"),row.opt("artists")?.toString().orEmpty(),row.optString("album")).joinToString("\u001f")
    }
})
