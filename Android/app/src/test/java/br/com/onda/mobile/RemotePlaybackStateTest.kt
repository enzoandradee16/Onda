package br.com.onda.mobile

import org.junit.Assert.assertEquals
import org.junit.Test

class RemotePlaybackStateTest {
    @Test fun estimatesProgressUsingPcSpeedAndClampsToDuration() {
        val state = RemotePlaybackState(online = true, playing = true, position = 20.0, duration = 100.0, speed = .85f, receivedAt = 10000)
        assertEquals(20.85, state.positionAt(11000), .001)
        assertEquals(100.0, state.copy(position = 99.5).positionAt(12000), .001)
        assertEquals(20.0, state.positionAt(9000), .001)
    }

    @Test fun doesNotInventProgressWhenPausedDisconnectedOrStale() {
        val state = RemotePlaybackState(online = true, playing = true, position = 20.0, duration = 100.0, receivedAt = 10000)
        assertEquals(20.0, state.copy(playing = false).positionAt(12000), .001)
        assertEquals(20.0, state.copy(online = false).positionAt(12000), .001)
        assertEquals(23.0, state.positionAt(99000), .001)
    }
}
