package br.com.onda.mobile

import android.content.Context
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors

/** Callers hand off owned snapshots. Encoding and disk commits share an ordered writer. */
internal object PlaybackSessions {
    private val executor=Executors.newSingleThreadExecutor {task->Thread(task,"ONDA-session-save").apply {isDaemon=true}}
    private class Snapshot(val data:JSONObject)
    private val pending=ConcurrentHashMap<String,Snapshot>()
    private val lock=Any()
    private val persisted=ConcurrentHashMap<String,String>()
    private val queueEncodings=mutableMapOf<String,Pair<org.json.JSONArray,String>>()
    private fun identity(context:Context,key:String)=context.filesDir.absolutePath+":"+key
    fun load(context:Context,key:String):JSONObject?=runCatching {
        pending[identity(context,key)]?.data?.let {JSONObject(it.toString())}
            ?: context.getSharedPreferences("playback-sessions",Context.MODE_PRIVATE).getString(key,null)?.let {JSONObject(it)}
    }.getOrNull()
    private fun encode(id:String,data:JSONObject):String {
        val rows=data.optJSONArray("queue") ?: return checkNotNull(data.toString()) {"Sessão de reprodução inválida."}
        val cached=queueEncodings[id]
        val queueJson=if(cached?.first===rows)cached.second else checkNotNull(rows.toString()).also {queueEncodings[id]=rows to it}
        val header=JSONObject()
        data.keys().forEach {key->if(key!="queue")header.put(key,data.get(key))}
        return header.toString().dropLast(1)+(if(header.length()>0)"," else "")+"\"queue\":"+queueJson+"}"
    }
    fun save(context:Context,key:String,data:JSONObject,synchronous:Boolean=false) {
        val application=context.applicationContext
        val id=identity(application,key)
        val snapshot=Snapshot(data)
        pending[id]=snapshot
        val write={
            synchronized(lock) {
                if(pending[id]===snapshot) {
                    val raw=encode(id,snapshot.data)
                    val preferences=application.getSharedPreferences("playback-sessions",Context.MODE_PRIVATE)
                    if(synchronous || persisted[id]!=raw) {
                    check(preferences.edit().putString(key,raw).commit()) {"Não foi possível salvar a sessão antes de reiniciar."}
                    persisted[id]=raw
                    }
                    pending.remove(id,snapshot)
                }
            }
        }
        if(synchronous)write() else executor.execute {
            try {write()} catch(error:Exception){android.util.Log.w("ONDA","Could not persist playback session",error)}
        }
    }
}
