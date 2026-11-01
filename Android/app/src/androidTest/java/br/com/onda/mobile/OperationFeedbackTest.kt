package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class OperationFeedbackTest {
    @get:Rule val compose=createComposeRule()

    @Test fun structuredResultsAreReadableIncludingCacheFailures() {
        val message=operationResultMessage(JSONObject().put("bytes",16384).put("removed",1048576).put("failed",1))
        assertTrue(message.contains("MB"))
        assertTrue(message.contains("não puderam ser removidos"))
        assertFalse(message.contains("\"removed\""))
        assertEquals("Concluído",operationResultMessage(JSONObject().put("message",JSONObject().put("internal",true))))
        assertEquals("Concluído",operationResultMessage(JSONObject()))
    }

    @Test fun emptyCatalogAndPlaybackSearchWarnBeforeStartingRequests() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val store=ViewModelStore()
        lateinit var vm:OndaViewModel
        compose.runOnUiThread {
            vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
            vm.jukebox.stop()
            vm.search("   ","Spotify")
            assertEquals(EMPTY_MUSIC_SEARCH,vm.dialogNotice.value?.message)
            assertFalse(vm.busy.value)
            vm.dismissNotice()
        }
        try {
            compose.setContent {MaterialTheme {PlaybackPage(vm)}}
            compose.onNodeWithTag("playback-search-submit").assertIsEnabled().performClick()
            compose.runOnIdle {
                assertEquals(EMPTY_MUSIC_SEARCH,vm.dialogNotice.value?.message)
                assertFalse(vm.jukebox.searching.value)
            }
        } finally {compose.runOnUiThread {store.clear()}}
    }
}
