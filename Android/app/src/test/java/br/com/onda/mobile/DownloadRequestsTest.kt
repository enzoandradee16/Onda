package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.Executors

class DownloadRequestsTest {
    @Test fun immediateRequestsExtendScopeWithoutIncludingUnrequestedItems() {
        val pending=DownloadRequests()
        val selection=DownloadScope()
        pending.submit("first")
        selection.include(pending.poll()!!)
        pending.submit("second")
        selection.include(pending.poll()!!)
        assertTrue(selection.accepts("first"))
        assertTrue(selection.accepts("second"))
        assertFalse(selection.accepts("unrequested"))
    }
    @Test fun requestArrivingAfterLastPollRemainsForNextRunner() {
        val pending=DownloadRequests()
        assertNull(pending.poll())
        pending.submit("late")
        assertTrue(pending.hasPending())
        assertEquals(setOf("late"),pending.poll()!!.ids)
        assertFalse(pending.hasPending())
    }
    @Test fun batchAndGlobalQueueRequestsKeepTheirMeaning() {
        val selection=DownloadScope()
        selection.include(DownloadRequest(setOf("a","b")))
        assertFalse(selection.accepts("c"))
        selection.include(DownloadRequest(null))
        assertTrue(selection.accepts("c"))
    }
    @Test fun concurrentSubmissionsAreNotLost() {
        val pending=DownloadRequests()
        val executor=Executors.newFixedThreadPool(4)
        try {
            (1..64).map {id->executor.submit {pending.submit(id.toString())}}.forEach {it.get()}
            val received=mutableSetOf<String>()
            while(true){val request=pending.poll() ?: break;received.addAll(request.ids!!)}
            assertEquals((1..64).map {it.toString()}.toSet(),received)
        } finally {executor.shutdownNow()}
    }
    @Test fun stoppingDiscardsUnstartedRequests() {
        val pending=DownloadRequests()
        pending.submit("before-stop")
        pending.clear()
        assertFalse(pending.hasPending())
        pending.submit("after-stop")
        assertEquals(setOf("after-stop"),pending.poll()!!.ids)
    }
}
