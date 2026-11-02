package br.com.onda.mobile

import android.content.Context
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.SeekParameters
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import kotlinx.coroutines.*
import org.json.JSONObject

/** Memory-only native streaming: no download manager or disk cache is installed. */
@androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
internal class AndroidStreamPlayback(
    context:Context,
    private val scope:CoroutineScope,
    model:JSONObject,
    seconds:Double,
    private val onClock:(Double,Boolean)->Unit,
    private val onEnded:()->Unit,
    private val refresh:suspend ()->JSONObject,
    private val onFailure:(Exception)->Unit,
) {
    private val player=ExoPlayer.Builder(context)
        .setLoadControl(DefaultLoadControl.Builder().setBufferDurationsMs(12000,30000,1500,3000).setBackBuffer(10000,true).setPrioritizeTimeOverSizeThresholds(true).build())
        .build().apply {setSeekParameters(SeekParameters.EXACT);trackSelectionParameters=trackSelectionParameters.buildUpon().setTrackTypeDisabled(C.TRACK_TYPE_VIDEO,true).build()}
    private var closed=false
    private var retried=false
    private var recovery:Job?=null
    private val clock:Job
    init {
        player.addListener(object:Player.Listener {
            override fun onEvents(player:Player,events:Player.Events) {publish()}
            override fun onPlaybackStateChanged(state:Int) {if(!closed && state==Player.STATE_ENDED)onEnded()}
            override fun onPlayerError(error:PlaybackException) {
                if(closed || recovery?.isActive==true)return
                if(retried){onFailure(error);return}
                retried=true
                val position=player.currentPosition.coerceAtLeast(0)/1000.0
                val playing=player.playWhenReady
                recovery=scope.launch {
                    try {val fresh=refresh();if(!closed)open(fresh,position,playing)}
                    catch(cancelled:CancellationException){throw cancelled}
                    catch(failure:Exception){if(!closed)onFailure(failure)}
                }
            }
        })
        open(model,seconds,true)
        clock=scope.launch {while(isActive && !closed){publish();delay(80)}}
    }
    private fun publish() {if(!closed)onClock(player.currentPosition.coerceAtLeast(0)/1000.0,player.isPlaying)}
    private fun open(model:JSONObject,seconds:Double,playing:Boolean) {
        val stream=model.getJSONObject("_stream")
        val headers=stream.optJSONObject("headers")
        val properties=buildMap<String,String> {headers?.keys()?.forEach {key->val value=headers.optString(key);if(!key.contains('\r')&&!key.contains('\n')&&!value.contains('\r')&&!value.contains('\n'))put(key,value)}}
        val http=DefaultHttpDataSource.Factory().setDefaultRequestProperties(properties).setAllowCrossProtocolRedirects(true).setConnectTimeoutMs(15000).setReadTimeoutMs(15000)
        val source=DefaultMediaSourceFactory(http)
        val url=stream.getString("url")
        val item=MediaItem.Builder().setUri(url).apply {
            if(stream.optString("protocol").startsWith("m3u8") || url.contains("/hls_playlist/") || url.substringBefore('?').endsWith(".m3u8"))setMimeType(MimeTypes.APPLICATION_M3U8)
        }.build()
        player.setMediaSource(source.createMediaSource(item),(seconds.coerceAtLeast(0.0)*1000).toLong())
        player.playWhenReady=playing;player.prepare()
    }
    fun pause(){player.pause();publish()}
    fun resume(){player.play()}
    fun seek(seconds:Double){player.seekTo((seconds.coerceAtLeast(0.0)*1000).toLong());publish()}
    fun volume(value:Float){player.volume=value.coerceIn(0f,1f)}
    fun close(){if(closed)return;closed=true;clock.cancel();recovery?.cancel();player.release()}
}
