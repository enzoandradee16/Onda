package br.com.onda.mobile

import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

class PlaybackSessionWritesTest {
    private val tasks = mutableListOf<Runnable>()
    private val errors = mutableListOf<Exception>()
    private val writer = PlaybackSessionWrites(Executor { tasks.add(it) }, errors::add)

    @Test fun minimizingQueuesDiskIoAndKeepsTheLatestPositionReadableImmediately() {
        val disk = mutableListOf<String>()
        writer.save("jukebox", "position:10", false, disk::add)
        writer.save("jukebox", "position:15", false, disk::add)
        assertTrue(disk.isEmpty())
        assertEquals("position:15", writer.latest("jukebox"))
        tasks.forEach { it.run() }
        assertEquals(listOf("position:15"), disk)
        assertNull(writer.latest("jukebox"))
    }

    @Test fun aSynchronousRestartSaveCannotBeOverwrittenByAnOlderQueuedSave() {
        val disk = mutableListOf<String>()
        writer.save("jukebox", "old", false, disk::add)
        writer.save("jukebox", "latest", true, disk::add)
        tasks.forEach { it.run() }
        assertEquals(listOf("latest"), disk)
    }

    @Test fun diskFailureDoesNotCrashLifecycleAndRetainsThePositionForRetry() {
        writer.save("jukebox", "position:20", false) { throw IllegalStateException("disk full") }
        tasks.removeAt(0).run()
        assertEquals(1, errors.size)
        assertEquals("position:20", writer.latest("jukebox"))
        var retried = ""
        writer.save("jukebox", "position:20", false) { retried = it }
        tasks.removeAt(0).run()
        assertEquals("position:20", retried)
        assertNull(writer.latest("jukebox"))
    }

    @Test fun explicitRestartStillReportsPersistenceFailure() {
        try {
            writer.save("jukebox", "position:30", true) { throw IllegalStateException("disk full") }
            fail("An explicit restart requires a successful disk save")
        } catch (error: IllegalStateException) {
            assertEquals("disk full", error.message)
        }
    }
}
