package br.com.onda.mobile

import android.app.*
import android.content.*
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.media.MediaMetadata
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.combine
import java.net.HttpURLConnection
import java.net.URL

/** Application-owned audio survives activity recreation; the service owns its media session. */
internal object JukeboxRuntime {
    private var controller:JukeboxController?=null
    @Synchronized fun get(context:Context):JukeboxController = controller ?: JukeboxController(context.applicationContext,CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate),{}).also {controller=it}
}

class JukeboxService:Service() {
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
    private lateinit var session:MediaSession
    private lateinit var controller:JukeboxController
    private lateinit var wake:PowerManager.WakeLock
    private var artwork:Bitmap?=null
    private var artworkKey:List<String>?=null
    private var artworkTask:Job?=null
    private var selfStopped=false
    override fun onBind(intent:Intent?)=null
    override fun onCreate() {
        super.onCreate();controller=JukeboxRuntime.get(this)
        val manager=getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("jukebox",translateUi("Reprodução"),NotificationManager.IMPORTANCE_LOW))
        wake=getSystemService(PowerManager::class.java).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ONDA:Jukebox").apply {setReferenceCounted(false)}
        session=MediaSession(this,"ONDA Jukebox")
        session.setCallback(object:MediaSession.Callback() {
            override fun onPlay(){if(!controller.state.value.playing || controller.state.value.paused)controller.playPause()}
            override fun onPause(){controller.pause()}
            override fun onStop(){controller.stop()}
            override fun onSkipToPrevious(){controller.previousTrack()}
            override fun onSkipToNext(){controller.nextTrack()}
        },Handler(Looper.getMainLooper()))
        val notification=notification()
        if(Build.VERSION.SDK_INT>=29)startForeground(13,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK) else startForeground(13,notification)
        scope.launch {
            combine(controller.state,controller.playbackQueue,controller.currentQueueId) {state,rows,id->
                val row=rows.firstOrNull {it.optString("_queue_id")==id}
                val model=state.model
                listOf(state.playing.toString(),state.paused.toString(),model?.optString("source").orEmpty(),
                    model?.optString("media_title").orEmpty(),model?.optString("media_artist").orEmpty(),
                    model?.optString("media_cover").orEmpty().ifBlank {model?.optString("_cover").orEmpty()}.ifBlank {row?.optString("_cover").orEmpty()},
                    model?.optString("cover_url").orEmpty().ifBlank {row?.optString("cover_url").orEmpty()})
            }.distinctUntilChanged().collect {state->
                if(state[0]!="true"){selfStopped=true;stopSelf();return@collect}
                if(state[1]=="true"){if(wake.isHeld)wake.release()}else if(!wake.isHeld)wake.acquire()
                session.isActive=true
                val key=state.drop(2)
                if(artworkKey!=key) {
                    artworkKey=key;artwork=null;artworkTask?.cancel()
                    artworkTask=launch {
                        for(attempt in 0..2) {
                            if(attempt>0)delay(1000L*attempt)
                            val image=withContext(Dispatchers.IO) {
                                decodeMediaArtwork(state[5],state[6]) {url->
                                    val connection=URL(url).openConnection() as HttpURLConnection
                                    connection.connectTimeout=5000;connection.readTimeout=5000
                                    try {connection.inputStream.use {input->
                                        val output=java.io.ByteArrayOutputStream();val buffer=ByteArray(8192)
                                        while(output.size()<=10*1024*1024){val count=input.read(buffer);if(count<0)break;output.write(buffer,0,count)}
                                        val bytes=output.toByteArray()
                                        if(bytes.size>10*1024*1024)null else bytes
                                    }}finally {connection.disconnect()}
                                }
                            }
                            ensureActive()
                            if(artworkKey!=key)return@launch
                            if(image!=null){artwork=image;refresh();break}
                        }
                    }
                }
                refresh()
            }
        }
    }
    private fun action(name:String,code:Int)=PendingIntent.getService(this,code,Intent(this,JukeboxService::class.java).setAction(name),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    private fun notification():Notification {
        val state=controller.state.value;val model=state.model
        val title=model?.optString("media_title")?.takeIf {it.isNotBlank()} ?: state.title.takeIf {it.isNotBlank()} ?: translateUi("Reprodução")
        val artist=model?.optString("media_artist").orEmpty()
        val open=PendingIntent.getActivity(this,13,Intent(this,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this,"jukebox").setSmallIcon(R.drawable.ic_onda_notification)
            .setContentTitle(title).setContentText(artist.ifBlank {translateUi("Reprodução")}).setSubText(translateUi("Reprodução"))
            .setContentIntent(open).setLargeIcon(artwork).setOnlyAlertOnce(true).setOngoing(!state.paused)
            .addAction(Notification.Action.Builder(if(state.paused)android.R.drawable.ic_media_play else android.R.drawable.ic_media_pause,translateUi(if(state.paused)"Retomar" else "Pausar"),action(if(state.paused)"play" else "pause",14)).build())
            .addAction(Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,translateUi("Parar"),action("stop",15)).build())
            .setStyle(Notification.MediaStyle().setMediaSession(session.sessionToken).setShowActionsInCompactView(0,1)).build()
    }
    private fun refresh() {
        val state=controller.state.value;val model=state.model
        session.setPlaybackState(PlaybackState.Builder().setActions(PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_STOP or PlaybackState.ACTION_SKIP_TO_PREVIOUS or PlaybackState.ACTION_SKIP_TO_NEXT)
            .setState(if(state.paused)PlaybackState.STATE_PAUSED else PlaybackState.STATE_PLAYING,PlaybackState.PLAYBACK_POSITION_UNKNOWN,if(state.paused)0f else 1f).build())
        session.setMetadata(MediaMetadata.Builder().putString(MediaMetadata.METADATA_KEY_TITLE,model?.optString("media_title")?.takeIf {it.isNotBlank()} ?: state.title.ifBlank {translateUi("Reprodução")})
            .putString(MediaMetadata.METADATA_KEY_ARTIST,model?.optString("media_artist").orEmpty())
            .putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART,artwork).putBitmap(MediaMetadata.METADATA_KEY_ART,artwork)
            .putBitmap(MediaMetadata.METADATA_KEY_DISPLAY_ICON,artwork).build())
        getSystemService(NotificationManager::class.java).notify(13,notification())
    }
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        when(intent?.action){"play"->if(controller.state.value.paused)controller.playPause();"pause"->controller.pause();"stop"->controller.stop()}
        return START_NOT_STICKY
    }
    override fun onTaskRemoved(rootIntent:Intent?) {controller.stop();stopSelf()}
    override fun onDestroy() {
        // A stop from the previous song may finish after the next one has started.
        val restart=selfStopped && controller.state.value.playing
        if(!selfStopped)controller.stop()
        scope.cancel();if(wake.isHeld)wake.release();session.isActive=false;session.release();stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy()
        if(restart)androidx.core.content.ContextCompat.startForegroundService(applicationContext,Intent(applicationContext,JukeboxService::class.java))
    }
}
