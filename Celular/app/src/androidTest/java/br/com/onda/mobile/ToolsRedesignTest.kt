package br.com.onda.mobile

import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.content.IntentFilter
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.core.content.FileProvider
import com.chaquo.python.Python
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class ToolsRedesignTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource(){override fun before(){val i=InstrumentationRegistry.getInstrumentation();if(android.os.Build.VERSION.SDK_INT>=33)i.uiAutomation.grantRuntimePermission(i.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)}}
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()
    private fun ready(){compose.waitForIdle();if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()}
    private fun open(label:String){compose.onNodeWithTag("nav-Mais").performClick();compose.onNodeWithTag("more-list").performScrollToNode(hasTestTag("more-$label"));compose.onNodeWithTag("more-$label").performClick()}
    private fun capture(name:String){compose.waitForIdle();Thread.sleep(600);val context=InstrumentationRegistry.getInstrumentation().targetContext;val bitmap=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot();File(context.getExternalFilesDir(null),"tools-$name.png").outputStream().use {bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()}

    @Test fun openingCacheCategoriesDoesNotPublishAnOperation() {
        ready()
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        val previous=JSONObject(OndaStore.settings.value.toString())
        val originalStatus=vm.status.value
        try {
            compose.runOnIdle {
                OndaStore.saveSettings(JSONObject(previous.toString()).put("language","pt-BR").put("check_updates",false))
                vm.status.value="Estado anterior"
            }
            compose.onNodeWithTag("open-settings").performClick()
            compose.onNodeWithText("Ferramentas").performScrollTo().performClick()
            compose.onNodeWithText("Cache").performScrollTo()
            compose.waitUntil(30000){compose.onAllNodes(hasText("Cache em disco:",substring=true)).fetchSemanticsNodes().isNotEmpty()}
            compose.runOnIdle {assertEquals("Estado anterior",vm.status.value);assertFalse(vm.busy.value);assertNull(vm.dialogNotice.value)}
            compose.onNodeWithContentDescription("Voltar").performClick()
            compose.onNodeWithText("Desempenho").performScrollTo().performClick()
            compose.waitUntil(30000){compose.onAllNodes(hasText("Cache em disco:",substring=true)).fetchSemanticsNodes().isNotEmpty()}
            compose.onNodeWithText("Atualizar tamanho").performScrollTo().performClick()
            compose.waitForIdle()
            compose.runOnIdle {assertEquals("Estado anterior",vm.status.value);assertFalse(vm.busy.value);assertNull(vm.dialogNotice.value)}
        } finally {compose.runOnIdle {vm.status.value=originalStatus;OndaStore.saveSettings(previous)}}
    }

    @Test fun allToolsKeepTheirActionsAndSettingsUseCategories() {
        ready()
        val instrumentation=InstrumentationRegistry.getInstrumentation();val context=instrumentation.targetContext
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        val previous=JSONObject(OndaStore.settings.value.toString());val history=OndaStore.history.value
        val library=runBlocking {CollectionsLibrary.read()}
        val monitors=mutableListOf<Instrumentation.ActivityMonitor>()
        fun selectFile(file:File){val uri=FileProvider.getUriForFile(context,"${context.packageName}.files",file);monitors+=instrumentation.addMonitor(IntentFilter(Intent.ACTION_OPEN_DOCUMENT).apply {addDataType("*/*")},Instrumentation.ActivityResult(Activity.RESULT_OK,Intent().setData(uri)),true)}
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(previous.toString()).put("language","pt-BR").put("theme","Escuro").put("accent","Verde-Água").put("check_updates",false).put("hidden_tabs",JSONArray()).put("history_view","Compacto"))}
            compose.onNodeWithTag("open-settings").performClick()
            compose.onNodeWithText("Preferências").assertIsDisplayed();capture("settings")
            compose.onNodeWithText("Áudio").performClick()
            compose.onNodeWithText("Reprodução e prévias").assertExists()
            compose.onNodeWithContentDescription("Voltar").performClick()
            compose.onNodeWithTag("settings-search").performTextInput("transição")
            compose.onNodeWithText("Áudio · Duração da transição entre músicas (segundos)").performClick()
            compose.onNodeWithText("Duração da transição entre músicas (segundos)").assertExists()
            compose.onNodeWithTag("nav-Mais").performClick()
            open("Imagens");compose.onNodeWithText("Sua imagem aparece aqui").assertExists()
            val image=File(context.cacheDir,"tools-fixture.png")
            val bitmap=android.graphics.Bitmap.createBitmap(640,360,android.graphics.Bitmap.Config.ARGB_8888);bitmap.eraseColor(android.graphics.Color.rgb(30,100,115));image.outputStream().use {bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()
            selectFile(image);compose.onNodeWithText("Escolher arquivo").performClick();compose.onNodeWithText("Procurar nos arquivos").performClick()
            compose.waitUntil(30000){compose.onAllNodesWithText("640 × 360 · PNG").fetchSemanticsNodes().isNotEmpty()}
            capture("images")
            compose.onNodeWithContentDescription("Formato: Original").performScrollTo().performClick();compose.onNodeWithText("JPG").performClick()
            compose.waitUntil(30000){compose.onAllNodesWithText("640 × 360 · JPG").fetchSemanticsNodes().isNotEmpty()}
            instrumentation.removeMonitor(monitors.removeAt(0))
            open("Conversor");compose.onNodeWithTag("converter-start").performScrollTo().assertIsNotEnabled();compose.onNodeWithText("Conversor").performScrollTo();capture("converter")
            compose.onNodeWithText("Opções avançadas").performScrollTo().performClick();compose.onNodeWithText("Bitrate de vídeo").performScrollTo().assertIsDisplayed()
            MobileEngine.initialize(context)
            val source=File(Python.getInstance().getModule("mobile_history_smoke").callAttr("fixture",context.cacheDir.absolutePath).toString())
            selectFile(source)
            open("Editar metadados");compose.onNodeWithText("Escolher arquivo de áudio").performClick()
            compose.waitUntil(30000){compose.onAllNodesWithText("History Song").fetchSemanticsNodes().isNotEmpty() && !vm.busy.value}
            compose.onNodeWithText("Alterar capa").assertExists();capture("metadata")
            compose.onNodeWithText("Salvar alterações").performScrollTo().assertIsEnabled()
            instrumentation.removeMonitor(monitors.removeAt(0))
            compose.runOnIdle {vm.collection.value=JSONObject().put("title","Coleção de teste").put("subtitle","Artista de teste").put("kind","album").put("tracks",JSONArray().put(JSONObject().put("title","Faixa de teste").put("artists",JSONArray().put("Artista de teste")).put("source_url","https://example.com/track")))}
            open("Álbuns e playlists");compose.onNodeWithText("Importar").performClick()
            compose.onNodeWithText("Salvar coleção").performScrollTo().performClick()
            compose.waitUntil(10000){runBlocking {CollectionsLibrary.read()}.any {it.optString("title")=="Coleção de teste"}}
            compose.onNodeWithText("Salvos").performScrollTo().performClick();compose.onNodeWithText("Coleção de teste").assertExists();capture("collections")
            compose.onNodeWithText("Coleção de teste").performClick();compose.onNodeWithTag("collection-list").performScrollToNode(hasText("Faixa de teste"));compose.onNodeWithText("Faixa de teste").assertExists()
            compose.runOnIdle {OndaStore.history.value=listOf(HistoryItem(989898,"History Artist - History Song",android.net.Uri.fromFile(source).toString(),"mp3",source.length(),completedAt=System.currentTimeMillis()))}
            open("Histórico")
            compose.waitUntil(10000){compose.onAllNodesWithText("History Song").fetchSemanticsNodes().isNotEmpty()}
            compose.onNodeWithText("Hoje").assertExists();compose.onNodeWithText("History Artist").assertExists();capture("history")
            compose.onNodeWithText("Imagens").performClick();compose.onNodeWithText("Nenhum resultado").assertExists()
            compose.onNodeWithText("Todos").performClick()
            compose.onNodeWithContentDescription("Opções do histórico").performClick()
            compose.onNodeWithContentDescription("Tamanho dos cards do histórico: Grande").performClick();compose.onNodeWithText("Médio").performClick()
            compose.runOnIdle {assertEquals("Médio",OndaStore.settings.value.optString("history_card_size"))}
            compose.onNodeWithText("Pronto").performClick()
            compose.onNodeWithText("Selecionar").performClick();compose.onNodeWithTag("history-list").performScrollToNode(hasTestTag("history-card-989898"));compose.onNodeWithTag("history-card-989898").performClick().assertIsOn()
            compose.onNodeWithTag("history-list").performScrollToNode(hasText("Concluir"));compose.onNodeWithText("Concluir").performClick()
            compose.onNodeWithContentDescription("Mais ações").performClick();compose.onNodeWithText("Compartilhar").assertExists()
        } finally {
            monitors.forEach {instrumentation.removeMonitor(it)}
            compose.runOnIdle {OndaStore.history.value=history;OndaStore.saveSettings(previous);vm.collection.value=JSONObject()}
            runBlocking {CollectionsLibrary.write(library)}
        }
    }
}
