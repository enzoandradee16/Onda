package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class WorkflowStatusTest {
    @Test fun toolDatesUseDeviceZoneAndRejectInvalidTimestamps() {
        val date=toolDateText("2026-10-27T23:38:29+00:00","pt-BR",java.time.ZoneId.of("America/Sao_Paulo"))
        assertTrue(date,date.contains("20:38"))
        assertFalse(date,date.contains("T23"))
        assertEquals("—",toolDateText("invalid","en"))
    }
    @Test fun statesHaveCommonLabelsWithoutChangingDatabaseValues() {
        assertEquals(workflowLabel("Na fila"),workflowLabel("Pendente"))
        assertEquals(workflowLabel("Falhou"),workflowLabel("Erro"))
        assertEquals("Pronta para reproduzir",workflowLabel("Pronta",true))
        assertEquals("Aguardando preparação",workflowLabel("Pendente",true))
    }
    @Test fun completedTasksCannotBeRetriedAndPausedTasksCanResume() {
        assertFalse(canQueueAction("Concluído","retry"))
        assertFalse(canQueueAction("Erro","pause"))
        assertTrue(canQueueAction("Erro","retry"))
        assertTrue(canQueueAction("Pausado","resume"))
    }
}
