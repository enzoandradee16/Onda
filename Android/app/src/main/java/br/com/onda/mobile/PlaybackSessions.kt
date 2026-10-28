package br.com.onda.mobile

import android.content.Context
import org.json.JSONObject

/** Kept separately from preferences: forgetting appearance must not discard queues. */
internal object PlaybackSessions {
    fun load(context:Context,key:String):JSONObject? = runCatching {
        context.getSharedPreferences("playback-sessions",Context.MODE_PRIVATE).getString(key,null)?.let {JSONObject(it)}
    }.getOrNull()
    fun save(context:Context,key:String,data:JSONObject,synchronous:Boolean=false) {
        val preferences=context.getSharedPreferences("playback-sessions",Context.MODE_PRIVATE)
        val raw=data.toString()
        if(preferences.getString(key,null)!=raw || synchronous) {
            val editor=preferences.edit().putString(key,raw)
            if(synchronous)check(editor.commit()){"Não foi possível salvar a sessão antes de reiniciar."} else editor.apply()
        }
    }
}
