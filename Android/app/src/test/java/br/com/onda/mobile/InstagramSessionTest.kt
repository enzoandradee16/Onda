package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class InstagramSessionTest {
    @Test fun verificationFramesWorkWithoutAllowingOffsiteMainNavigation() {
        assertTrue(instagramNavigationAllowed("https","www.instagram.com",true))
        assertTrue(instagramNavigationAllowed("https","www.google.com",false))
        assertFalse(instagramNavigationAllowed("https","instagram.com.example.org",true))
        assertFalse(instagramNavigationAllowed("file","",false))
    }
    @Test fun requiresActualLoginAndPreservesEncodedSessionValues() {
        val entries=instagramCookieEntries(listOf("csrftoken=public", "sessionid=123%3Aabc%3Axyz; ds_user_id=123"))
        assertFalse(hasInstagramLogin(instagramCookieEntries(listOf("csrftoken=public"))))
        assertTrue(hasInstagramLogin(entries))
        assertTrue(instagramCookieFile(entries).contains(".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t123%3Aabc%3Axyz"))
    }
    @Test fun rejectsCookieLineInjection() {
        val entries=instagramCookieEntries(listOf("sessionid=valid\n.evil.com\tTRUE; ds_user_id=123"))
        assertFalse(hasInstagramLogin(entries))
    }
}
