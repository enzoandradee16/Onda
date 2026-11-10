package br.com.onda.mobile

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class JukeboxQueuePreparationTest {
    @Test fun searchSelectionKeepsCurrentPlayingDuringPreparationAndFailure()=runBlocking {
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        withContext(Dispatchers.Main){OndaStore.initialize(context)}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val started=CompletableDeferred<Unit>()
        val release=CompletableDeferred<Unit>()
        val current=JSONObject().put("title","Current")
        val controller=JukeboxController(context,scope,{}, {_,config,_->
            assertEquals("Selected",config.getJSONObject("record").getString("title"))
            started.complete(Unit)
            release.await()
            error("Preparation failed")
        })
        try {
            withContext(Dispatchers.Main){
                controller.stop();controller.clearPlaybackQueue()
                controller.playbackQueue.value=listOf(JSONObject().put("_queue_id","current").put("_analysis","Erro").put("title","Current"))
                controller.currentQueueId.value="current"
                controller.state.value=JukeboxState(title="Current",model=current,playing=true)
                controller.playRecord(JSONObject().put("title","Selected").put("source_url","https://example.com/selected"))
            }
            withTimeout(5000){started.await()}
            assertSame(current,controller.state.value.model)
            assertTrue(controller.state.value.playing)
            assertEquals("current",controller.currentQueueId.value)
            assertEquals("Selected",controller.playbackQueue.value[1].getString("title"))
            release.complete(Unit)
            withTimeout(5000){while(controller.playbackQueue.value[1].optString("_analysis")!="Erro")delay(20)}
            assertSame(current,controller.state.value.model)
            assertTrue(controller.state.value.playing)
        } finally {withContext(Dispatchers.Main){controller.close()};scope.cancel()}
    }

    @Test fun preparesQueueSeriallyWithoutReplacingTheCurrentSongAndKeepsTimersIndependent()=runBlocking {
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        var calls=0;var active=0;var peak=0
        val current=JSONObject().put("title","Current")
        val controller=JukeboxController(ApplicationProvider.getApplicationContext(),scope,{}, {action,config,_->
            assertEquals("jukebox_prepare",action)
            calls++;active++;peak=maxOf(peak,active);delay(30);active--
            JSONObject().put("media_title",config.getJSONObject("record").optString("title"))
        })
        try {
            withContext(Dispatchers.Main){
                controller.clearPlaybackQueue();controller.effects.value=JSONObject().put("enabled",false)
                controller.state.value=JukeboxState(title="Current",model=current)
                controller.enqueue(JSONObject().put("title","First"))
                controller.enqueue(JSONObject().put("title","Second"))
                controller.setTimer(30);controller.setTimer(5,true)
                assertEquals(30,controller.timerMinutes.value);assertEquals(5,controller.switchMinutes.value)
                controller.setTimer(0,true)
                assertEquals(30,controller.timerMinutes.value)
            }
            withTimeout(5000){while(controller.playbackQueue.value.any {it.optString("_analysis")!="Pronta"})delay(20)}
            assertEquals(2,calls);assertEquals(1,peak)
            assertSame(current,controller.state.value.model)
            assertEquals(listOf("First","Second"),controller.playbackQueue.value.map {it.optString("title")})
        } finally {withContext(Dispatchers.Main){controller.close()};scope.cancel()}
    }
    @Test fun reorderAndManualInsertionRetargetPreparation()=runBlocking {
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        withContext(Dispatchers.Main){OndaStore.initialize(context)}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val firstStarted=CompletableDeferred<Unit>();val firstCancelled=CompletableDeferred<Unit>()
        val controller=JukeboxController(context,scope,{}, {_,config,_->
            val title=config.getJSONObject("record").getString("title")
            if(title=="First") {
                firstStarted.complete(Unit)
                try {awaitCancellation()} finally {firstCancelled.complete(Unit)}
            }
            delay(30)
            JSONObject().put("media_title",title)
        })
        try {
            withContext(Dispatchers.Main){
                controller.stop();controller.clearPlaybackQueue();controller.effects.value=JSONObject().put("enabled",false)
                controller.enqueueAll(listOf("First","Second","Third").map {JSONObject().put("title",it)})
            }
            withTimeout(5000){firstStarted.await()}
            withContext(Dispatchers.Main){controller.moveQueued(2,-2);controller.enqueue(JSONObject().put("title","Manual"))}
            withTimeout(5000){firstCancelled.await();while(controller.playbackQueue.value.take(2).any {it.optString("_analysis")!="Pronta"})delay(30)}
            assertEquals(listOf("Manual","Third"),controller.playbackQueue.value.take(2).map {it.optString("title")})
            assertEquals("0:10",exportPositionText("10"));assertEquals("1:05",exportPositionText("65"));assertEquals("1:00:00",exportPositionText("3600"))
        } finally {withContext(Dispatchers.Main){controller.close()};scope.cancel()}
    }

    @Test fun failedTrackSelectionStartsAfterPreparationWithoutSecondTap()=runBlocking {
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        withContext(Dispatchers.Main){OndaStore.initialize(context)}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val release=CompletableDeferred<Unit>()
        val opened=CompletableDeferred<Unit>()
        val cache=java.io.File(context.cacheDir,"queue-retry-${System.nanoTime()}").apply {mkdirs()}
        java.io.File(cache,"analysis.json").writeText("{}")
        val model=JSONObject().put("cache",cache.absolutePath).put("media_title","Selected").put("duration",20)
        val controller=JukeboxController(context,scope,{}, {action,_,_->
            when(action) {
                "jukebox_prepare"->{release.await();model}
                "jukebox_open"->{opened.complete(Unit);awaitCancellation()}
                else->JSONObject()
            }
        })
        try {
            withContext(Dispatchers.Main){
                controller.playbackQueue.value=listOf(JSONObject().put("_queue_id","selected").put("title","Selected").put("_analysis","Erro"))
                controller.playQueued(0)
                assertEquals("selected",controller.pendingPlaybackId.value)
            }
            release.complete(Unit)
            withTimeout(5000){opened.await()}
            assertEquals("selected",controller.currentQueueId.value)
            assertTrue(controller.state.value.playing)
            assertEquals("",controller.pendingPlaybackId.value)
        } finally {
            withContext(Dispatchers.Main){controller.close()}
            scope.cancel();cache.deleteRecursively()
        }
    }
}
