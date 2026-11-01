package br.com.onda.mobile

import android.util.Base64
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class PerformancePathsTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun jsonSnapshotsOwnNestedValuesWithoutReencodingArtwork() {
        val artwork="x".repeat(1000000)
        val original=JSONObject().put("cover",artwork).put("nested",JSONObject().put("title","Before"))
            .put("artists",JSONArray().put("Artist"))
        val copy=copyJsonObject(original)
        assertSame(artwork,copy.getString("cover"))
        copy.getJSONObject("nested").put("title","After")
        copy.getJSONArray("artists").put("Second")
        assertEquals("Before",original.getJSONObject("nested").getString("title"))
        assertEquals(1,original.getJSONArray("artists").length())
    }

    @Test fun downloadSelectionMatchesOnlySelectedCompletedAudioInHistoryOrder() {
        val queue=listOf(
            DownloadItem("one","One",JSONObject().put("url","https://www.deezer.com/track/1").put("mode","mp3"),"Concluído"),
            DownloadItem("two","Two",JSONObject().put("url","https://www.deezer.com/track/2").put("mode","flac"),"Pendente"),
            DownloadItem("three","Three",JSONObject().put("url","https://www.deezer.com/track/3").put("mode","mp3"),"Concluído")
        )
        val source=jobSource(queue[0].config)
        val history=listOf(
            HistoryItem(1,"One.mp3","content://one","MP3",100,source=source),
            HistoryItem(2,"Other.mp3","content://other","mp3",100,source=jobSource(queue[2].config)),
            HistoryItem(3,"One video.mp4","content://video","MP3",100,source=source),
            HistoryItem(4,"One.mp3","content://one","mp3",100,source=source)
        )
        assertTrue(downloadMetadataUris(queue,emptySet(),history).isEmpty())
        assertEquals(listOf("content://one"),downloadMetadataUris(queue,setOf("one","two"),history))
    }

    @Test fun equalizerGainIsBitExactOnAndroid() {
        MobileEngine.initialize(context)
        val report=JSONObject(Python.getInstance().getModule("playback_continuity_smoke").callAttr("verify_equalizer_gain").toString())
        assertTrue(report.getBoolean("bit_exact"))
        assertEquals(65536,report.getInt("samples"))
    }

    @Test fun rawPcmMatchesLegacyBytesWithoutEncodingAudioInJson() {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val report=JSONObject(Python.getInstance().getModule("playback_continuity_smoke").callAttr("verify").toString())
        val session="raw-pcm-parity"
        fun call(action:String,config:JSONObject)=MobileEngine.call(context,"parity-$action",action,config,EventCallback {})
        val config=JSONObject().put("session",session).put("normal",true).put("volume",100).put("smooth",0).put("seek",0)
        try {
            call("jukebox_open",JSONObject().put("session",session).put("cache",report.getString("cache")))
            val legacy=call("jukebox_chunk",config)
            val packet=MobileEngine.pcmChunk(context,"parity-raw",config)
            assertFalse(packet.first.has("pcm"))
            assertArrayEquals(Base64.decode(legacy.getString("pcm"),Base64.NO_WRAP),packet.second)
            assertEquals(legacy.getDouble("seconds"),packet.first.getDouble("seconds"),0.0)
        } finally {call("jukebox_close",JSONObject().put("session",session))}
    }

    @Test fun clocksDoNotRepublishMetadataAndSessionStoresOnlyCacheReference() {
        OndaStore.initialize(context)
        val previous=PlaybackSessions.load(context,"jukebox")
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        lateinit var controller:JukeboxController
        var emissions=0
        compose.runOnUiThread {
            controller=JukeboxController(context,scope,{})
            controller.clearPlaybackQueue()
            controller.state.value=JukeboxState(title="Clock fixture",model=JSONObject().put("cache","fixture-cache").put("title","Clock fixture").put("beats",JSONArray(listOf(0,1,2))).put("neighbors",JSONArray().put(JSONArray()).put(JSONArray())))
        }
        compose.setContent {MaterialTheme {androidx.compose.material3.Text("Fixture")}}
        lateinit var observer:Job
        compose.runOnUiThread {observer=scope.launch {controller.presentationState.collect {emissions++}}}
        compose.waitForIdle()
        try {
            compose.runOnIdle {emissions=0;repeat(100){controller.state.value=controller.state.value.copy(phase=it/100f,elapsed=it/10.0)}}
            compose.waitForIdle()
            compose.runOnIdle {
                assertEquals(0,emissions)
                assertTrue(controller.state.value.phase>0f)
                controller.savePlaybackSession(synchronous=true)
                val saved=PlaybackSessions.load(context,"jukebox")!!
                assertFalse(saved.getJSONObject("model").has("beats"))
                assertEquals("fixture-cache",saved.getJSONObject("model").getString("cache"))
            }
        } finally {compose.runOnUiThread {observer.cancel();controller.close();scope.cancel();if(previous!=null)PlaybackSessions.save(context,"jukebox",previous,true)}}
    }
}
