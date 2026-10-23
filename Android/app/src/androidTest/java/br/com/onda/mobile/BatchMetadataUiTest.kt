package br.com.onda.mobile

import android.app.Activity
import android.app.Instrumentation
import android.content.ClipData
import android.content.Intent
import android.content.IntentFilter
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.core.content.FileProvider
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
class BatchMetadataUiTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    private fun ready() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
    }
    private fun metadata() {
        compose.onNodeWithTag("nav-Mais").performClick()
        compose.onNodeWithTag("more-list").performScrollToNode(hasTestTag("more-Editar metadados"))
        compose.onNodeWithTag("more-Editar metadados").performClick()
    }
    @Test fun batchDialogIsTranslatedInAllLanguages() {
        ready()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            for(language in listOf("pt-BR","es","en")) {
                compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("language",language))}
                metadata()
                compose.onNodeWithText(translateUi("Editar metadados em lote",language)).performClick()
                compose.onNodeWithText(translateUi("Marque somente os campos que deseja alterar. Campos desmarcados serão preservados.",language)).assertIsDisplayed()
                compose.onNodeWithTag("batch-apply").assertIsNotEnabled()
                compose.onNodeWithText(translateUi("Fechar",language)).performClick()
            }
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }
    @Test fun multipleDocumentsCanBeEditedWithoutChangingOriginals() {
        ready()
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        val settings=JSONObject(OndaStore.settings.value.toString())
        compose.runOnIdle {OndaStore.saveSettings(JSONObject(settings.toString()).put("language","pt-BR").put("output_uri",""))}
        MobileEngine.initialize(context)
        val fixture=File(Python.getInstance().getModule("mobile_smoke").callAttr("create_live_audio",context.cacheDir.absolutePath).toString())
        val sources=listOf("batch-ui-a.mp3","batch-ui-b.mp3").map {File(context.cacheDir,it).apply {fixture.copyTo(this,overwrite=true)}}
        val originals=sources.map {it.readBytes()}
        val uris=sources.map {FileProvider.getUriForFile(context,"${context.packageName}.files",it)}
        val clip=ClipData.newRawUri("audio",uris[0]).apply {addItem(ClipData.Item(uris[1]))}
        val monitor=instrumentation.addMonitor(IntentFilter(Intent.ACTION_OPEN_DOCUMENT).apply {addDataType("*/*")},Instrumentation.ActivityResult(Activity.RESULT_OK,Intent().apply {clipData=clip}),true)
        val history=OndaStore.history.value.map {it.id}.toSet()
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            metadata()
            compose.onNodeWithText("Editar metadados em lote").performClick()
            compose.onNodeWithText("Escolher vários arquivos de áudio").performClick()
            compose.onNodeWithText("2 arquivos selecionados").assertIsDisplayed()
            compose.onNodeWithContentDescription("Álbum").performClick()
            compose.onNodeWithTag("batch-field-album").performScrollTo().performTextReplacement("Batch UI Album")
            compose.onNodeWithTag("batch-apply").performClick()
            compose.waitUntil(30000) {!vm.busy.value && vm.status.value=="2 arquivos salvos; 0 falhas."}
            val added=OndaStore.history.value.filter {it.id !in history}
            assertEquals(2,added.size)
            sources.zip(originals).forEach {(source,bytes)->assertArrayEquals(bytes,source.readBytes())}
            for(item in added) {
                val file=OndaStore.importDocument(android.net.Uri.parse(item.uri),"batch-ui-read")
                try {
                    val result=MobileEngine.call(context,"batch-ui-read-${item.id}","audio_read",JSONObject().put("source",file.absolutePath),EventCallback {})
                    assertEquals("Batch UI Album",result.getJSONObject("record").getString("album"))
                } finally {file.delete()}
            }
            compose.onNodeWithText("Fechar").performClick()
        } finally {
            instrumentation.removeMonitor(monitor)
            OndaStore.history.value.filter {it.id !in history}.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null);OndaStore.removeHistory(it.id)}
            sources.forEach {it.delete()};fixture.delete()
            compose.runOnIdle {OndaStore.saveSettings(settings)}
        }
    }
}
