package br.com.onda.mobile

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.io.File

class PlaybackSessionFeaturesTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun shuffleControlHasOnlyAnIconAndCanBeToggled() {
        val checked=androidx.compose.runtime.mutableStateOf(false)
        compose.setContent {MaterialTheme {ShufflePlaybackButton(checked.value,{checked.value=it})}}
        compose.onNodeWithTag("playback-shuffle").assertIsOff().performClick().assertIsOn()
        compose.onNodeWithContentDescription("Reprodução aleatória").assertExists()
        compose.onAllNodesWithText("Reprodução aleatória").assertCountEquals(0)
    }
    @Test fun bothSessionsRestoreQueuesAndPositionWithNoPlayback()=runBlocking {
        OndaStore.initialize(context)
        val preferences=context.getSharedPreferences("playback-sessions",0)
        val oldEffects=preferences.getString("effects",null);val oldJuke=preferences.getString("jukebox",null)
        val folder=File(context.cacheDir,"restore-session-${System.nanoTime()}").apply {mkdirs()}
        val source=File(folder,"song.wav").apply {writeBytes(byteArrayOf(0))}
        File(folder,"analysis.json").writeText("{}")
        val model=JSONObject().put("title","Restored Jukebox").put("cache",folder.absolutePath).put("source",source.absolutePath).put("beats",JSONArray(listOf(0,1,2,3)))
        PlaybackSessions.save(context,"effects",JSONObject().put("source",source.absolutePath).put("duration",120).put("position",42).put("queue",JSONArray().put(source.absolutePath)).put("speed",75).put("reverb",10).put("pitch",true).put("mode",0).put("shuffle",true))
        PlaybackSessions.save(context,"jukebox",JSONObject().put("queue",JSONArray().put(JSONObject().put("_queue_id","active").put("title","Restored Jukebox"))).put("current","active").put("model",model).put("index",1).put("phase",.5).put("normal",true).put("shuffle",true))
        val store=ViewModelStore();val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        var calls=0
        try {
            withContext(Dispatchers.Main) {
                val controller=JukeboxController(context,scope,{}, {_,_,_->calls++;JSONObject()})
                assertFalse(controller.state.value.playing);assertFalse(controller.state.value.busy)
                assertEquals("active",controller.currentQueueId.value);assertEquals(1,controller.state.value.index)
                assertEquals(.5f,controller.state.value.phase);assertTrue(controller.normal)
                assertTrue(controller.queueShuffle.value);assertEquals(0,calls)
                val vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
                assertEquals(source.absolutePath,vm.effectsSource.value);assertEquals(42.0,vm.effectsPosition.value,0.0)
                assertEquals(listOf(source.absolutePath),vm.effectsPlaylist.value)
                assertEquals(Triple(75,10,true),vm.effectsControlSnapshot())
                assertFalse(vm.effectsPreviewEnabled.value);assertFalse(vm.player.isPlaying)
                assertTrue(vm.effectsShuffle.value)
                store.clear();controller.close()
                val saved=PlaybackSessions.load(context,"jukebox")!!
                assertEquals(1.5,saved.getDouble("seconds"),0.0)
                assertFalse(saved.optBoolean("playing"))
                File(folder,"analysis.json").delete()
                val restored=JukeboxController(context,scope,{}, {_,_,_->calls++;JSONObject()})
                assertEquals(1.5,restored.playbackQueue.value.first().getDouble("_restore_seconds"),0.0)
                assertFalse(restored.state.value.playing)
                restored.savePlaybackSession(synchronous=true)
                assertEquals(1.5,PlaybackSessions.load(context,"jukebox")!!.getDouble("seconds"),0.0)
                assertEquals(0,calls);restored.close()
            }
        } finally {
            scope.cancel()
            preferences.edit().apply {if(oldEffects==null)remove("effects") else putString("effects",oldEffects);if(oldJuke==null)remove("jukebox") else putString("jukebox",oldJuke)}.commit()
            source.delete();File(folder,"analysis.json").delete();folder.delete()
        }
    }
    @Test fun replacingFailedLinkPreservesIdentityAndDownloadOptions() {
        OndaStore.initialize(context)
        val id=OndaStore.enqueue("https://example.com/old","Old",extra=JSONObject().put("queue_info",JSONObject().put("title","Old")))
        try {
            OndaStore.update(id,"Erro",message="HTTP 404")
            val mode=OndaStore.items.value.first {it.id==id}.config.optString("mode")
            assertFalse(OndaStore.replaceDownloadLink(id,"file:///private/file"))
            assertTrue(OndaStore.replaceDownloadLink(id,"https://example.com/new"))
            val item=OndaStore.items.value.first {it.id==id}
            assertEquals("https://example.com/new",item.config.optString("url"));assertEquals(mode,item.config.optString("mode"))
            assertEquals("Pendente",item.state);assertFalse(item.config.has("queue_info"))
        } finally {OndaStore.remove(setOf(id))}
    }
    @Test fun compactBarsKeepShuffleIndependentForEffectsAndJukebox() {
        OndaStore.initialize(context)
        val store=ViewModelStore()
        val file=File(context.cacheDir,"shuffle-fixture-${System.nanoTime()}.wav").apply {writeBytes(byteArrayOf(0))}
        lateinit var vm:OndaViewModel
        compose.runOnIdle {
            vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
            vm.selectEffectsSource(file.absolutePath,120.0);vm.effectsSource.value=file.absolutePath
            vm.effectsInfo.value=mapOf(file.absolutePath to JSONObject().put("duration",120).put("record",JSONObject().put("title","Effects fixture")))
            vm.effectsShuffle.value=false;vm.jukebox.queueShuffle.value=false;vm.playbackMode.value=0
        }
        val old=vm.jukebox.state.value
        try {
            compose.setContent {MaterialTheme {AndroidPlaybackSurface(vm)}}
            compose.onNodeWithTag("playback-shuffle").assertIsOff().performClick().assertIsOn()
            assertTrue(vm.effectsShuffle.value);assertFalse(vm.jukebox.queueShuffle.value)
            compose.runOnIdle {
                vm.jukebox.state.value=JukeboxState(title="Jukebox fixture",model=JSONObject().put("source",file.absolutePath).put("duration",120))
                vm.playbackMode.value=1
            }
            compose.onNodeWithTag("playback-shuffle").assertIsOff().performClick().assertIsOn()
            assertTrue(vm.effectsShuffle.value);assertTrue(vm.jukebox.queueShuffle.value)
            compose.onAllNodesWithText("Reprodução aleatória").assertCountEquals(0)
        } finally {compose.runOnIdle {vm.jukebox.state.value=old;store.clear()};file.delete()}
    }
}
