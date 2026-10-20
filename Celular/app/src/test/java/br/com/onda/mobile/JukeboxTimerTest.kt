package br.com.onda.mobile
import org.junit.Assert.*
import org.junit.Test
class JukeboxTimerTest {
    @Test fun graphFollowsOnlyTheAudibleTransition() {
        assertEquals(0f,jukeboxJumpBlend(.5f,.5,.05),.001f)
        assertEquals(.5f,jukeboxJumpBlend(.95f,.5,.05),.001f)
        assertEquals(1f,jukeboxJumpBlend(1f,.5,.05),.001f)
        assertEquals(0f,jukeboxJumpBlend(1f,.5,0.0),.001f)
    }
    @Test fun countsOnlyAudiblePlaybackAndResetsForAnotherSong() {
        val timer=JukeboxTimerProgress(60.0);val first=Any();val second=Any()
        assertEquals(50.0,timer.advance(10.0,true,false,first),0.001)
        assertEquals(50.0,timer.advance(30.0,true,true,first),0.001)
        assertEquals(50.0,timer.advance(30.0,false,false,first),0.001)
        assertEquals(60.0,timer.advance(30.0,false,false,second),0.001)
        assertEquals(0.0,timer.advance(90.0,true,false,second),0.001)
        timer.restart()
        assertEquals(59.0,timer.advance(1.0,true,false,second),0.001)
    }
}
