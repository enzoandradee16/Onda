package br.com.onda.mobile

import org.json.JSONObject

/** Queue lists and their identities are replaced, not edited in place. */
internal class PlaybackQueueIndex {
    private data class Snapshot(val rows:List<JSONObject>,val identity:String,val index:Int)
    @Volatile private var cached:Snapshot?=null
    fun index(rows:List<JSONObject>,identity:String):Int {
        val previous=cached
        if(previous!=null && previous.rows===rows && previous.identity==identity)return previous.index
        return rows.indexOfFirst {it.optString("_queue_id")==identity}.also {cached=Snapshot(rows,identity,it)}
    }
    fun clear(){cached=null}
}
