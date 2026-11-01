package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class StableListIdentityTest {
    @Test fun reorderAndUnrelatedRemovalKeepIdentity() {
        val before=occurrenceKeys(listOf("a","b","c"))
        assertEquals(listOf(before[2],before[0]),occurrenceKeys(listOf("c","a")))
    }
    @Test fun duplicateTracksHaveDistinctKeys() {
        val keys=occurrenceKeys(listOf("a","a","b"))
        assertEquals(3,keys.toSet().size)
        assertEquals(keys,occurrenceKeys(listOf("a","a","b")))
    }
}
