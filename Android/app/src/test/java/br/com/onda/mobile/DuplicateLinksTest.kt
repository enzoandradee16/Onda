package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class DuplicateLinksTest {
    @Test fun spotifySharingAndLocale() {
        assertEquals("spotify:track:ABC",sourceKey("https://open.spotify.com/intl-pt/track/ABC?si=123"))
        assertEquals("spotify:track:ABC",sourceKey("spotify:track:ABC"))
    }
    @Test fun youtubeVariants() {
        val values=listOf("https://youtu.be/abc?si=xyz","https://www.youtube.com/watch?v=abc&utm_source=share","https://youtube.com/shorts/abc","https://music.youtube.com/watch?v=abc")
        assertEquals(1,values.map(::sourceKey).distinct().size)
    }
    @Test fun deezerLocale() {
        assertEquals(sourceKey("https://deezer.com/br/track/123"),sourceKey("https://deezer.com/track/123?utm_source=share"))
    }
    @Test fun meaningfulParametersPreserved() {
        assertNotEquals(sourceKey("https://example.com/audio?id=1"),sourceKey("https://example.com/audio?id=2"))
    }
    @Test fun unrelatedGenericResourcesRemainDistinct() {
        val base=sourceKey("https://example.com/audio")
        listOf("http://example.com/audio","https://www.example.com/audio","https://example.com/audio/","https://example.com:8443/audio","https://user@example.com/audio").forEach {assertNotEquals(it,base,sourceKey(it))}
    }
    @Test fun genericTrackingParametersAndOrder() {
        assertEquals(sourceKey("https://example.com/audio?b=2&a=1"),sourceKey("https://example.com/audio?utm_source=share&a=1&b=2#section"))
        assertNotEquals(sourceKey("https://example.com/audio?a="),sourceKey("https://example.com/audio"))
    }
}
