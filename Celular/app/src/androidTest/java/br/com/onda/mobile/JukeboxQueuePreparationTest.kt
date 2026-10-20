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
}
