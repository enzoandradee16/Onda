package br.com.onda.mobile

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadata
import android.media.VolumeProvider
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.*
import kotlinx.coroutines.*

/** Publishes the PC player to Android without opening an audio output on the phone. */
class RemotePlaybackService: Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private lateinit var session: MediaSession
    private lateinit var volume: VolumeProvider
    private lateinit var wake: PowerManager.WakeLock
    private var artwork: Bitmap? = null
    private var artworkId = ""
    private var ownGeneration = 0L

    override fun onBind(intent: Intent?) = null

    override fun onCreate() {
        super.onCreate()
        ownGeneration = RemotePlaybackRuntime.generation
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel("remote-playback", translateUi("Controle remoto"), NotificationManager.IMPORTANCE_LOW)
        )
        wake = getSystemService(PowerManager::class.java).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ONDA:RemoteControl").apply { setReferenceCounted(false) }
        session = MediaSession(this, "ONDA PC")
        volume = object: VolumeProvider(VolumeProvider.VOLUME_CONTROL_ABSOLUTE, 100, RemotePlaybackRuntime.state.value.volume) {
            override fun onSetVolumeTo(value: Int) { scope.launch { RemotePlaybackRuntime.setVolume(value) } }
            override fun onAdjustVolume(direction: Int) {
                if (direction == -1 || direction == 1) scope.launch { RemotePlaybackRuntime.setVolume(RemotePlaybackRuntime.state.value.volume + direction * 5) }
            }
        }
        session.setPlaybackToRemote(volume)
        session.setCallback(object: MediaSession.Callback() {
            override fun onPlay() { RemotePlaybackRuntime.command("play") }
            override fun onPause() { RemotePlaybackRuntime.command("pause") }
            override fun onStop() { RemotePlaybackRuntime.disconnect() }
            override fun onSkipToPrevious() { RemotePlaybackRuntime.command("previous") }
            override fun onSkipToNext() { RemotePlaybackRuntime.command("next") }
            override fun onSeekTo(position: Long) { RemotePlaybackRuntime.seek(position / 1000.0) }
        }, Handler(Looper.getMainLooper()))
        val notification = notification(RemotePlaybackRuntime.state.value)
        if (Build.VERSION.SDK_INT >= 29) startForeground(16, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        else startForeground(16, notification)
        scope.launch {
            RemotePlaybackRuntime.state.collect { state ->
                if (!state.connected) { stopSelf(); return@collect }
                if (state.online && state.playing) {
                    if (!wake.isHeld) wake.acquire(10 * 60 * 1000L)
                } else if (wake.isHeld) wake.release()
                if (artworkId != state.artworkId || (artwork == null && state.artwork != null)) {
                    artworkId = state.artworkId
                    val bytes = state.artwork
                    artwork = withContext(Dispatchers.IO) { bytes?.let {
                        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                        BitmapFactory.decodeByteArray(it, 0, it.size, bounds)
                        if (bounds.outWidth in 1..2048 && bounds.outHeight in 1..2048) BitmapFactory.decodeByteArray(it, 0, it.size) else null
                    } }
                }
                session.isActive = true
                volume.setCurrentVolume(state.volume)
                val now = SystemClock.elapsedRealtime()
                val actions = PlaybackState.ACTION_STOP or if (state.online) (
                    PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or
                    PlaybackState.ACTION_SKIP_TO_NEXT or PlaybackState.ACTION_SKIP_TO_PREVIOUS or PlaybackState.ACTION_SEEK_TO
                ) else 0L
                session.setPlaybackState(PlaybackState.Builder().setActions(actions).setState(
                    when { !state.online -> PlaybackState.STATE_CONNECTING; state.busy -> PlaybackState.STATE_BUFFERING; state.playing -> PlaybackState.STATE_PLAYING; else -> PlaybackState.STATE_PAUSED },
                    (state.positionAt(now) * 1000).toLong(), if (state.online && state.playing) state.speed else 0f, now
                ).build())
                session.setMetadata(MediaMetadata.Builder().putString(MediaMetadata.METADATA_KEY_TITLE, state.title)
                    .putString(MediaMetadata.METADATA_KEY_ARTIST, state.artist).putString(MediaMetadata.METADATA_KEY_ALBUM, state.album)
                    .putString(MediaMetadata.METADATA_KEY_DISPLAY_SUBTITLE, translateUi("Reproduzindo no computador"))
                    .putLong(MediaMetadata.METADATA_KEY_DURATION, (state.duration * 1000).toLong())
                    .putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART, artwork).putBitmap(MediaMetadata.METADATA_KEY_ART, artwork).build())
                getSystemService(NotificationManager::class.java).notify(16, notification(state))
            }
        }
    }

    private fun action(name: String, code: Int) = PendingIntent.getService(this, code,
        Intent(this, RemotePlaybackService::class.java).setAction(name), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

    private fun notification(state: RemotePlaybackState): Notification {
        val open = PendingIntent.getActivity(this, 260, Intent(this, MainActivity::class.java).putExtra("open_remote", true)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, "remote-playback").setSmallIcon(R.drawable.ic_onda_notification)
            .setContentTitle(state.title.ifBlank { "ONDA PC" }).setContentText(state.artist)
            .setSubText(translateUi(if (state.online) "Reproduzindo no computador" else "Computador desconectado"))
            .setContentIntent(open).setLargeIcon(artwork).setOnlyAlertOnce(true).setOngoing(true).setVisibility(Notification.VISIBILITY_PUBLIC)
            .addAction(Notification.Action.Builder(android.R.drawable.ic_media_previous, translateUi("Retroceder"), action("previous", 261)).build())
            .addAction(Notification.Action.Builder(if (state.playing) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play,
                translateUi(if (state.playing) "Pausar" else "Reproduzir"), action(if (state.playing) "pause" else "play", 262)).build())
            .addAction(Notification.Action.Builder(android.R.drawable.ic_media_next, translateUi("Avançar"), action("next", 263)).build())
            .addAction(Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel, translateUi("Desconectar"), action("disconnect", 264)).build())
            .setStyle(Notification.MediaStyle().setMediaSession(session.sessionToken).setShowActionsInCompactView(0, 1, 2)).build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        ownGeneration = RemotePlaybackRuntime.generation
        when (intent?.action) {
            "disconnect" -> RemotePlaybackRuntime.disconnect()
            "play", "pause", "next", "previous" -> RemotePlaybackRuntime.command(intent.action!!)
            else -> RemotePlaybackRuntime.startPolling()
        }
        if (!RemotePlaybackRuntime.state.value.connected) stopSelf()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        if (wake.isHeld) wake.release()
        session.isActive = false; session.release()
        stopForeground(STOP_FOREGROUND_REMOVE)
        if (ownGeneration == RemotePlaybackRuntime.generation && RemotePlaybackRuntime.state.value.connected) RemotePlaybackRuntime.disconnect()
        super.onDestroy()
    }
}
