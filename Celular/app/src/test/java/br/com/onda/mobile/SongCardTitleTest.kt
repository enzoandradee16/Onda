package br.com.onda.mobile
import org.junit.Assert.*
import org.junit.Test
class SongCardTitleTest {
    @Test fun removesOnlyConfirmedArtistPrefix() {
        assertEquals("Music Sounds Better With You",songCardTitle("NEIL FRANCES - Music Sounds Better With You","NEIL FRANCES"))
        assertEquals("Music Sounds Better With You",songCardTitle("Stardust, Benjamin Diamond - Music Sounds Better With You","Stardust, Benjamin Diamond"))
        assertEquals("One More Time",songCardTitle("One More Time","Daft Punk"))
        assertEquals("Love - Part II",songCardTitle("Love - Part II","Another Artist"))
        assertEquals("Artist - Song",songCardTitle("Artist - Song",""))
    }
}
