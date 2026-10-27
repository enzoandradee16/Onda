package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class DownloadsHomeTest {
    @get:Rule val compose=createComposeRule()
    @Test fun searchFilterRetryAndBatchRemoveStayOnTheSimpleScreen() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val original=JSONObject(OndaStore.settings.value.toString())
        val ids=mutableListOf<String>()
        val prefix="simple-${System.nanoTime()}"
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        fun menu(text:String){compose.onNodeWithTag("downloads-menu").performClick();compose.onNodeWithText(text).performClick()}
        try {
            OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("queue_view","Compacto").put("queue_actions_at_top",false))
            for((index,state) in listOf("Pendente","Erro","Concluído").withIndex()) {
                ids+=OndaStore.enqueue("https://example.com/$prefix/$index","$prefix Track $index",extra=JSONObject().put("queue_info",JSONObject().put("title","$prefix Track $index")))
                OndaStore.update(ids.last(),state)
            }
            val dark=mutableStateOf(false)
            compose.setContent {MaterialTheme(colorScheme=if(dark.value)pureBlackSurfaces(darkColorScheme(),false) else lightColorScheme()) {Surface {DownloadsHome(vm)}}}
            compose.onNodeWithTag("downloads-home").assertExists()
            for(mode in listOf(false,true)) {
                compose.runOnIdle {dark.value=mode}
                compose.onRoot().captureToImage().asAndroidBitmap().let {image->File(context.getExternalFilesDir(null),if(mode)"downloads-dark.png" else "downloads-light.png").outputStream().use {image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}}
            }
            compose.onNodeWithText("Fila de downloads").assertDoesNotExist()
            compose.onNodeWithTag("queue-view-control").assertDoesNotExist()
            menu("Buscar na fila")
            compose.onNodeWithTag("queue-search").performTextInput(prefix)
            compose.onNodeWithTag("download-summary-${ids[0]}").performScrollTo().assertExists()
            menu("Filtrar e ordenar")
            compose.onNodeWithText("Todos").performClick()
            compose.onNodeWithText("Com falha").performClick()
            compose.onNodeWithText("Aplicar").performClick()
            compose.onNodeWithTag("download-summary-${ids[0]}").assertDoesNotExist()
            compose.onNodeWithTag("download-menu-${ids[1]}").performScrollTo().performClick()
            compose.onAllNodesWithText("Tentar novamente").onLast().performClick()
            compose.waitUntil(5000){OndaStore.items.value.first {it.id==ids[1]}.state=="Pendente"}
            compose.onNodeWithTag("downloads-clear-filter").performClick()
            menu("Selecionar")
            compose.onNodeWithTag("download-summary-${ids[0]}").performScrollTo().performClick().assertIsOn()
            compose.onNodeWithTag("downloads-remove-selected").performClick()
            compose.waitUntil(5000){OndaStore.items.value.none {it.id==ids[0]}}
            assertTrue(OndaStore.items.value.any {it.id==ids[1]})
            assertTrue(OndaStore.items.value.any {it.id==ids[2]})
            compose.onNodeWithText("Pronto").performClick()
            compose.onNodeWithText("Concluídos").performClick()
            compose.onNodeWithTag("download-summary-${ids[2]}").performScrollTo().assertExists()
            menu("Filtrar e ordenar")
            compose.onNodeWithText("Todos").performClick()
            compose.onAllNodesWithText("Concluídos").onLast().performClick()
            compose.onNodeWithText("Aplicar").performClick()
            compose.onNodeWithTag("download-summary-${ids[2]}").performScrollTo().assertExists()
            assertFalse(OndaStore.settings.value.has("queue_view"))
            assertFalse(OndaStore.settings.value.has("queue_actions_at_top"))
            assertTrue(settingsSearchEntries().none {it.label in setOf("Gerenciamento avançado","Mostrar itens na fila","Mostrar ações antes das listas")})
        } finally {OndaStore.remove(ids.toSet());OndaStore.saveSettings(original)}
    }
}
