package br.com.onda.mobile

import org.junit.Assert.assertEquals
import org.junit.Test

class DownloadFeedbackTest {
    @Test fun probableCausesOfferRelevantActions() {
        assertEquals("Verificar acesso",failureAdvice("HTTP 403 Forbidden").second)
        assertEquals("Atualizar link",failureAdvice("HTTP 404 Not found").second)
        assertEquals("Tentar novamente",failureAdvice("Connection timeout").second)
        assertEquals("Tentar novamente",failureAdvice("Unknown failure").second)
    }
}
