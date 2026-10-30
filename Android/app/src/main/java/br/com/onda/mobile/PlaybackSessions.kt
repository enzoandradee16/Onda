package br.com.onda.mobile

import android.content.Context
import org.json.JSONObject

/** Kept separately from preferences: forgetting appearance must not discard queues. */
internal object PlaybackSessions {
    private val writes=PlaybackSessionWrites(java.util.concurrent.Executors.newSingleThreadExecutor {task->
        Thread(task,"ONDA-session-save").apply {isDaemon=true}
    }) {android.util.Log.w("ONDA","Could not persist playback session",it)}
    private fun identity(context:Context,key:String)=context.filesDir.absolutePath+":"+key
    fun load(context:Context,key:String):JSONObject? = runCatching {
        (writes.latest(identity(context,key)) ?: context.getSharedPreferences("playback-sessions",Context.MODE_PRIVATE).getString(key,null))?.let {JSONObject(it)}
    }.getOrNull()
    fun save(context:Context,key:String,data:JSONObject,synchronous:Boolean=false) {
        val application=context.applicationContext
        val raw=checkNotNull(data.toString()) {"Sessão de reprodução inválida."}
        writes.save(identity(application,key),raw,synchronous) {snapshot->
            // commit runs on our writer, outside Android's lifecycle-blocking apply queue.
            val preferences=application.getSharedPreferences("playback-sessions",Context.MODE_PRIVATE)
            check(preferences.edit().putString(key,snapshot).commit()){"Não foi possível salvar a sessão antes de reiniciar."}
        }
    }
}
