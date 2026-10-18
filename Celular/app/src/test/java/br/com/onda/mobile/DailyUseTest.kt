package br.com.onda.mobile
import org.junit.Assert.*
import org.junit.Test
class DailyUseTest {
    @Test fun wifiAndExplicitPause() {
        assertEquals(QueueGate.WIFI,queueGate(true,false,true,false))
        assertEquals(QueueGate.WIFI,queueGate(true,false,false,true))
        assertEquals(QueueGate.RUN,queueGate(true,false,true,true))
        assertEquals(QueueGate.RUN,queueGate(false,false,true,false))
        assertEquals(QueueGate.PAUSE,queueGate(true,true,true,true))
    }
    @Test fun lossBehaviorAndPauseDiffer() {
        assertTrue(interruptForGate(QueueGate.WIFI,"Pausar downloads"))
        assertFalse(interruptForGate(QueueGate.WIFI,"Concluir downloads ativos"))
        assertTrue(interruptForGate(QueueGate.PAUSE,"Concluir downloads ativos"))
        assertFalse(interruptForGate(QueueGate.RUN,"Pausar downloads"))
    }
    @Test fun completedFilesAreNotRepeatedButInterruptedOnesReturnToPending() {
        assertTrue(interruptedDownload(false,true,true,true,-1))
        assertTrue(interruptedDownload(false,false,true,true,-1))
        assertFalse(interruptedDownload(false,false,true,false,0))
        assertFalse(interruptedDownload(false,false,false,true,1))
        assertTrue(interruptedDownload(true,false,false,false,0))
    }
    @Test fun optionalNotificationButtons() {
        assertTrue(notificationActions(false,false).isEmpty())
        assertEquals(listOf("Pausar fila","Parar fila","Abrir fila"),notificationActions(true,false))
        assertEquals(listOf("Retomar fila","Parar fila","Abrir fila"),notificationActions(true,true))
    }
}
