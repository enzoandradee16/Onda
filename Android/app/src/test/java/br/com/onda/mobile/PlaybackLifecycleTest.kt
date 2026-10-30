package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class PlaybackLifecycleTest {
    @Test fun minimizingMustNotChangeLauncherComponentsWhileAudioIsActive() {
        assertFalse(canApplyLauncherChange(0,true,false,false))
        assertFalse(canApplyLauncherChange(0,false,true,false))
        assertFalse(canApplyLauncherChange(0,false,false,true))
        assertFalse(canApplyLauncherChange(1,false,false,false))
        assertTrue(canApplyLauncherChange(0,false,false,false))
    }

    @Test fun aNewTrackInvalidatesThePreviousTracksDelayedStop() {
        val idle=PlaybackIdleStop()
        val previousTrackStop=idle.changed()
        idle.changed() // Next song started before the delayed callback.
        assertFalse(idle.canStop(previousTrackStop,true))
        assertFalse(idle.canStop(previousTrackStop,false))
        val actualStop=idle.changed()
        assertFalse(idle.canStop(actualStop,true))
        assertTrue(idle.canStop(actualStop,false))
    }

    @Test fun preparingTheNextSlowedTrackKeepsTheForegroundServiceAlive() {
        val idle=PlaybackIdleStop()
        val request=idle.changed()
        assertFalse(idle.canStop(request,playing=false,preparing=true))
        val completedPreparation=idle.changed()
        assertTrue(idle.canStop(completedPreparation,false))
    }
}
