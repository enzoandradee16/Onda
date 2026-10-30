package br.com.onda.mobile

import android.content.Context
import android.content.Intent
import android.os.SystemClock
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject

/** Process-owned connection; UI and MediaSession share one state and command queue. */
internal object RemotePlaybackRuntime {
    val state = MutableStateFlow(RemotePlaybackState())
    val expandedRequested = MutableStateFlow(false)
    val localExpandedRequested = MutableStateFlow(false)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val commands = Channel<Pair<Long, JSONObject>>(16)
    private val queueMutex = Mutex()
    private var poll: Job? = null
    private var endpoint = ""
    private var token = ""
    private val pairedDevices = linkedMapOf<String, Pair<String, String>>()
    var generation = 0L
        private set

    init {
        scope.launch {
            for ((own, body) in commands) {
                if (own != generation || !state.value.online) continue
                val host = endpoint; val credential = token
                try { RemoteClient.request(host, "/v1/command", credential, body) }
                catch (cancelled: CancellationException) { throw cancelled }
                catch (_: Exception) {
                    if (own == generation) state.update { it.copy(notice = "Não foi possível enviar o comando. Tente novamente.") }
                }
            }
        }
    }

    suspend fun connect(context: Context, address: String, code: String) {
        val host = remoteEndpoint(address)
        val paired = RemoteClient.request(host, "/v1/pair", body = JSONObject().put("code", code))
        require(paired.optInt("protocol") == 1 && paired.optInt("features") >= 3) { "Atualize o ONDA PC para usar a reprodução remota integrada." }
        val credential = paired.optString("token")
        require(credential.length in 20..128) { "Resposta inválida do PC." }
        val name = paired.optString("name", "ONDA PC").take(80)
        if (pairedDevices.size >= 8) pairedDevices.remove(pairedDevices.keys.first())
        pairedDevices[host] = credential to name
        activate(context, host, credential, name)
    }

    suspend fun reconnect(context: Context, address: String): Boolean {
        val host = remoteEndpoint(address)
        val (credential, name) = pairedDevices[host] ?: return false
        try {
            val data = RemoteClient.request(host, "/v1/state", credential)
            require(data.optInt("protocol") == 1 && data.optInt("features") >= 3)
        } catch (cancelled: CancellationException) { throw cancelled
        } catch (_: Exception) { pairedDevices.remove(host); return false }
        activate(context, host, credential, name)
        return true
    }

    fun forget(address: String) {
        pairedDevices.remove(address)
        val preferences = OndaStore.context.getSharedPreferences("remote_control", 0)
        if (preferences.getString("address", "") == address) preferences.edit().remove("address").remove("name").apply()
        if (state.value.address == address) disconnect()
    }

    private fun activate(context: Context, host: String, credential: String, name: String) {
        poll?.cancel(); generation++
        endpoint = host; token = credential
        state.value = RemotePlaybackState(connected = true, title = "ONDA PC", deviceName = name, address = host)
        context.getSharedPreferences("remote_control", 0).edit().putString("address", host).putString("name", name).apply()
        try { ContextCompat.startForegroundService(context, Intent(context, RemotePlaybackService::class.java)) }
        catch (error: Exception) { disconnect(); throw error }
        // Keep the local song and its position, but release local audio and MediaSession.
        JukeboxRuntime.get(context).stopPreservingPosition()
        EffectsPlaybackRuntime.owner?.let { it.mediaPauseEffects(); EffectsPlaybackRuntime.clear(it) }
        context.stopService(Intent(context, EffectsPlaybackService::class.java))
    }

