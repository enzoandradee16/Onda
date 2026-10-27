package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class PlaybackParityTest {
    @Test fun shuffleKeepsPlayedPrefixAndSkipsCurrentWhenWrapping() {
        assertEquals(2,shuffledNextIndex(5,1,2){0})
        assertEquals(4,shuffledNextIndex(5,1,2){it-1})
        assertEquals(3,shuffledNextIndex(5,4,0){it-1})
        assertEquals(0,shuffledNextIndex(1,0,0){0})
    }
    @Test fun repeatRespectsEndAndManualSkip() {
        assertEquals(-1,nextPlaybackIndex(0,-1,"Todas"))
        assertEquals(-1,nextPlaybackIndex(3,2,"Desativada",true))
        assertEquals(0,nextPlaybackIndex(3,2,"Todas",true))
        assertEquals(1,nextPlaybackIndex(3,1,"Uma",true))
        assertEquals(2,nextPlaybackIndex(3,1,"Uma",false))
    }
    @Test fun reorderedQueueKeepsCurrentTrackIdentity() {
        val original=listOf("first","playing","last")
        val result=movePlaybackEntry(original,1,1)
        assertEquals(listOf("first","last","playing"),result)
        assertEquals(2,result.indexOf("playing"))
        assertEquals(original,movePlaybackEntry(result,2,-1))
    }
    @Test fun movingAtQueueBoundariesKeepsOrder() {
        val rows=listOf("a","b")
        assertSame(rows,movePlaybackEntry(rows,0,-1))
        assertSame(rows,movePlaybackEntry(rows,1,1))
        assertSame(rows,movePlaybackEntry(rows,-1,1))
    }
    @Test fun cursorTracksItemsMovedAcrossTheCurrentPosition() {
        assertEquals(2,playbackCursorAfterMove(1,1,2))
        assertEquals(0,playbackCursorAfterMove(1,0,2))
        assertEquals(2,playbackCursorAfterMove(1,2,0))
        assertEquals(1,playbackCursorAfterMove(1,3,4))
    }
    @Test fun lyricBeforeFirstTimestampHasNoActiveVerse() {
        val rows=listOf(2.0 to "First",8.0 to "Next")
        assertEquals(-1,lyricActiveIndex(rows,1.9))
        assertEquals(0,lyricActiveIndex(rows,2.0))
        assertEquals(1,lyricActiveIndex(rows,10.0))
    }
    @Test fun unsynchronizedLyricsRemainReadableWithoutSelectingTheLastLine() {
        assertEquals(-1,lyricActiveIndex(listOf(0.0 to "First",0.0 to "Second"),60.0))
    }
    @Test fun enhancedLyricsKeepWordsWithoutShowingTimestampMarkup() {
        assertEquals("Hello world",lyricPlainText("<01:02.300>Hello <01:03.100>world"))
    }
}
