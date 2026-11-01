package br.com.onda.mobile

import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File

class PlaybackHandoffTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun portableReferenceKeepsIdentityWithoutPrivatePaths() {
        val input=JSONObject().put("title","私たちを信じていて").put("artists",JSONArray().put("Cindy"))
            .put("album","Angel Touch").put("duration_ms",352000).put("cache","private-cache")
        val exported=handoffRecord(input)!!
        assertEquals("私たちを信じていて",exported.getString("title"))
        assertEquals(352000.0,exported.getDouble("duration_ms"),0.0)
        assertFalse(exported.has("cache"))
        assertNull(handoffRecord(copyJsonObject(input).put("_local_source","/private/song.wav")))
        assertNotNull(handoffRecord(copyJsonObject(input).put("_local_source","/cached/song.wav").put("_catalog_source",true)))
        assertNull(handoffRecord(copyJsonObject(input).put("source_url","https://example.com/audio")))
        assertNull(handoffRecord(copyJsonObject(input).put("artists",JSONArray())))
    }

    @Test fun preparationDoesNotReplaceCurrentSongAndPausedTransferRestoresFractionalPosition()=runBlocking {
        OndaStore.initialize(context)
        val savedSession=PlaybackSessions.load(context,"jukebox")
        val folder=File(context.cacheDir,"handoff-${System.nanoTime()}").apply {mkdirs()}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val model=JSONObject().put("cache",folder.absolutePath).put("source",File(folder,"audio.wav").absolutePath)
            .put("media_title","Destination").put("duration",120).put("beats",JSONArray().put(0).put(30).put(60).put(90).put(120))
        File(folder,"analysis.json").writeText(model.toString())
        var failPreparation=false
        val controller=JukeboxController(context,scope,{},callOverride={action,_,_->
            assertEquals("jukebox_prepare",action)
            if(failPreparation)error("Preparation failed")
            model
        })
        withContext(Dispatchers.Main) {controller.clearPlaybackQueue()}
        val previous=JukeboxState(title="Original",model=JSONObject().put("source","original"),index=2,phase=.5f)
        controller.state.value=previous
        val record=JSONObject().put("title","Destination").put("artists",JSONArray().put("Artist"))
        try {
            val prepared=controller.prepareHandoff(record)
            assertSame(previous,controller.state.value)
            assertTrue(controller.playbackQueue.value.isEmpty())
            failPreparation=true
            try {controller.prepareHandoff(record);fail("Expected preparation failure")}catch(_:IllegalStateException){}
            assertSame(previous,controller.state.value)
            withContext(Dispatchers.Main) {controller.startHandoff(record,prepared,76.25,false)}
            assertFalse(controller.state.value.playing)
            assertEquals("Destination",controller.state.value.title)
            assertEquals(76.25,controller.sessionSeconds(controller.state.value.model,controller.state.value.index,controller.state.value.phase.toDouble()),.001)
            assertEquals(1,controller.playbackQueue.value.size)
        } finally {
            withContext(Dispatchers.Main) {controller.clearPlaybackQueue();controller.close()}
            scope.cancel();folder.deleteRecursively()
            PlaybackSessions.save(context,"jukebox",savedSession ?: JSONObject().put("queue",JSONArray()),synchronous=true)
        }
    }
}
