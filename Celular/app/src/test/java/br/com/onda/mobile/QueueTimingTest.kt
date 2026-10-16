package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class QueueTimingTest {
    @Test fun waitsForCompletionThenUsesWholeQueueRate() {
        var time=0.0;val clock=QueueTiming {time}
        assertEquals(QueueTimes(0,null),clock.snapshot(4))
        clock.setRunning(true);time=20.0
        assertEquals(QueueTimes(20,null),clock.snapshot(4))
        clock.recordCompletion();assertEquals(QueueTimes(20,60),clock.snapshot(3))
    }
    @Test fun excludesPauseAndKeepsPriorActiveTime() {
        var time=0.0;val clock=QueueTiming {time}
        clock.setRunning(true);time=10.0;clock.recordCompletion();clock.setRunning(false)
        time=100.0;assertEquals(QueueTimes(10,null),clock.snapshot(3))
        clock.setRunning(true);time=110.0;assertEquals(QueueTimes(20,60),clock.snapshot(3))
    }
    @Test fun accountsForParallelismThroughObservedCompletions() {
        var time=0.0;val clock=QueueTiming {time}
        clock.setRunning(true);time=10.0;repeat(4) {clock.recordCompletion()}
        assertEquals(QueueTimes(10,20),clock.snapshot(8))
        assertEquals(QueueTimes(10,10),clock.snapshot(4))
    }
    @Test fun oldCompletionsAndEmptyQueueDoNotSkewRate() {
        var time=0.0;val clock=QueueTiming {time}
        clock.recordCompletion();clock.setRunning(true);time=10.0
        assertEquals(QueueTimes(10,null),clock.snapshot(4))
        assertEquals(QueueTimes(10,0),clock.snapshot(0))
        clock.reset();assertEquals(QueueTimes(0,null),clock.snapshot(0,false))
    }
    @Test fun formatsMinutesAndHours() {
        assertEquals("01:05",queueDuration(65));assertEquals("01:01:01",queueDuration(3661));assertEquals("00:00",queueDuration(-1))
    }
}
