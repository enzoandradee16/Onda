package br.com.onda.mobile

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class PlaybackCardToneTest {
    @get:Rule val compose = createComposeRule()
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext


    @Test fun nativeToneChangesFrequencyWithoutChangingDuration() {
        MobileEngine.initialize(context)
        val builtins = com.chaquo.python.Python.getInstance().getModule("builtins")
        val scope = builtins.callAttr("dict")
        scope.callAttr("__setitem__", "folder", context.cacheDir.absolutePath)
        builtins.callAttr("exec", """
import subprocess, tempfile, wave, struct
from pathlib import Path
from mobile_backend import _native
from audio_tools import effects_filter
from playback_effects import PreparedEffects
with tempfile.TemporaryDirectory(dir=folder) as temp:
    root = Path(temp)
    ffmpeg = str(_native/'libffmpeg.so')
    def run(args):
        subprocess.run([ffmpeg, '-y', '-v', 'error', *args], check=True, capture_output=True, timeout=30)
    run(['-f', 'lavfi', '-i', 'sine=frequency=440:duration=4:sample_rate=44100', '-ac', '2', str(root/'audio.wav')])
    for shift, expected in [(-12, 220), (12, 880)]:
        target = root/'tone.wav'
        run(['-i', str(root/'audio.wav'), '-af', effects_filter(pitch_shift=shift), '-ar', '44100', str(target)])
        with wave.open(str(target), 'rb') as audio:
            assert abs(audio.getnframes()/audio.getframerate()-4) < .08
            audio.setpos(audio.getframerate())
            samples = struct.unpack('<'+'h'*(audio.getframerate()*2), audio.readframes(audio.getframerate()))[::2]
            crossings = sum(a <= 0 < b for a,b in zip(samples, samples[1:]))
            assert abs(crossings-expected) <= 2, (shift, crossings)
""".trimIndent(), scope)
    }

    @Test fun verySmallShrinksEntirePlaybackCard() {
        val store = androidx.lifecycle.ViewModelStore()
        OndaStore.initialize(context)
        MobileEngine.initialize(context)
        val saved = JSONObject(OndaStore.settings.value.toString())
        lateinit var vm: OndaViewModel
        compose.runOnUiThread {
            vm = androidx.lifecycle.ViewModelProvider(store,
                androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.getInstance(
                    androidx.test.core.app.ApplicationProvider.getApplicationContext()
                ))[OndaViewModel::class.java]
            vm.jukebox.stop()
            vm.jukebox.clearPlaybackQueue()
            vm.jukebox.state.value = JukeboxState(title = "Compact track", model = JSONObject()
                .put("media_artist", "Sample artist").put("album", "Sample album").put("release_date", "2001-03-12"))
            OndaStore.saveSettings(JSONObject(saved.toString()).put("playback_card_size", "Pequeno"))
        }
        try {
            compose.setContent { MaterialTheme { PlaybackPage(vm) } }
            compose.onNodeWithTag("effects-track-information").assertExists()
            val small = compose.onNodeWithTag("effects-track-information").fetchSemanticsNode().boundsInRoot.height
            compose.runOnIdle {
                OndaStore.saveSettings(JSONObject(saved.toString()).put("playback_card_size", "Muito pequeno"))
            }
            compose.waitUntil(5000) {
                compose.onNodeWithTag("effects-track-information").fetchSemanticsNode().boundsInRoot.height < small * .7f
            }
            compose.onNodeWithText("Compact track").assertExists()
            compose.onNodeWithText("Sample artist").assertExists()
            compose.onNodeWithText("Sample album").assertExists()
        } finally {
            compose.runOnUiThread { vm.jukebox.stop(); store.clear() }
            OndaStore.saveSettings(saved)
        }
    }

    @Test fun independentToneAndCardSizeControls() {
        OndaStore.initialize(context)
        val original = JSONObject(OndaStore.settings.value.toString())
        val scope = CoroutineScope(SupervisorJob().apply { cancel() } + Dispatchers.Main.immediate)
        val controller = JukeboxController(context, scope, {})
        try {
            OndaStore.saveSettings(JSONObject(original.toString()).put("playback_card_size", "Padrão"))
            compose.setContent {
                val settings by OndaStore.settings.collectAsState()
                val effects by controller.effects.collectAsState()
                MaterialTheme {
                    Column {
                        PlaybackMainCardSizeControl(settings)
                        PlaybackToneControl(effects.optInt("pitch_shift")) { controller.setEffects("pitch_shift", it) }
                    }
                }
            }
            compose.onNodeWithTag("playback-main-card-size").performClick()
            compose.onNodeWithText("Muito pequeno").performClick()
            compose.runOnIdle {
                assertEquals("Muito pequeno", OndaStore.settings.value.getString("playback_card_size"))
                assertTrue(playbackArtworkSide("Muito pequeno", true) < playbackArtworkSide("Pequeno", true))
                assertTrue(playbackArtworkSide("Muito pequeno", false) < playbackArtworkSide("Pequeno", false))
            }
            compose.onNodeWithTag("playback-main-card-size").performClick()
            compose.onNodeWithText("Grande").performClick()
            compose.runOnIdle {
                assertEquals("Grande", OndaStore.settings.value.getString("playback_card_size"))
                assertEquals(72, playbackArtworkSide("Padrão", true))
                assertEquals(88, playbackArtworkSide("Padrão", false))
                assertTrue(playbackArtworkSide("Pequeno", false) < playbackArtworkSide("Padrão", false))
                assertTrue(playbackArtworkSide("Grande", true) > playbackArtworkSide("Padrão", true))
            }
            compose.onNodeWithTag("unified-effects-pitch").assertIsEnabled()
                .performSemanticsAction(SemanticsActions.SetProgress) { it(5f) }
            compose.runOnIdle {
                assertEquals(5, controller.effects.value.getInt("pitch_shift"))
                assertFalse(controller.effects.value.getBoolean("enabled"))
                assertTrue(playbackEffectsActive(controller.effects.value))
                controller.setEffects("pitch_shift", 99)
                assertEquals(12, controller.effects.value.getInt("pitch_shift"))
            }
            compose.onNodeWithText("Restaurar tom").performClick()
            compose.runOnIdle {
                assertEquals(0, controller.effects.value.getInt("pitch_shift"))
                assertFalse(playbackEffectsActive(controller.effects.value))
            }
        } finally {
            OndaStore.saveSettings(original)
            scope.cancel()
        }
    }
}
