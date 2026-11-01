package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class PerformanceRegressionTest {
    @Test fun remoteClockAndQueueUpdatesDoNotRepublishArtworkOrNotification() {
        val artwork=Any()
        val before=RemotePlaybackState(trackId="track",title="Song",online=true,playing=true)
        val clock=before.copy(position=42.0,receivedAt=1000L,queueLoading=true)
        assertEquals(before.metadataSignature(artwork),clock.metadataSignature(artwork))
        assertEquals(before.notificationSignature(artwork),clock.notificationSignature(artwork))
        assertNotEquals(before.metadataSignature(artwork),before.copy(title="Other").metadataSignature(artwork))
        assertNotEquals(before.notificationSignature(artwork),before.copy(playing=false).notificationSignature(artwork))
        assertNotEquals(before.metadataSignature(artwork),before.metadataSignature(Any()))
    }
}
