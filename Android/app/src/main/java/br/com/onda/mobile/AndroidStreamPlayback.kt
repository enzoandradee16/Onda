package br.com.onda.mobile

import android.content.Context
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.SeekParameters
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import kotlinx.coroutines.*
import org.json.JSONObject

/** Starts from a small buffer, then fills a bounded app-private cache in the background. */
@androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
internal class AndroidStreamPlayback(
    private val context:Context,
    private val scope:CoroutineScope,
    model:JSONObject,
    seconds:Double,
    private val onClock:(Double,Boolean,Double,Double)->Unit,
    private val onEnded:()->Unit,
    private val refresh:suspend ()->JSONObject,
    private val onFailure:(Exception)->Unit,
    private val prefetchAllowed:()->Boolean={true},
) {
    private val player=ExoPlayer.Builder(context)
        .setWakeMode(C.WAKE_MODE_NETWORK)
        .setAudioAttributes(androidx.media3.common.AudioAttributes.Builder().setUsage(C.USAGE_MEDIA).setContentType(C.AUDIO_CONTENT_TYPE_MUSIC).build(),false)
        .setLoadControl(DefaultLoadControl.Builder().setBufferDurationsMs(12000,30000,1500,3000).setBackBuffer(10000,true).setPrioritizeTimeOverSizeThresholds(true).build())
        .build().apply {setSeekParameters(SeekParameters.EXACT);trackSelectionParameters=trackSelectionParameters.buildUpon().setTrackTypeDisabled(C.TRACK_TYPE_VIDEO,true).build()}
    private var closed=false
    private var retried=false
    private var recovery:Job?=null
    private var prefetch:Job?=null
    private var streamModel=model
    private var localFile=""
    private var rejectedLocalFile=""
    @Volatile private var complete=false
    private var origin=seconds
    private var duration=model.optDouble("duration",0.0)
    private val clock:Job
    init {
        player.addListener(object:Player.Listener {
            override fun onEvents(player:Player,events:Player.Events) {publish()}
            override fun onPlaybackStateChanged(state:Int) {if(!closed && state==Player.STATE_ENDED)onEnded()}
            override fun onPlayerError(error:PlaybackException) {
                if(closed || recovery?.isActive==true)return
                val position=player.currentPosition.coerceAtLeast(0)/1000.0
                val playing=player.playWhenReady
                if(localFile.isNotBlank() && localFile!=rejectedLocalFile) {
                    val invalid=localFile
                    rejectedLocalFile=invalid;StreamAudioCache.release(invalid);localFile=""
                    if(invalid !in StreamAudioCache.protectedPaths())runCatching {java.io.File(invalid).delete()}
                    val fallback=JSONObject(streamModel.toString()).apply {remove("_stream_file")}
                    try {open(fallback,position,playing)} catch(failure:Exception){onFailure(failure)}
                    return
                }
                if(retried){onFailure(error);return}
                retried=true
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
    private fun publish() {
        if(closed)return
        val position=player.currentPosition.coerceAtLeast(0)/1000.0
        val start=if(complete)0.0 else maxOf(origin,position-10)
        val end=if(complete)duration else player.bufferedPosition.coerceAtLeast(0)/1000.0
        onClock(position,player.isPlaying,start,end.coerceAtMost(duration))
        if(!prefetchAllowed() && !complete && prefetch!=null){prefetch?.cancel();prefetch=null}
        if(player.isPlaying && prefetch==null && localFile.isBlank() && prefetchAllowed())prefetch()
    }
    private fun prefetch() {
        val model=JSONObject(streamModel.toString())
        prefetch=scope.launch {
            delay(200)
            for(attempt in 0..2) {
                try {
                    StreamAudioCache.prefetch(context,model)
                    if(!closed){
                        val cached=model.optString("_stream_file")
                        check(cached.isBlank() || cached!=rejectedLocalFile){"Discarded cached audio"}
                        if(cached.isNotBlank() && cached!=localFile)useCachedFile(cached,player.currentPosition,player.playWhenReady)
                        complete=true;publish()
                    }
                    break
                } catch(cancelled:CancellationException){throw cancelled}
                catch(error:Exception) {
                    if(attempt==2)android.util.Log.w("ONDA-stream-cache","Prefetch failed: ${error.javaClass.simpleName}")
                    else delay(1000L*(attempt+1))
                }
            }
        }
    }
    private fun useCachedFile(path:String,position:Long,playing:Boolean) {
        val file=java.io.File(path).canonicalFile
        require(file.isFile && (file.toPath().startsWith(context.filesDir.canonicalFile.toPath()) || file.toPath().startsWith(context.cacheDir.canonicalFile.toPath())))
        if(localFile!=path){if(localFile.isNotBlank())StreamAudioCache.release(localFile);StreamAudioCache.protect(path);localFile=path}
        val media=MediaItem.Builder().setUri(android.net.Uri.fromFile(file)).setMimeType(MimeTypes.AUDIO_MATROSKA).build()
        player.setMediaSource(DefaultMediaSourceFactory(context).createMediaSource(media),position.coerceAtLeast(0))
        player.playWhenReady=playing;player.prepare();complete=true
    }
    private fun open(model:JSONObject,seconds:Double,playing:Boolean) {
        prefetch?.cancel();prefetch=null;complete=false;streamModel=model
        origin=seconds;duration=model.optDouble("duration",duration)
        val cached=model.optString("_stream_file")
        if(cached.isNotBlank() && cached!=rejectedLocalFile && java.io.File(cached).isFile){useCachedFile(cached,(seconds*1000).toLong(),playing);return}
        if(localFile.isNotBlank()){StreamAudioCache.release(localFile);localFile=""}
        val stream=model.getJSONObject("_stream")
        val http=StreamAudioCache.http(stream)
        val source=DefaultMediaSourceFactory(StreamAudioCache.factory(context,http).setCacheWriteDataSinkFactory(null))
        val url=stream.getString("url")
        val hls=stream.optString("protocol").startsWith("m3u8") || url.contains("/hls_playlist/") || url.substringBefore('?').endsWith(".m3u8")
        val media=MediaItem.Builder().setUri(url).apply {if(hls)setMimeType(MimeTypes.APPLICATION_M3U8)}.build()
        player.setMediaSource(source.createMediaSource(media),(seconds.coerceAtLeast(0.0)*1000).toLong())
        player.playWhenReady=playing;player.prepare()
    }
    fun pause(){player.pause();publish()}
    fun resume(){player.play()}
    fun seek(seconds:Double){origin=seconds;player.seekTo((seconds.coerceAtLeast(0.0)*1000).toLong());publish()}
    fun volume(value:Float){player.volume=value.coerceIn(0f,1f)}
    fun close(){if(closed)return;closed=true;clock.cancel();recovery?.cancel();prefetch?.cancel();player.release();if(localFile.isNotBlank())StreamAudioCache.release(localFile)}
}
