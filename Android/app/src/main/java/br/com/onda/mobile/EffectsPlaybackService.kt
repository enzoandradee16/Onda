package br.com.onda.mobile

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadata
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.*
import android.util.Base64
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow

internal data class EffectsMediaState(
    val source:String="",val title:String="Efeitos",val artist:String="",val album:String="",
    val duration:Double=0.0,val position:Long=0,val playing:Boolean=false,val preparing:Boolean=false,
    val speed:Float=1f,val hasPrevious:Boolean=false,val hasNext:Boolean=false,val cover:String="",
)

/** This session controls only Effects; Jukebox keeps its own source, queue and MediaSession. */
internal object EffectsPlaybackRuntime {
    var owner:OndaViewModel?=null
        private set
    val state=MutableStateFlow<EffectsMediaState?>(null)
    fun publish(model:OndaViewModel,value:EffectsMediaState){owner=model;state.value=value}
    fun clear(model:OndaViewModel){if(owner===model){state.value=null;owner=null}}
}

class EffectsPlaybackService:Service() {
    companion object {
        fun start(context:android.content.Context){ContextCompat.startForegroundService(context,Intent(context,EffectsPlaybackService::class.java))}
    }
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
    private lateinit var session:MediaSession
    private lateinit var wake:PowerManager.WakeLock
    private var selfStopped=false
    private var artworkKey=""
    private var artwork:Bitmap?=null
    override fun onBind(intent:Intent?)=null
    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("effects-playback",translateUi("Efeitos"),NotificationManager.IMPORTANCE_LOW))
        wake=getSystemService(PowerManager::class.java).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ONDA:Effects").apply {setReferenceCounted(false)}
        session=MediaSession(this,"ONDA Effects")
        session.setCallback(object:MediaSession.Callback() {
            override fun onPlay(){val state=EffectsPlaybackRuntime.state.value;if(state!=null&&!state.playing&&!state.preparing)EffectsPlaybackRuntime.owner?.mediaToggleEffects()}
            override fun onPause(){EffectsPlaybackRuntime.owner?.mediaPauseEffects()}
            override fun onStop(){EffectsPlaybackRuntime.owner?.stopEffectsPlayback()}
            override fun onSeekTo(pos:Long){EffectsPlaybackRuntime.owner?.mediaSeekEffects(pos/1000.0)}
            override fun onSkipToPrevious(){EffectsPlaybackRuntime.owner?.mediaPreviousEffects()}
            override fun onSkipToNext(){EffectsPlaybackRuntime.owner?.mediaNextEffects()}
        },Handler(Looper.getMainLooper()))
        val notification=notification(EffectsPlaybackRuntime.state.value ?: EffectsMediaState())
        if(Build.VERSION.SDK_INT>=29)startForeground(14,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK) else startForeground(14,notification)
        scope.launch {
            EffectsPlaybackRuntime.state.collect {state->
                if(state==null){selfStopped=true;stopSelf();return@collect}
                if(state.playing){if(!wake.isHeld)wake.acquire()}else if(wake.isHeld)wake.release()
                if(state.cover!=artworkKey){artworkKey=state.cover;artwork=withContext(Dispatchers.IO){runCatching {val bytes=Base64.decode(state.cover,Base64.DEFAULT);BitmapFactory.decodeByteArray(bytes,0,bytes.size)}.getOrNull()}}
                session.isActive=true
                val actions=PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_STOP or PlaybackState.ACTION_SEEK_TO or PlaybackState.ACTION_SKIP_TO_PREVIOUS or if(state.hasNext)PlaybackState.ACTION_SKIP_TO_NEXT else 0L
                session.setPlaybackState(PlaybackState.Builder().setActions(actions).setState(when {state.preparing->PlaybackState.STATE_BUFFERING;state.playing->PlaybackState.STATE_PLAYING;else->PlaybackState.STATE_PAUSED},state.position*1000,if(state.playing)state.speed else 0f).build())
                session.setMetadata(MediaMetadata.Builder().putString(MediaMetadata.METADATA_KEY_TITLE,state.title).putString(MediaMetadata.METADATA_KEY_ARTIST,state.artist).putString(MediaMetadata.METADATA_KEY_ALBUM,state.album).putLong(MediaMetadata.METADATA_KEY_DURATION,(state.duration*1000).toLong()).putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART,artwork).build())
                getSystemService(NotificationManager::class.java).notify(14,notification(state))
            }
        }
    }
    private fun action(name:String,code:Int)=PendingIntent.getService(this,code,Intent(this,EffectsPlaybackService::class.java).setAction(name),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    private fun notification(state:EffectsMediaState):Notification {
        val open=PendingIntent.getActivity(this,210,Intent(this,MainActivity::class.java).putExtra("open_effects",true).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val active=state.playing||state.preparing
        val builder=Notification.Builder(this,"effects-playback").setSmallIcon(R.drawable.ic_onda_notification).setContentTitle(state.title).setContentText(state.artist).setSubText(translateUi("Efeitos")).setLargeIcon(artwork).setContentIntent(open).setDeleteIntent(action("stop",214)).setOnlyAlertOnce(true).setOngoing(active).setVisibility(Notification.VISIBILITY_PUBLIC)
            .addAction(Notification.Action.Builder(android.R.drawable.ic_media_previous,translateUi("Retroceder"),action("previous",211)).build())
            .addAction(Notification.Action.Builder(if(active)android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play,translateUi(if(active)"Pausar" else "Reproduzir"),action(if(active)"pause" else "play",212)).build())
        if(state.hasNext)builder.addAction(Notification.Action.Builder(android.R.drawable.ic_media_next,translateUi("Avançar"),action("next",213)).build())
        builder.addAction(Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,translateUi("Parar"),action("stop",214)).build())
        return builder.setStyle(Notification.MediaStyle().setMediaSession(session.sessionToken).setShowActionsInCompactView(*if(state.hasNext)intArrayOf(0,1,2) else intArrayOf(0,1))).build()
    }
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        val owner=EffectsPlaybackRuntime.owner
        when(intent?.action){"play"->if(EffectsPlaybackRuntime.state.value?.playing!=true)owner?.mediaToggleEffects();"pause"->owner?.mediaPauseEffects();"previous"->owner?.mediaPreviousEffects();"next"->owner?.mediaNextEffects();"stop"->owner?.stopEffectsPlayback()}
        return START_NOT_STICKY
    }
    override fun onTaskRemoved(rootIntent:Intent?){EffectsPlaybackRuntime.owner?.stopEffectsPlayback();stopSelf()}
    override fun onDestroy(){
        if(!selfStopped)EffectsPlaybackRuntime.owner?.stopEffectsPlayback()
        scope.cancel();if(wake.isHeld)wake.release();session.isActive=false;session.release()
        stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy()
        if(selfStopped&&EffectsPlaybackRuntime.state.value!=null)start(this)
    }
}
