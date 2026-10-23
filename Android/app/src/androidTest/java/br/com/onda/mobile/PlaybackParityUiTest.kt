package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.ui.Modifier
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

@RunWith(AndroidJUnit4::class)
class PlaybackParityUiTest {
    @get:Rule val compose=createComposeRule()
    private val store=ViewModelStore()
    private fun model():OndaViewModel {
        val app=ApplicationProvider.getApplicationContext<android.app.Application>()
        OndaStore.initialize(app);MobileEngine.initialize(app)
        OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("check_updates",false).put("resume_queue",false).put("jukebox_gradual_transition",true).put("jukebox_transition_seconds",1))
        lateinit var vm:OndaViewModel
        compose.runOnUiThread {vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(app))[OndaViewModel::class.java]}
        return vm
    }
    private fun screenshot(name:String) {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val image=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        File(context.getExternalFilesDir(null),name).outputStream().use {image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
        image.recycle()
    }
    private fun audio(name:String):File {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val data=ByteArray(22050*2*40)
        val header=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).put("RIFF".toByteArray()).putInt(36+data.size).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1).putShort(1).putInt(22050).putInt(44100).putShort(2).putShort(16).put("data".toByteArray()).putInt(data.size).array()
        return File(context.cacheDir,name).also {file->file.outputStream().use {it.write(header);it.write(data)}}
    }
    @Test fun effectsTransportStaysVisibleAndPreservesPauseSeekAndStop() {
        val vm=model();val source=audio("parity-one.wav")
        try {
            compose.runOnUiThread {vm.storeLyrics(source.path,listOf(0.0 to "First",10.0 to "Second"));vm.effectsSource.value=source.path}
            compose.setContent {MaterialTheme {Column(Modifier.fillMaxSize()){Box(Modifier.weight(1f)){EffectsPage(vm)};AndroidPlaybackSurface(vm)}}}
            compose.onNodeWithTag("effects-volume").assertDoesNotExist()
            compose.waitUntil(30000) {(vm.effectsInfo.value[source.path]?.optDouble("duration",0.0) ?: 0.0)>0}
            compose.onNodeWithTag("compact-player-toggle").assertIsDisplayed().performClick()
            compose.waitUntil(60000){vm.previewActive.value&&!vm.effectsPreparing.value}
            compose.waitUntil(10000){vm.effectsPosition.value>.1}
            val app=ApplicationProvider.getApplicationContext<android.app.Application>()
            val notifications=app.getSystemService(android.app.NotificationManager::class.java)
            compose.waitUntil(10000){notifications.activeNotifications.any {it.id==14}}
            val notification=notifications.activeNotifications.first {it.id==14}.notification
            @Suppress("DEPRECATION")
            val token=notification.extras.getParcelable<android.media.session.MediaSession.Token>(android.app.Notification.EXTRA_MEDIA_SESSION)!!
            val media=android.media.session.MediaController(app,token)
            assertEquals(source.path,EffectsPlaybackRuntime.state.value?.source)
            media.transportControls.pause()
            compose.waitUntil(10000){!vm.effectsPreviewEnabled.value}
            media.transportControls.seekTo(5000)
            compose.waitUntil(10000){kotlin.math.abs(vm.effectsPosition.value-5.0)<.1}
            media.transportControls.play()
            compose.waitUntil(60000){vm.previewActive.value&&!vm.effectsPreparing.value&&vm.effectsPreviewEnabled.value}
            compose.onNodeWithTag("compact-player-toggle").performClick()
            compose.runOnIdle {assertFalse(vm.effectsPreviewEnabled.value)}
            compose.onNodeWithTag("android-compact-player").performClick()
            compose.onNodeWithTag("android-expanded-player").assertIsDisplayed()
            compose.onNodeWithTag("expanded-album-cover").assertIsDisplayed()
            compose.onNodeWithTag("expanded-player-timeline").performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.SetProgress){it(10f)}
            compose.onNodeWithContentDescription("Recolher reprodução").performClick()
            compose.runOnIdle {assertEquals(10.0,vm.effectsPosition.value,.1)}
            compose.onNodeWithTag("compact-player-toggle").performClick()
            compose.waitUntil(60000){vm.previewActive.value&&!vm.effectsPreparing.value}
            compose.onNodeWithTag("effects-reverb").performScrollTo()
            compose.onNodeWithTag("android-compact-player").assertIsDisplayed()
            screenshot("paridade-efeitos.png")
            compose.runOnIdle {vm.stopEffectsPlayback()}
            compose.runOnIdle {assertFalse(vm.effectsPreviewEnabled.value);assertEquals(0.0,vm.effectsPosition.value,.001)}
        } finally {compose.runOnUiThread {store.clear()};source.delete()}
    }
    @Test fun playbackTabsKeepTheirOwnMusicWhenSelectionAndTabChange() {
        val vm=model();val effects=audio("effects-independent.wav");val jukebox=audio("jukebox-independent.wav")
        val original=vm.jukebox.state.value
        try {
            compose.runOnUiThread {
                vm.effectsSource.value=effects.path;vm.appendEffectsFiles(listOf(effects.path))
                vm.playbackMode.value=0
                vm.jukebox.state.value=JukeboxState(model=JSONObject().put("source",jukebox.path),title="Jukebox independente")
            }
            compose.setContent {MaterialTheme {PlaybackPage(vm)}}
            compose.onNodeWithText("Jukebox infinito").performClick()
            compose.onNodeWithText("Reprodução normal").assertExists()
            compose.runOnIdle {vm.jukebox.normal=true}
            compose.runOnIdle {
                assertTrue(vm.jukebox.normal)
                assertEquals(effects.path,vm.effectsSource.value)
                assertEquals(listOf(effects.path),vm.effectsPlaylist.value)
                assertEquals(jukebox.path,vm.jukebox.state.value.model?.optString("source"))
            }
            compose.onNodeWithText("Efeitos").performClick()
            compose.runOnIdle {
                assertEquals(effects.path,vm.effectsSource.value)
                assertEquals(jukebox.path,vm.jukebox.state.value.model?.optString("source"))
            }
        } finally {compose.runOnUiThread {vm.jukebox.normal=false;vm.jukebox.state.value=original;store.clear()};effects.delete();jukebox.delete()}
    }
    @Test fun switchingTabsKeepsEffectsPlayingAndEachPageCanTakeOverPlayback() {
        val vm=model();val effects=audio("effects-handoff.wav");val jukebox=audio("jukebox-handoff.wav")
        try {
            compose.runOnUiThread {vm.effectsSource.value=effects.path;vm.playbackMode.value=0}
            compose.setContent {MaterialTheme {Column(Modifier.fillMaxSize()){Box(Modifier.weight(1f)){PlaybackPage(vm)};AndroidPlaybackSurface(vm)}}}
            compose.waitUntil(30000){(vm.effectsInfo.value[effects.path]?.optDouble("duration",0.0) ?: 0.0)>0}
            compose.onNodeWithTag("effects-page-play").assertDoesNotExist()
            compose.onNodeWithTag("compact-player-toggle").performClick()
            compose.waitUntil(60000){vm.previewActive.value&&!vm.effectsPreparing.value}
            var rendered=""
            compose.runOnIdle {rendered=vm.previewUrl.value}
            compose.onNodeWithText("Jukebox infinito").performClick()
            compose.runOnIdle {assertTrue(vm.effectsPreviewEnabled.value);assertEquals(rendered,vm.previewUrl.value);vm.jukebox.prepare(jukebox.path)}
            compose.waitUntil(120000){vm.jukebox.state.value.model!=null&&!vm.jukebox.state.value.busy}
            compose.onNodeWithTag("jukebox-page-play").performScrollTo().performClick()
            compose.waitUntil(10000){vm.jukebox.state.value.playing&&!vm.jukebox.state.value.paused&&!vm.effectsPreviewEnabled.value}
            compose.onNodeWithTag("jukebox-page-play").assertDoesNotExist()
            compose.onNodeWithText("Efeitos").performClick()
            compose.onNodeWithTag("effects-page-play").performScrollTo().performClick()
            compose.waitUntil(60000){vm.previewActive.value&&!vm.effectsPreparing.value&&vm.jukebox.state.value.paused}
            compose.onNodeWithText("Jukebox infinito").performClick()
            compose.onNodeWithTag("jukebox-page-play").performScrollTo().performClick()
            compose.waitUntil(10000){!vm.jukebox.state.value.paused&&!vm.effectsPreviewEnabled.value}
            compose.runOnIdle {assertEquals(effects.path,vm.effectsSource.value);assertEquals(jukebox.path,vm.jukebox.state.value.model?.optString("source"))}
        } finally {compose.runOnUiThread {vm.jukebox.stop();vm.stopEffectsPlayback();store.clear()};effects.delete();jukebox.delete()}
    }
    @Test fun lyricsShowAllVersesAndSeekingSelectsTheTappedVerse() {
        val vm=model();var position=0.0
        try {
            compose.runOnUiThread {vm.storeLyrics("fixture",listOf(0.0 to "First verse",10.0 to "Second verse",20.0 to "Third verse"))}
            compose.setContent {MaterialTheme {LyricsButton(vm,"fixture",{position},30.0,{position=it},{})}}
            compose.onNodeWithTag("lyrics-button").performClick()
            compose.onNodeWithText("First verse").assertExists()
            compose.onNodeWithText("Third verse").assertExists()
            screenshot("paridade-letras.png")
            compose.onNodeWithText("Second verse").performClick()
            compose.runOnIdle {assertEquals(10.0,position,.001)}
        } finally {compose.runOnUiThread {store.clear()}}
    }
    @Test fun lyricsCardExpandsWithMetadataAndControlsTheSamePlayback() {
        val vm=model()
        val position=androidx.compose.runtime.mutableDoubleStateOf(0.0)
        val playing=androidx.compose.runtime.mutableStateOf(true)
        try {
            compose.runOnUiThread {vm.storeLyrics("lyrics-card-fixture",listOf(0.0 to "First verse",15.0 to "Second verse",30.0 to "Third verse"))}
            compose.setContent {MaterialTheme {LyricsPreviewCard(vm,"lyrics-card-fixture","Fixture song","Fixture artist",position.doubleValue,45.0,playing.value,{position.doubleValue=it},{playing.value=!playing.value})}}
            compose.onNodeWithTag("lyrics-preview-card").performClick()
            compose.onNodeWithTag("lyrics-fullscreen").assertIsDisplayed()
            compose.onNodeWithText("Fixture song").assertIsDisplayed()
            compose.onNodeWithText("Fixture artist").assertIsDisplayed()
            compose.onNodeWithTag("lyric-line-1").performClick()
            compose.runOnIdle {assertEquals(15.0,position.doubleValue,.001)}
            compose.onNodeWithTag("lyrics-play-pause").performClick()
            compose.runOnIdle {assertFalse(playing.value)}
            compose.onNodeWithContentDescription("Recolher letra").performClick()
            compose.onNodeWithTag("lyrics-fullscreen").assertDoesNotExist()
            compose.onNodeWithTag("lyrics-preview-card").assertIsDisplayed()
        } finally {compose.runOnUiThread {store.clear()}}
    }
    @Test fun effectsQueueReordersWithoutChangingTheSelectedFile() {
        val vm=model();val first=audio("parity-first.wav");val second=audio("parity-second.wav")
        try {
            compose.runOnUiThread {vm.appendEffectsFiles(listOf(first.path,second.path));vm.effectsSource.value=first.path;vm.storeLyrics(first.path,emptyList())}
            compose.setContent {MaterialTheme {Column(Modifier.fillMaxSize()){Box(Modifier.weight(1f)){EffectsPage(vm)};AndroidPlaybackSurface(vm)}}}
            compose.onNodeWithText("Fila (2)").assertDoesNotExist()
            compose.onNodeWithTag("compact-player-queue").performClick()
            compose.onNodeWithTag("effects-queue-panel").assertExists()
            compose.runOnIdle {vm.moveEffectsTrack(0,1);assertEquals(first.path,vm.effectsSource.value);assertEquals(listOf(second.path,first.path),vm.effectsPlaylist.value)}
            compose.runOnIdle {vm.clearEffectsQueue();assertEquals(first.path,vm.effectsSource.value);assertTrue(vm.effectsPlaylist.value.isEmpty())}
        } finally {compose.runOnUiThread {store.clear()};first.delete();second.delete()}
    }
    @Test fun effectsTrackChangeOverlapsBothOutputsAndStopReleasesTheTail() {
        val vm=model();val first=audio("parity-fade-first.wav");val second=audio("parity-fade-second.wav")
        try {
            compose.runOnUiThread {
                OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("jukebox_transition_seconds",3))
                vm.appendEffectsFiles(listOf(first.path,second.path));vm.effectsSource.value=first.path
                vm.storeLyrics(first.path,emptyList());vm.storeLyrics(second.path,emptyList())
            }
            compose.setContent {MaterialTheme {Column(Modifier.fillMaxSize()){Box(Modifier.weight(1f)){EffectsPage(vm)};AndroidPlaybackSurface(vm)}}}
            compose.waitUntil(30000){vm.effectsInfo.value.size>=2}
            compose.onNodeWithTag("compact-player-toggle").performClick()
            compose.waitUntil(60000){vm.previewActive.value&&!vm.effectsPreparing.value}
            compose.waitUntil(60000){vm.isEffectsTrackPreloaded(second.path,85,25,false)}
            lateinit var outgoing:androidx.media3.exoplayer.ExoPlayer
            compose.runOnIdle {outgoing=vm.player}
            compose.onNodeWithTag("android-compact-player").performClick()
            compose.onNodeWithTag("expanded-player-next").performClick()
            compose.waitUntil(60000){var both=false;compose.runOnUiThread {both=vm.player!==outgoing&&vm.player.isPlaying&&outgoing.isPlaying};both}
            compose.runOnIdle {vm.stopEffectsPlayback()}
            compose.runOnIdle {assertFalse(outgoing.isPlaying);assertFalse(vm.player.isPlaying);assertEquals(0.0,vm.effectsPosition.value,.001)}
        } finally {compose.runOnUiThread {store.clear()};first.delete();second.delete()}
    }
}
