package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class FailureSummaryTest {
    @Test fun onlyFailedAttemptsAreReported() {
        val rows=listOf("old" to "Erro","failed" to "Erro","done" to "Concluído","cancelled" to "Pendente")
        assertEquals(listOf("failed"),finishedFailureIds(setOf("failed","done","cancelled"),rows,true))
    }
    @Test fun interruptedAndSuccessfulRunsHaveNoSummary() {
        assertTrue(finishedFailureIds(setOf("a"),listOf("a" to "Erro"),false).isEmpty())
        assertTrue(finishedFailureIds(setOf("a"),listOf("a" to "Concluído"),true).isEmpty())
    }
    @Test fun catalogUrlsAreRestrictedToPublicTracks() {
        listOf("https://www.deezer.com/track/123","https://deezer.com/track/123","https://music.apple.com/us/song/123").forEach {assertTrue(it,validFailureCatalogUrl(it))}
        listOf("http://deezer.com/track/123","https://evil.com/track/123","https://www.deezer.com/album/123","https://www.deezer.com.evil.com/track/123","https://user@deezer.com/track/123").forEach {assertFalse(it,validFailureCatalogUrl(it))}
    }
    @Test fun largeSummaryPreservesQueueOrder() {
        val rows=(0 until 1300).map {it.toString() to if(it%3==0)"Erro" else "Concluído"}
        assertEquals((0 until 1300 step 3).map {it.toString()},finishedFailureIds(rows.map {it.first}.toSet(),rows,true))
    }
}
