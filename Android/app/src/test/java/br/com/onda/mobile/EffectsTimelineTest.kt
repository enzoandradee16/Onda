package br.com.onda.mobile

import org.junit.Assert.assertEquals
import org.junit.Test

class EffectsTimelineTest {
    @Test fun slowedPlaybackUsesSourceClockAfterSeeking() {
        assertEquals(67.5,EffectsTimeline.position(60.0,10000,75,240.0),.0001)
        assertEquals(230.0,EffectsTimeline.remaining(67.5,240.0,75),.0001)
    }
    @Test fun spedUpPlaybackUsesSourceClockAfterPausing() {
        val paused=EffectsTimeline.position(20.0,10000,150,240.0)
        assertEquals(35.0,paused,.0001)
        assertEquals(36.5,EffectsTimeline.position(paused,1000,150,240.0),.0001)
    }
    @Test fun reverbTailDoesNotAdvancePastEndOfSource() {
        assertEquals(180.0,EffectsTimeline.position(170.0,20000,100,180.0),.0001)
        assertEquals(0.0,EffectsTimeline.remaining(181.0,180.0,100),.0001)
    }
    @Test fun fullSongIsNotLimitedToPreviewLength() {
        assertEquals(600.0,EffectsTimeline.remaining(0.0,300.0,50),.0001)
    }
    @Test fun seekNearEndKeepsFractionalSeconds() {
        assertEquals(.5,EffectsTimeline.remaining(299.25,300.0,150),.0001)
    }
    @Test fun playerUnsetPositionCannotMoveClockBackwards() {
        assertEquals(40.0,EffectsTimeline.position(40.0,-1,100,180.0),.0001)
    }
}
