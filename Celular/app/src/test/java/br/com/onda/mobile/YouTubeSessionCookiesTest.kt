package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test
import java.io.File

class YouTubeSessionCookiesTest {
    @Test fun importedCookieFileMustBeNetscapeAndContainYouTubeDomain() {
        val file=File.createTempFile("onda-cookie-test-",".txt")
        try {
            file.writeText("# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tfixture\n")
            assertTrue(isYouTubeCookieFile(file))
            file.writeText("# HTTP Cookie File\n#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tfixture\n")
            assertTrue(isYouTubeCookieFile(file))
            file.writeText("# Netscape HTTP Cookie File\n.youtube.com.example.com\tTRUE\t/\tTRUE\t0\tSID\tfixture\n")
            assertFalse(isYouTubeCookieFile(file))
            file.writeText("not a cookie file");assertFalse(isYouTubeCookieFile(file))
        } finally {file.delete()}
    }
    @Test fun loginMarkerIsRequiredAndUnsafeHeaderValuesAreRejected() {
        assertFalse(hasYouTubeLogin(youtubeCookieEntries(listOf("CONSENT=YES"))))
        assertTrue(hasYouTubeLogin(youtubeCookieEntries(listOf("SID=fixture"))))
        assertFalse(youtubeCookieEntries(listOf("SID=unsafe\rvalue")).containsKey("SID"))
    }
}
