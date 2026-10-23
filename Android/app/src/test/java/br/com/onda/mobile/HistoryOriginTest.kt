package br.com.onda.mobile
import org.junit.Assert.*
import org.junit.Test
class HistoryOriginTest {
    @Test fun recordedIdentitiesBecomeLinks() {
        assertEquals("https://open.spotify.com/track/abc",historyOrigin("spotify:track:abc"))
        assertEquals("https://www.deezer.com/track/123",historyOrigin("deezer:track:123"))
        assertEquals("https://www.youtube.com/watch?v=abc-123",historyOrigin("youtube:video:abc-123"))
        assertEquals("https://www.youtube.com/playlist?list=PL123",historyOrigin("youtube:playlist:PL123"))
        assertEquals("https://music.apple.com/br/song/123",historyOrigin("https://music.apple.com/br/song/123"))
    }
    @Test fun unsafeAndMissingOriginsAreDisabled() {
        for(source in listOf("","file:///x","javascript:alert(1)","https://","https://user:password@example.com"))assertEquals("",historyOrigin(source))
    }
}
