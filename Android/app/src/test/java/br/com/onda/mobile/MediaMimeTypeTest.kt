package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test
import java.util.Locale

class MediaMimeTypeTest {
    @Test fun recognizesConverterAndAudioEditorFormats() {
        mapOf("mp3" to "audio/mpeg","m4a" to "audio/mp4","aac" to "audio/aac","flac" to "audio/flac","wav" to "audio/wav","ogg" to "audio/ogg","opus" to "audio/ogg").forEach {(extension,mime)->
            assertEquals(mime,mediaMimeType("song.$extension"))
        }
    }
    @Test fun recognizesOriginalAnimatedAndModernImages() {
        for(extension in listOf("gif","avif","heic","heif","bmp"))assertEquals("image/$extension",mediaMimeType("photo.$extension"))
        assertEquals("image/jpeg",mediaMimeType("photo.jpeg"))
        assertEquals("video/x-matroska",mediaMimeType("video.mkv"))
    }
    @Test fun handlesUnknownExtensionsAndLocaleIndependentCase() {
        assertEquals("application/octet-stream",mediaMimeType("file.unknown"))
        assertEquals("application/octet-stream",mediaMimeType("mp3"))
        val previous=Locale.getDefault()
        try {Locale.setDefault(Locale.forLanguageTag("tr-TR"));assertEquals("image/gif",mediaMimeType("PHOTO.GIF"))}
        finally {Locale.setDefault(previous)}
    }
}
