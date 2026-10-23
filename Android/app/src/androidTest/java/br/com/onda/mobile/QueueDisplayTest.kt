package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class QueueDisplayTest {
    @get:Rule val compose=createComposeRule()
    @Test fun displayChoicesSurviveReloadWithRememberOnAndOff() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val original=JSONObject(OndaStore.settings.value.toString())
        try {
            for(remember in listOf(true,false)) for(view in listOf("Compacto","Completa")) {
                OndaStore.saveSettings(JSONObject(original.toString()).put("remember",remember).put("queue_view",view).put("history_view",view).put("queue_card_size","Pequeno").put("history_card_size","Médio"))
                OndaStore.initialize(context)
                assertEquals(view,OndaStore.settings.value.getString("queue_view"))
                assertEquals(view,OndaStore.settings.value.getString("history_view"))
                assertEquals("Pequeno",OndaStore.settings.value.getString("queue_card_size"))
                assertEquals("Médio",OndaStore.settings.value.getString("history_card_size"))
                assertEquals(remember,OndaStore.settings.value.getBoolean("remember"))
            }
        } finally { OndaStore.saveSettings(original) }
    }
    @Test fun publicAlbumMessagesUseSharedCatalogs() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        assertEquals("14 of 14",translateUi("14 de 14","en"))
        assertEquals("Public Spotify album. The public page may omit tracks; connect Spotify if the list is incomplete.",translateUi("Álbum Spotify público. A página pública pode omitir faixas; conecte Spotify se a lista estiver incompleta.","en"))
        assertEquals("Álbum público de Spotify. La página pública puede omitir canciones; conecta Spotify si la lista está incompleta.",translateUi("Álbum Spotify público. A página pública pode omitir faixas; conecte Spotify se a lista estiver incompleta.","es"))
    }
    @Test fun queueSizesAndCompactModePreserveMetadataAndHistorySize() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        val original=JSONObject(OndaStore.settings.value.toString())
        val id=OndaStore.enqueue("https://example.com/song","Artist - Song",extra=JSONObject().put("queue_info",JSONObject().put("album","Test Album").put("duration_ms",240000).put("cover_url","https://example.com/cover.png").put("artists",org.json.JSONArray().put("Fixture Artist")).put("release_date","2024-01-01")))
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        try {
            OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("queue_view","Completa").put("queue_card_size","Grande").put("history_card_size","Médio"))
            compose.setContent {MaterialTheme {QueuePage(vm)}}
            compose.onNodeWithTag("queue-card-$id").performScrollTo()
            val large=compose.onNodeWithTag("queue-card-$id").fetchSemanticsNode().boundsInRoot.height
            compose.onNodeWithText("Test Album",substring=true).assertExists()
            compose.onNodeWithTag("queue-cover-$id",useUnmergedTree=true).assertExists()
            compose.onNodeWithTag("queue-size-control").performScrollTo().performClick()
            compose.onNodeWithText("Pequeno").performClick()
            compose.onNodeWithTag("queue-card-$id").performScrollTo()
            assertTrue(compose.onNodeWithTag("queue-card-$id").fetchSemanticsNode().boundsInRoot.height<large)
            assertEquals("Pequeno",OndaStore.settings.value.getString("queue_card_size"))
            assertEquals("Médio",OndaStore.settings.value.getString("history_card_size"))
            compose.onNodeWithTag("queue-view-control").performScrollTo().performClick()
            compose.onNodeWithText("Compacto").performClick()
            compose.onNodeWithTag("queue-size-control").assertDoesNotExist()
            compose.onNodeWithText("Test Album",substring=true).assertDoesNotExist()
            assertEquals("Artist - Song",OndaStore.items.value.first {it.id==id}.title)
            compose.onNodeWithTag("queue-view-control").performScrollTo().performClick()
            compose.onNodeWithText("Completa").performClick()
            compose.onNodeWithText("Test Album",substring=true).assertExists()
        } finally {OndaStore.remove(setOf(id));OndaStore.saveSettings(original)}
    }
    @Test fun historyToolbarIsAboveCardsAndAlignedHorizontally() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        val original=JSONObject(OndaStore.settings.value.toString())
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        try {
            OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("history_view","Completa"))
            compose.setContent {MaterialTheme {HistoryPage(vm,{})}}
            val clear=compose.onNodeWithTag("clear-history-control").fetchSemanticsNode().boundsInRoot
            val view=compose.onNodeWithTag("history-view-control").fetchSemanticsNode().boundsInRoot
            val size=compose.onNodeWithTag("history-size-control").fetchSemanticsNode().boundsInRoot
            assertTrue(kotlin.math.abs(clear.center.y-view.center.y)<3f)
            assertTrue(kotlin.math.abs(clear.center.y-size.center.y)<3f)
            assertTrue(clear.right<=view.left && view.right<=size.left)
            compose.onNodeWithTag("history-view-control").performClick()
            compose.onNodeWithText("Compacto").performClick()
            compose.onNodeWithTag("history-size-control").assertDoesNotExist()
            assertEquals("Compacto",OndaStore.settings.value.getString("history_view"))
        } finally {OndaStore.saveSettings(original)}
    }

}