    fun startPolling() {
        poll?.cancel()
        val own = generation; val host = endpoint; val credential = token
        if (!state.value.connected) return
        poll = scope.launch {
            var failedSince = 0L
            while (isActive && own == generation) {
                try {
                    val data = RemoteClient.request(host, "/v1/state", credential)
                    if (own != generation) break
                    require(data.optInt("protocol") == 1 && data.optInt("features") >= 3)
                    val previous = state.value
                    val artId = data.optString("artwork_id").takeIf { it.matches(Regex("[a-f0-9]{24}")) }.orEmpty()
                    val effects = data.optJSONObject("effects") ?: JSONObject()
                    val jukebox = data.optJSONObject("jukebox") ?: JSONObject()
                    val search = data.optJSONObject("search") ?: JSONObject()
                    val searchRows = search.optJSONArray("rows")
                    state.value = previous.copy(
                        effects = RemoteEffects(effects.optBoolean("enabled"), effects.optInt("speed", 85), effects.optInt("reverb", 25), effects.optBoolean("keep_pitch")),
                        jukebox = RemoteJukebox(jukebox.optDouble("variation", 20.0).toFloat(), jukebox.optDouble("smooth", 50.0).toFloat(), jukebox.optBoolean("normal", true)),
                        effectsPending = data.optBoolean("effects_pending"), searchBusy = search.optBoolean("busy"),
                        searchRows = (0 until (searchRows?.length() ?: 0).coerceAtMost(100)).mapNotNull { searchRows?.optJSONObject(it)?.let(::readTrack) },
                        searchMessage = search.optString("message"), searchBatch = search.optString("batch"),
                        deviceName = data.optString("device_name", previous.deviceName).take(80),
                        shuffle = data.optBoolean("shuffle"), repeat = data.optString("repeat", "Desativada"),
                        online = true, title = data.optString("title"), artist = data.optString("artist"), album = data.optString("album"),
                        trackId = data.optString("track_id"), position = data.optDouble("position", 0.0).safeSeconds(),
                        duration = data.optDouble("duration", 0.0).safeSeconds(), playing = data.optBoolean("playing"), ready = data.optBoolean("ready"),
                        busy = data.optBoolean("busy"), speed = data.optDouble("speed", 1.0).takeIf { it.isFinite() && it in 0.5..1.5 }?.toFloat() ?: 1f,
                        volume = data.optInt("volume", 80).coerceIn(0, 100), receivedAt = SystemClock.elapsedRealtime(),
                        artworkId = artId, artwork = if (artId == previous.artworkId) previous.artwork else null, notice = "",
                    )
                    failedSince = 0L
                    if (artId.isNotBlank() && state.value.artwork == null) {
                        val bytes = runCatching { RemoteClient.artwork(host, credential, artId) }.getOrNull()
                        ensureActive()
                        if (own == generation && state.value.artworkId == artId && bytes != null) state.update { it.copy(artwork = bytes) }
                    }
                    if (state.value.queueRevision != data.optLong("queue_revision", -1)) loadQueue(own, reset = true)
                } catch (cancelled: CancellationException) { throw cancelled
                } catch (error: Exception) {
                    if (own != generation) break
                    if (error is RemoteHttpException && error.status == 401) { disconnect("Conecte novamente com o código exibido no PC."); break }
                    val now = SystemClock.elapsedRealtime()
                    if (failedSince == 0L) failedSince = now
                    state.update { it.copy(online = false, position = it.positionAt(now), receivedAt = now, notice = "Conexão perdida. Verifique o PC e a rede Wi-Fi ou conecte novamente.") }
                    if (now - failedSince >= 90000) { disconnect("Conexão encerrada. Conecte novamente ao ONDA PC."); break }
                }
                delay(if (state.value.online) 1000 else 3000)
            }
        }
    }

    private fun Double.safeSeconds(): Double = if (isFinite()) coerceIn(0.0, 86400.0) else 0.0

