package br.com.onda.mobile

import org.json.JSONObject

// Index once instead of scanning every returned match for every playlist track.
fun mergeTrackMatches(tracks: List<JSONObject>, matches: List<JSONObject>): List<JSONObject> {
    val byUrl=matches.groupBy {it.optString("source_url")}.mapValues {it.value.first()}
    return tracks.map {byUrl[it.optString("source_url")] ?: it}
}
