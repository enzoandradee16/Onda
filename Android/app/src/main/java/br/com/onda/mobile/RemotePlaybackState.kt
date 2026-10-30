package br.com.onda.mobile

internal data class RemoteQueueTrack(
    val id: String, val title: String, val artist: String,
    val duration: Double = 0.0, val cover: String = "",
    val preparation: String = "",
    val recentRank: Int = -1,
)

internal data class RemoteEffects(val enabled: Boolean = false, val speed: Int = 85, val reverb: Int = 25, val keepPitch: Boolean = false)
internal data class RemoteJukebox(val variation: Float = 20f, val smooth: Float = 50f, val normal: Boolean = true)

internal data class RemotePlaybackState(
    val deviceName: String = "ONDA PC", val address: String = "",
    val shuffle: Boolean = false, val repeat: String = "Desativada",
    val connected: Boolean = false, val online: Boolean = false,
    val title: String = "", val artist: String = "", val album: String = "",
    val trackId: String = "", val position: Double = 0.0, val duration: Double = 0.0,
    val playing: Boolean = false, val ready: Boolean = false, val busy: Boolean = false,
    val speed: Float = 1f, val volume: Int = 80, val receivedAt: Long = 0L,
    val artworkId: String = "", val artwork: ByteArray? = null,
    val queue: List<RemoteQueueTrack> = emptyList(), val queueTotal: Int = 0,
    val queueRevision: Long = -1, val queueLoading: Boolean = false,
    val notice: String = "",
    val effects: RemoteEffects = RemoteEffects(), val jukebox: RemoteJukebox = RemoteJukebox(), val effectsPending: Boolean = false,
    val searchBusy: Boolean = false, val searchRows: List<RemoteQueueTrack> = emptyList(), val searchMessage: String = "", val searchBatch: String = "",
) {
    fun positionAt(now: Long): Double {
        val elapsed = if (online && playing && receivedAt > 0) ((now - receivedAt).coerceAtLeast(0) / 1000.0) * speed else 0.0
        return (position + elapsed.coerceAtMost(3.0)).coerceIn(0.0, duration.coerceAtLeast(0.0))
    }
}
