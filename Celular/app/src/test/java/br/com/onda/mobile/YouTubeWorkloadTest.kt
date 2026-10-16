package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class YouTubeWorkloadTest {
    @Test fun catalogAudioSharesBudgetWithDirectVideos() {
        for(url in listOf("https://open.spotify.com/track/1","https://www.deezer.com/track/1","https://music.apple.com/br/song/1","https://youtu.be/abcdefghijk")) {
            assertTrue(usesYouTube(url,"mp3"))
        }
    }
    @Test fun unrelatedSourcesKeepParallelism() {
        assertFalse(usesYouTube("https://www.deezer.com/track/1","flac"))
        assertFalse(usesYouTube("https://youtube.com.example.org/file","mp3"))
        assertFalse(usesYouTube("invalid","mp3"))
        assertTrue(usesYouTube("https://music.youtube.com/watch?v=abcdefghijk","flac"))
    }
}
