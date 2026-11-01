package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class AndroidResponsivenessTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun queuePositionCacheScansOnceAndTracksMovesAndCurrentIdentity() {
        val data=(0 until 5000).map {JSONObject().put("_queue_id",it.toString())}
        var reads=0
        val rows=object:AbstractList<JSONObject>() {
            override val size:Int get()=data.size
            override fun get(index:Int):JSONObject {reads++;return data[index]}
        }
        val cache=PlaybackQueueIndex()
        assertEquals(4999,cache.index(rows,"4999"));val first=reads
        repeat(1000){assertEquals(4999,cache.index(rows,"4999"))}
        assertEquals(first,reads)
        assertEquals(0,cache.index(rows,"0"))
        assertEquals(0,cache.index(rows.reversed(),"4999"))
        assertEquals(-1,cache.index(emptyList(),"4999"))
    }

    @Test fun remoteClockUpdatesOnlyTheClockAndKeepsActualPosition() {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val previous=RemotePlaybackRuntime.state.value
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        var renders=0
        try {
            compose.runOnUiThread {
                vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
                RemotePlaybackRuntime.state.value=RemotePlaybackState(connected=true,online=true,ready=true,title="Remote fixture",trackId="fixture",position=75.0,duration=180.0)
            }
            compose.setContent {MaterialTheme {
                val metadata by RemotePlaybackRuntime.presentationState.collectAsStateWithLifecycle()
                SideEffect {renders++}
                RemotePlaybackSurface(metadata,vm,false)
            }}
            compose.onNodeWithText("1:15").assertExists()
            compose.runOnIdle {renders=0;RemotePlaybackRuntime.state.value=RemotePlaybackRuntime.state.value.copy(position=90.0,receivedAt=10L)}
            compose.waitForIdle()
            compose.onNodeWithText("1:30").assertExists()
            compose.runOnIdle {assertEquals(0,renders)}
            compose.onNodeWithText("Remote fixture").performClick()
            compose.onNodeWithTag("remote-player-timeline").assertExists()
            compose.onAllNodesWithText("1:30").assertCountEquals(2)
        } finally {compose.runOnUiThread {RemotePlaybackRuntime.state.value=previous;store.clear()}}
    }

    @Test fun localQueueClockDoesNotReadTheWholeTrackCardAgain() {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val saved=PlaybackSessions.load(context,"jukebox")
        val remote=RemotePlaybackRuntime.state.value
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        var reads=0
        val record=object:JSONObject() {
            override fun optString(name:String):String {if(name=="title")reads++;return super.optString(name)}
        }.put("_queue_id","fixture").put("title","Local fixture").put("artists",JSONArray(listOf("Artist"))).put("duration_ms",3000)
        try {
            compose.runOnUiThread {
                RemotePlaybackRuntime.state.value=RemotePlaybackState()
                vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
                vm.jukebox.stop();vm.jukebox.clearPlaybackQueue()
                vm.jukebox.playbackQueue.value=listOf(record);vm.jukebox.currentQueueId.value="fixture"
                vm.jukebox.state.value=JukeboxState(title="Local fixture",model=JSONObject().put("source","fixture").put("duration",3).put("beats",JSONArray(listOf(0,1,2,3))))
            }
            compose.setContent {MaterialTheme {PlaybackQueuePage(vm)}}
            compose.waitForIdle();compose.runOnIdle {reads=0}
            repeat(10) {step->
                compose.runOnIdle {vm.jukebox.state.value=vm.jukebox.state.value.copy(phase=step/10f,elapsed=step/10.0)}
                compose.waitForIdle()
            }
            compose.onNodeWithTag("queue-current-cover-progress",useUnmergedTree=true).assertExists()
            compose.runOnIdle {assertEquals(0,reads)}
        } finally {compose.runOnUiThread {store.clear();RemotePlaybackRuntime.state.value=remote;if(saved!=null)PlaybackSessions.save(context,"jukebox",saved,true)}}
    }
}