    private suspend fun loadQueue(own: Long, reset: Boolean) = queueMutex.withLock {
        if (own != generation || !state.value.connected) return@withLock
        val before = state.value
        val offset = if (reset) 0 else before.queue.size
        state.update { it.copy(queueLoading = true) }
        try {
            val data = RemoteClient.request(endpoint, "/v1/queue?offset=$offset", token)
            if (own != generation) return@withLock
            val revision = data.optLong("revision", -1)
            if (!reset && revision != before.queueRevision) return@withLock
            val rows = data.optJSONArray("rows")
            val page = (0 until (rows?.length() ?: 0)).mapNotNull { index ->
                val row = rows?.optJSONObject(index) ?: return@mapNotNull null
                val id = row.optString("id").takeIf { it.isNotBlank() && it.length <= 128 } ?: return@mapNotNull null
                readTrack(row)
            }
            state.update { it.copy(queue = if (reset) page else (before.queue + page).distinctBy { row -> row.id }, queueRevision = revision, queueTotal = data.optInt("total").coerceIn(0, 5000)) }
        } finally { if (own == generation) state.update { it.copy(queueLoading = false) } }
    }

    fun loadMore() {
        val own = generation
        if (!state.value.online || state.value.queueLoading || state.value.queue.size >= state.value.queueTotal) return
        scope.launch { runCatching { loadQueue(own, reset = false) } }
    }

    private fun readTrack(row: JSONObject): RemoteQueueTrack = RemoteQueueTrack(row.optString("id"), row.optString("title"), row.optString("artist"), row.optDouble("duration", 0.0).safeSeconds(), row.optString("cover").takeIf { it.startsWith("https://") }.orEmpty(), row.optString("preparation"), row.optInt("recent_rank", -1))

    fun effects(key: String, value: Any) = command("effects", JSONObject().put(key, value))
    fun clearSearch() {
        command("search_cancel")
        state.update { it.copy(searchBusy = false, searchRows = emptyList(), searchMessage = "", searchBatch = "") }
    }
    fun jukebox(key: String, value: Any) = command("jukebox", JSONObject().put(key, value))

    fun moveQueue(id: String, delta: Int) {
        val rows = state.value.queue
        val index = rows.indexOfFirst { it.id == id }
        if (index < 0) return
        val target = rows.getOrNull(index + delta) ?: return
        command("queue_move_to", target.id, id)
    }

    fun command(name: String, value: Any? = null, trackId: String? = null) {
        if (!state.value.online) return
        val body = JSONObject().put("command", name)
        if (value != null) body.put("value", value)
        if (trackId != null) body.put("track_id", trackId)
        if (!commands.trySend(generation to body).isSuccess) {
            state.update { it.copy(notice = "Aguarde o comando anterior.") }
            return
        }
        val now = SystemClock.elapsedRealtime()
        if (name == "effects" && value is JSONObject) state.update {
            val before = it.effects
            it.copy(effects = before.copy(enabled = value.optBoolean("enabled", before.enabled), speed = value.optInt("speed", before.speed), reverb = value.optInt("reverb", before.reverb), keepPitch = value.optBoolean("keep_pitch", before.keepPitch)))
        }
        if (name == "jukebox" && value is JSONObject) state.update {
            val before = it.jukebox
            it.copy(jukebox = before.copy(variation = value.optDouble("variation", before.variation.toDouble()).toFloat(), smooth = value.optDouble("smooth", before.smooth.toDouble()).toFloat(), normal = value.optBoolean("normal", before.normal)))
        }
        if (name == "play" || name == "pause") state.update {
            it.copy(playing = name == "play", position = it.positionAt(now), receivedAt = now)
        }
        if (name == "seek" && trackId == state.value.trackId && value is Number) state.update {
            it.copy(position = value.toDouble().coerceIn(0.0, it.duration.coerceAtLeast(0.0)), receivedAt = now)
        }
    }

    fun toggle() = command(if (state.value.playing) "pause" else "play")
    fun seek(seconds: Double) = command("seek", seconds, state.value.trackId)

    fun setVolume(value: Int) {
        if (!state.value.online) return
        val volume = value.coerceIn(0, 100)
        state.update { it.copy(volume = volume) }
        command("volume", volume)
    }

    fun disconnect(notice: String = "") {
        generation++; poll?.cancel(); poll = null; token = ""; endpoint = ""
        state.value = RemotePlaybackState(notice = notice)
        expandedRequested.value = false
        OndaStore.context.stopService(Intent(OndaStore.context, RemotePlaybackService::class.java))
    }
}
