package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.json.JSONArray
import org.json.JSONObject
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import android.app.Notification
import android.app.NotificationManager
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSession
import java.nio.ByteBuffer
import java.nio.ByteOrder

@RunWith(AndroidJUnit4::class)
class JukeboxMediaTest {
    @Test fun graphShowsAllConnectionsBeforePlayback() {
        val rows=JSONArray().apply {repeat(64){put(JSONArray().put((it+12)%64))}}
        val model=JSONObject().put("neighbors",rows)
        assertEquals((0 until 64).map {it to (it+12)%64},jukeboxVisibleLinks(model,false))
        assertTrue(jukeboxVisibleLinks(model,true).isEmpty())
        assertTrue(jukeboxVisibleLinks(null,false).isEmpty())
    }
    @Test fun mediaNotificationControlsKeepInfiniteAudioInBackground() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        val scenario=ActivityScenario.launch(MainActivity::class.java)
        val before=JSONObject(OndaStore.settings.value.toString())
        val controller=JukeboxRuntime.get(context)
        val source=java.io.File(context.cacheDir,"jukebox-media-silence.wav")
        fun await(check:()->Boolean) {val end=System.currentTimeMillis()+10000;while(!check() && System.currentTimeMillis()<end)Thread.sleep(50);assertTrue("Playback: ${controller.state.value.message}, playing=${controller.state.value.playing}, queued=${controller.playbackQueue.value.size}",check())}
        try {
            val data=ByteArray(44100*4*4)
            val header=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).put("RIFF".toByteArray()).putInt(36+data.size).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1).putShort(2).putInt(44100).putInt(176400).putShort(4).putShort(16).put("data".toByteArray()).putInt(data.size).array()
            source.outputStream().use {it.write(header);it.write(data)}
            val model=MobileEngine.call(context,"jukebox-media-test","jukebox_prepare",OndaStore.config().put("source",source.absolutePath),EventCallback {})
            assertFalse(model.toString(),model.has("error"))
            model.put("media_title","Silent test").put("media_artist","ONDA")
            scenario.onActivity {
                OndaStore.saveSettings(JSONObject(before.toString()).put("jukebox_background",true))
                controller.state.value=JukeboxState(title="",model=model)
                controller.playPause()
            }
            await {controller.state.value.elapsed>.1}
            val manager=context.getSystemService(NotificationManager::class.java)
            await {manager.activeNotifications.any {it.id==13}}
            val notification=manager.activeNotifications.first {it.id==13}.notification
            @Suppress("DEPRECATION") val token=notification.extras.getParcelable<MediaSession.Token>(Notification.EXTRA_MEDIA_SESSION)
            assertNotNull(token)
            val media=MediaController(context,token!!)
            assertEquals("Silent test",media.metadata?.getString(MediaMetadata.METADATA_KEY_TITLE))
            assertEquals("ONDA",media.metadata?.getString(MediaMetadata.METADATA_KEY_ARTIST))
            instrumentation.uiAutomation.executeShellCommand("input keyevent KEYCODE_HOME").close()
            await {controller.state.value.elapsed>.4}
            assertTrue(controller.state.value.playing);assertFalse(controller.state.value.paused)
            media.transportControls.pause();await {controller.state.value.paused}
            media.transportControls.play();await {!controller.state.value.paused}
            media.transportControls.stop();await {!controller.state.value.playing}
            await {manager.activeNotifications.none {it.id==13}}
            instrumentation.runOnMainSync {
                repeat(2){controller.enqueue(JSONObject().put("title","Queued test").put("_local_source",source.absolutePath))}
            }
            await {controller.playbackQueue.value.size==2 && controller.playbackQueue.value.all {it.optString("_analysis")=="Pronta"}}
            instrumentation.runOnMainSync {controller.setTimer(30);controller.setTimer(5,true);controller.playQueued(0)}
            await {controller.state.value.elapsed>.1}
            assertEquals(30,controller.timerMinutes.value);assertEquals(5,controller.switchMinutes.value)
            val trackField=JukeboxController::class.java.getDeclaredField("track").apply {isAccessible=true}
            val outputBefore=trackField.get(controller)
            instrumentation.runOnMainSync {controller.playQueued(0)}
            await {controller.playbackQueue.value.isEmpty() && controller.state.value.elapsed>.1}
            assertSame("Crossfade must reuse the same AudioTrack",outputBefore,trackField.get(controller))
            assertTrue(controller.playbackQueue.value.isEmpty())
            assertEquals(30,controller.timerMinutes.value);assertEquals(5,controller.switchMinutes.value)
            instrumentation.runOnMainSync {controller.stop()}
            await {manager.activeNotifications.none {it.id==13}}

        } finally {
            instrumentation.runOnMainSync {controller.stop();OndaStore.saveSettings(before)}
            scenario.close();source.delete()
        }
    }
    @Test fun backgroundIsExplicitAndPersistent() {
        assertFalse(OndaStore.defaults().optBoolean("jukebox_background"))
        assertTrue(categories.getValue("Áudio").contains("jukebox_background"))
    }
}
