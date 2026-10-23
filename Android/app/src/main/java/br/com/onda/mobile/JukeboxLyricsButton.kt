package br.com.onda.mobile

import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable internal fun JukeboxLyricsButton(vm:OndaViewModel) {
    val controller=vm.jukebox
    val state by controller.state.collectAsStateWithLifecycle()
    val queue by controller.playbackQueue.collectAsStateWithLifecycle()
    val current by controller.currentQueueId.collectAsStateWithLifecycle()
    LyricsButton(vm,state.model?.optString("source").orEmpty(),{
        val currentState=controller.state.value
        val beats=currentState.model?.optJSONArray("beats")
        val a=beats?.optDouble(currentState.index,0.0) ?: 0.0
        val b=beats?.optDouble(currentState.index+1,a) ?: a
        a+(b-a)*currentState.phase
    },state.model?.optDouble("duration",0.0) ?: 0.0,{seconds->
        val beats=controller.state.value.model?.optJSONArray("beats")
        if(beats!=null)controller.seek((0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=seconds} ?: 0)
    },controller::playPause,isPlaying={controller.state.value.playing&&!controller.state.value.paused},previous=controller::previousTrack,
        next=if(controller.nextQueueIndex<queue.size)controller::nextTrack else null)
}
