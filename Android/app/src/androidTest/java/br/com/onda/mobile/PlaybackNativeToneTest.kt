package br.com.onda.mobile

import androidx.media3.exoplayer.ExoPlayer
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.pow

class PlaybackNativeToneTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun changingToneKeepsOnlinePlayerPositionAndPauseState() = runBlocking<Unit> {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
        val server = AndroidStreamingParityTest.AudioServer(30)
        lateinit var saved: JSONObject
        lateinit var controller: JukeboxController
        var transfers = 0
        try {
            withContext(Dispatchers.Main) {
                OndaStore.initialize(context)
                saved = OndaStore.settings.value
                OndaStore.settings.value = JSONObject(saved.toString()).put("jukebox_equalizer", JSONObject().put("enabled", false))
                controller = JukeboxController(context, scope, {}, callOverride = { action, config, id ->
                    if (action == "jukebox_prepare") JSONObject().put("title", "Native tone")
                        .put("duration", 30.0).put("beats", org.json.JSONArray().put(0.0).put(30.0))
                        .put("links", 0).put("_stream", JSONObject().put("url", server.url).put("source_url", server.url))
                    else {
                        if (action == "jukebox_transfer_prepare") transfers++
                        withContext(Dispatchers.IO) { MobileEngine.call(context, id, action, config, EventCallback {}) }
                    }
                })
                controller.normal = true
                controller.setVolume(0f)
                controller.setEffects("pitch_shift", 3)
                controller.prepare(record = JSONObject().put("title", "Native tone").put("source_url", server.url).put("duration_ms", 30000), autoPlay = true)
            }
            withTimeout(20000) { controller.audioReady.first { it } }
            val model = controller.state.value.model
            fun nativePlayer(): ExoPlayer {
                val stream = controller.javaClass.getDeclaredField("streaming").apply { isAccessible = true }.get(controller)!!
                return stream.javaClass.getDeclaredField("player").apply { isAccessible = true }.get(stream) as ExoPlayer
            }
            val player = withContext(Dispatchers.Main) { nativePlayer() }
            for (pitch in listOf(3, -1, 12, -12, 0)) {
                val before = withContext(Dispatchers.Main) {
                    controller.setEffects("pitch_shift", pitch)
                    player.currentPosition
                }
                delay(850)
                withContext(Dispatchers.Main) {
                    assertSame(model, controller.state.value.model)
                    assertSame(player, nativePlayer())
                    assertTrue(player.isPlaying)
                    assertTrue(player.currentPosition > before)
                    assertEquals(1f, player.playbackParameters.speed, .001f)
                    assertEquals(2.0.pow(pitch / 12.0).toFloat(), player.playbackParameters.pitch, .001f)
                    assertFalse(controller.effects.value.optBoolean("enabled"))
                    assertFalse(controller.state.value.effectsPending)
                    assertEquals("", controller.state.value.playbackError)
                    assertEquals(0, transfers)
                }
            }
            withContext(Dispatchers.Main) {
                controller.pause()
                controller.setEffects("pitch_shift", 4)
                assertFalse(player.playWhenReady)
            }
            delay(500)
            withContext(Dispatchers.Main) {
                assertTrue(controller.state.value.paused)
                assertFalse(player.playWhenReady)
            }
        } finally {
            withContext(Dispatchers.Main) {
                runCatching { controller.close() }
                runCatching { OndaStore.settings.value = saved }
                scope.cancel()
            }
            server.close()
        }
    }
}
