package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class ListNavigationTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun largeQueueCanJumpToLastAndFirstWithActionsAboveOrBelow() {
        val settings=JSONObject(OndaStore.settings.value.toString())
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        val ids=mutableListOf<String>();val prefix=UUID.randomUUID().toString()
        try {
            OndaStore.saveSettings(JSONObject(settings.toString()).put("language","pt-BR").put("queue_view","Compacto").put("queue_actions_at_top",true))
            OndaStore.enqueueBatch {repeat(80) {ids+=OndaStore.enqueue("https://example.com/$prefix/$it","Track $it")}}
            compose.setContent {MaterialTheme {QueuePage(vm)}}
            compose.onNodeWithTag("queue-last").performClick()
            compose.onNodeWithTag("queue-card-${ids.last()}").assertIsDisplayed()
            compose.onNodeWithTag("queue-first").performClick()
            compose.onNodeWithText("Baixar fila").performScrollTo().assertIsDisplayed()
            val actionsY=compose.onNodeWithText("Baixar fila").fetchSemanticsNode().boundsInRoot.top
            compose.onNodeWithTag("queue-card-${ids.first()}").performScrollTo()
            assertTrue(actionsY<compose.onNodeWithTag("queue-card-${ids.first()}").fetchSemanticsNode().boundsInRoot.top+1000)
            OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("queue_actions_at_top",false))
            compose.waitForIdle()
            compose.onNodeWithTag("queue-last").performClick()
            compose.onNodeWithText("Baixar fila").assertIsDisplayed()
            compose.onNodeWithTag("queue-position").assertExists()
        } finally {OndaStore.remove(ids.toSet());OndaStore.saveSettings(settings);compose.runOnIdle {vm.player.release()}}
    }
    @Test fun collectionActionsAreBeforeLargeTrackListAndNavigationReachesEnd() {
        val old=JSONObject(OndaStore.settings.value.toString())
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        try {
            OndaStore.saveSettings(JSONObject(old.toString()).put("language","pt-BR").put("queue_actions_at_top",true))
            val tracks=JSONArray();repeat(1300) {tracks.put(JSONObject().put("source_url","https://example.com/$it").put("title","Collection track $it").put("artists",JSONArray().put("Artist")))}
            vm.collection.value=JSONObject().put("title","Large fixture").put("tracks",tracks)
            compose.setContent {MaterialTheme {CollectionsPage(vm)}}
            compose.onNodeWithText("Selecionar visíveis").performScrollTo().performClick()
            compose.onNodeWithText("Adicionar à fila").performScrollTo().assertIsEnabled()
            compose.onNodeWithTag("collection-last").performClick()
            compose.onNodeWithText("Collection track 1299").assertIsDisplayed()
            compose.onNodeWithTag("collection-first").performClick()
            compose.onNodeWithText("Seus álbuns e playlists na biblioteca.").assertIsDisplayed()
        } finally {OndaStore.saveSettings(old);compose.runOnIdle {vm.player.release()}}
    }
    @Test fun newLabelsAndProgressTranslateInBothLanguages() {
        assertEquals("Show actions before lists",translateUi("Mostrar ações antes das listas","en"))
        assertEquals("100 of 1300 items added to the queue",translateUi("100 de 1300 itens adicionados à fila","en"))
        assertEquals("100 de 1300 elementos añadidos a la cola",translateUi("100 de 1300 itens adicionados à fila","es"))
        assertEquals("List position",translateUi("Posição na lista","en"))
    }
}
