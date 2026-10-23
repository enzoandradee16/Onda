package br.com.onda.mobile

import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

class PreviewRequestTest {
    @Test fun stoppingInvalidatesEvenANonCooperativeLookup() = runBlocking {
        val cancelled=mutableListOf<String>()
        val request=PreviewRequest(this) {cancelled+=it}
        val release=CompletableDeferred<String>()
        val played=mutableListOf<String>()
        val errors=mutableListOf<Exception>()
        request.start(resolve={withContext(NonCancellable){release.await()}},onResult={played+=it},onError={errors+=it})
        yield();request.cancel();release.complete("old");coroutineContext[Job]!!.children.toList().joinAll()
        assertEquals(1,cancelled.size);assertTrue(played.isEmpty());assertTrue(errors.isEmpty())
    }
    @Test fun olderResultCannotReplaceNewerSelection() = runBlocking {
        val request=PreviewRequest(this) {}
        val old=CompletableDeferred<String>();val current=CompletableDeferred<String>()
        val played=mutableListOf<String>()
        request.start(resolve={withContext(NonCancellable){old.await()}},onResult={played+=it},onError={throw it})
        yield()
        request.start(resolve={current.await()},onResult={played+=it},onError={throw it})
        yield();current.complete("new");yield();old.complete("old");coroutineContext[Job]!!.children.toList().joinAll()
        assertEquals(listOf("new"),played)
    }
    @Test fun lateFailureDoesNotShowAnErrorForAnotherTrack() = runBlocking {
        val request=PreviewRequest(this) {}
        val release=CompletableDeferred<Unit>();val errors=mutableListOf<Exception>()
        request.start(resolve={withContext(NonCancellable){release.await();throw IllegalStateException("old error")}},onResult={fail("Unexpected result")},onError={errors+=it})
        yield();request.cancel();release.complete(Unit);coroutineContext[Job]!!.children.toList().joinAll()
        assertTrue(errors.isEmpty())
    }
    @Test fun currentFailureIsReportedButCancellationIsNot() = runBlocking {
        val request=PreviewRequest(this) {};val errors=mutableListOf<Exception>()
        request.start(resolve={throw IllegalArgumentException("current error")},onResult={fail("Unexpected result")},onError={errors+=it})
        yield();assertEquals("current error",errors.single().message)
        request.start(resolve={throw CancellationException("cancelled")},onResult={fail("Unexpected result")},onError={errors+=it})
        yield();assertEquals(1,errors.size)
    }
}
