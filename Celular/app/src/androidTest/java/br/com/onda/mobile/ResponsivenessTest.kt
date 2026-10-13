package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ResponsivenessTest {
    @Test fun progressBurstIsBoundedButFinalEventIsImmediate() {
        var time=0L
        val gate=ProgressGate(150) {time}
        assertTrue(gate.allow())
        repeat(149) {time++;assertFalse(gate.allow())}
        time=150;assertTrue(gate.allow())
        time=151;assertTrue(gate.allow(force=true))
        assertFalse(gate.allow())
        time=301;assertTrue(gate.allow())
    }
    @Test fun notificationGateLimitsCombinedWorkers() {
        var time=0L
        val gate=ProgressGate(500) {time}
        assertEquals(1,(1..4).count {gate.allow()})
        time=499;assertFalse(gate.allow())
        time=500;assertEquals(1,(1..4).count {gate.allow()})
        assertTrue(gate.allow(force=true))
    }
}
