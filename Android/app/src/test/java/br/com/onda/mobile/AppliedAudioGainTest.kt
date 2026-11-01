package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class AppliedAudioGainTest {
    @Test fun unchangedGainWritesOnceButNewOutputAndChangesWriteImmediately() {
        val cache=AppliedAudioGain();val output=Any();var writes=0
        repeat(1000){cache.apply(output,.5f){writes++;0}}
        assertEquals(1,writes)
        cache.apply(output,.25f){writes++;0};assertEquals(2,writes)
        val next=Any();cache.apply(next,.25f){writes++;0};assertEquals(3,writes)
        cache.clear(output)
        cache.apply(next,.25f){writes++;0};assertEquals(3,writes)
        cache.clear();cache.apply(next,.25f){writes++;0};assertEquals(4,writes)
    }
    @Test fun failedWritesRetryInsteadOfCachingAnUnappliedGain() {
        val cache=AppliedAudioGain();val output=Any();var writes=0
        cache.apply(output,.5f){writes++;-1}
        cache.apply(output,.5f){writes++;0}
        cache.apply(output,.5f){writes++;0}
        assertEquals(2,writes)
    }
}
