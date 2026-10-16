package br.com.onda.mobile
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class QueueFilterTest {
    @Test fun searchAndStateCanBeCombinedWithoutChangingQueueData() {
        val record=JSONObject().put("artists","Antônio Carlos Jobim").put("album","Wave").put("platform","Spotify")
        val config=JSONObject().put("queue_info",record)
        val original=config.toString()
        assertTrue(queueMatches("Garota de Ipanema","Pendente",config,"antonio wave","Pendentes"))
        assertFalse(queueMatches("Garota de Ipanema","Erro",config,"antonio wave","Pendentes"))
        assertTrue(queueMatches("Garota de Ipanema","Erro",config,"spotify","Com falha"))
        assertFalse(queueMatches("Garota de Ipanema","Pendente",config,"not found","Todos"))
        assertTrue(queueMatches("トーキョー","Baixando",config,"トーキョー","Em andamento"))
        assertEquals(original,config.toString())
    }
}
