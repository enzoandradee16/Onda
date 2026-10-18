package br.com.onda.mobile
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class QueueControlsTest {
    private fun item(id:String,seconds:Int?,state:String="Pendente")=DownloadItem(id,id,JSONObject().put("mode","mp3").put("audio_quality","320 kbps").put("queue_info",JSONObject().apply {if(seconds!=null)put("duration_ms",seconds*1000)}),state)
    @Test fun sortingAndMovingPreserveActiveSlotsAndUnknowns() {
        val rows=listOf(item("A",20),item("busy",10,"Baixando"),item("B",3),item("unknown",null))
        assertEquals(listOf("B","A","unknown"),orderedPending(rows,"Menor duração",rows.map {it.id}))
        assertEquals(listOf("A","B","unknown"),orderedPending(rows,"Maior duração",rows.map {it.id}))
        assertEquals(listOf("unknown","busy","B","A"),pendingOrder(rows,listOf("unknown","B","A"))!!.map {it.id})
        assertNull(pendingOrder(rows,listOf("A","A","unknown")))
        assertNull(pendingOrder(rows,listOf("busy","B","unknown")))
    }
    @Test fun spaceEstimatesAndWaitReasonsAreExplicit() {
        assertTrue(queueBytes(item("A",10))!!>400000)
        assertNull(queueBytes(item("unknown",null)))
        assertTrue(QueueSpace(100,2,300,200,1000).low)
        assertTrue(QueueSpace(100,2,300,null,200).low)
        assertFalse(QueueSpace(100,2,300,null,1000).low)
        val settings=JSONObject().put("schedule_enabled",false)
        assertEquals("Aguardando vaga",queueActivity(item("A",10),true,settings,true))
        assertEquals("Sem conexão",queueActivity(item("A",10),false,settings,false))
        assertEquals("Aguardando sua escolha",queueActivity(item("A",10,"Aguardando escolha"),true,settings,true))
    }
}
