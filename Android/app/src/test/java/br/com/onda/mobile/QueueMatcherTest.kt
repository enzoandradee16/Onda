package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class QueueMatcherTest {
    @Test fun preparesAccentInsensitiveTermsOnce() {
        val matcher=QueueMatcher("  ANTÔNIO   Álbum  ","Todos")
        assertEquals(listOf("antonio","album"),matcher.terms)
        assertTrue(QueueMatcher("   ","Pendentes").terms.isEmpty())
    }
}
