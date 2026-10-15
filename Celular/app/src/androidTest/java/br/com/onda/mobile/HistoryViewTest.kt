package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class HistoryViewTest {
    @get:Rule val compose=createComposeRule()
    @Test fun nativeTagsAndCoverAppearOnlyInCompleteMode() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        MobileEngine.initialize(context)
        val path=Python.getInstance().getModule("mobile_history_smoke").callAttr("fixture",context.cacheDir.absolutePath).toString()
        val uri=android.net.Uri.fromFile(File(path)).toString()
        val details=readHistoryDetails(context,uri)
        assertEquals("History Song",details.title);assertEquals("History Artist",details.artist)
        assertTrue(details.lines.any {it.contains("History Album")});assertNotNull(details.cover)
        val settings=JSONObject(OndaStore.settings.value.toString())
        val history=OndaStore.history.value
        val item=HistoryItem(987654,"song.mp3",uri,"mp3",File(path).length())
        val cached=cachedHistoryDetails(context,item,historyDetailsRevision.value)
        assertSame(cached,cachedHistoryDetails(context,item,historyDetailsRevision.value))
        invalidateHistoryDetails()
        assertNotSame(cached,cachedHistoryDetails(context,item,historyDetailsRevision.value))
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        try {
            OndaStore.history.value=listOf(item,item.copy(id=987655))
            OndaStore.settings.value=JSONObject(settings.toString()).put("language","pt-BR").put("history_card_size","Grande").put("history_view","Compacto")
            compose.setContent {MaterialTheme {HistoryPage(vm,{})}}
            compose.onNodeWithTag("history-card-987654").assertExists()
            compose.onNodeWithTag("history-complete-987654").assertDoesNotExist()
            compose.runOnIdle {OndaStore.settings.value=JSONObject(settings.toString()).put("language","pt-BR").put("history_card_size","Grande").put("history_view","Completa")}
            compose.waitUntil(5000) {compose.onAllNodesWithText("History Song").fetchSemanticsNodes().isNotEmpty()}
            val largeHeight=compose.onNodeWithTag("history-card-987654").fetchSemanticsNode().boundsInRoot.height
            compose.onNodeWithTag("history-size-control").performScrollTo().performClick()
            compose.onNodeWithText("Pequeno").performClick()
            compose.waitForIdle()
            assertTrue(compose.onNodeWithTag("history-card-987654").fetchSemanticsNode().boundsInRoot.height<largeHeight)
            compose.onNodeWithTag("history-size-control").performScrollTo().performClick()
            compose.onNodeWithText("Grande").performClick()
            assertEquals("Após 3 segundos",OndaStore.defaults().getString("notice_duration"))
            compose.onNodeWithTag("history-card-987654").performClick().assertIsOn()
            compose.onNodeWithTag("history-card-987655").performScrollTo().performClick().assertIsOn()
            compose.onNodeWithTag("history-card-987654").assertIsOn()
            compose.onAllNodesWithText("History Artist")[0].assertExists()
            compose.onAllNodesWithText("Álbum / single: History Album")[0].assertExists()
            compose.onAllNodesWithText("Abrir arquivo")[0].assertExists()
            compose.runOnIdle {OndaStore.settings.value=JSONObject(settings.toString()).put("language","pt-BR").put("history_card_size","Grande").put("history_view","Compacto")}
            compose.onNodeWithTag("history-complete-987654").assertDoesNotExist()
        } finally {OndaStore.history.value=history;OndaStore.saveSettings(settings)}
    }
}
