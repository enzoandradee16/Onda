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
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class MetadataTabTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before() {
            if(android.os.Build.VERSION.SDK_INT>=33) {
                val i=InstrumentationRegistry.getInstrumentation()
                i.uiAutomation.grantRuntimePermission(i.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()
    private fun ready() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
    }
    @Test fun localFileOutsideHistoryCanBeEditedAndReplacedFromNewTab() {
        ready()
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        MobileEngine.initialize(context)
        val source=File(Python.getInstance().getModule("mobile_smoke").callAttr("create_live_audio",context.cacheDir.absolutePath).toString())
        val uri=FileProvider.getUriForFile(context,"${context.packageName}.files",source)
        val before=OndaStore.history.value.map {it.id}
        val monitor=instrumentation.addMonitor(IntentFilter(Intent.ACTION_OPEN_DOCUMENT).apply {addDataType("*/*")},Instrumentation.ActivityResult(Activity.RESULT_OK,Intent().setData(uri)),true)
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithTag("tab-Metadados").performScrollTo().performClick()
            compose.onNodeWithText("Escolher arquivo de áudio").performClick()
            compose.waitUntil(20000) {compose.onAllNodes(hasText("Salvar cópia editada") and isEnabled()).fetchSemanticsNodes().isNotEmpty() && !vm.busy.value}
            compose.onNodeWithText("Música").performScrollTo().performTextReplacement("Editado fora do histórico")
            compose.onAllNodes(isDialog()).assertCountEquals(0)
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithTag("tab-Histórico").performClick()
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithTag("tab-Metadados").performScrollTo().performClick()
            compose.waitUntil(10000) {compose.onAllNodesWithText("Editado fora do histórico").fetchSemanticsNodes().isNotEmpty()}
            compose.onNodeWithText("Música").performScrollTo().assertTextContains("Editado fora do histórico")
            compose.onNodeWithText("Sobrescrever arquivo original").performScrollTo().performClick()
            compose.onNodeWithText("Salvar no original").performScrollTo().performClick()
            compose.waitUntil(30000) {vm.status.value=="Arquivo original atualizado."}
            compose.onNodeWithTag("app-status").assertTextEquals("Arquivo original atualizado.").assertIsDisplayed()
            assertEquals(before,OndaStore.history.value.map {it.id})
            val result=MobileEngine.call(context,"local-read","audio_read",JSONObject().put("source",source.absolutePath),EventCallback {})
            assertEquals("Editado fora do histórico",result.getJSONObject("record").getString("title"))
        } finally {instrumentation.removeMonitor(monitor);source.delete()}
    }
    @Test fun collectionCardAndTracksAreShownAndOldTabOrderGetsMetadata() {
        ready()
        val before=JSONObject(OndaStore.settings.value.toString())
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            compose.runOnIdle {
                OndaStore.saveSettings(JSONObject(before.toString()).put("tab_order",JSONArray(listOf("Imagens","Pesquisar","Links e fila","Playlists / Álbuns","Histórico","Efeitos"))))
                assertEquals("Metadados",OndaStore.settings.value.getJSONArray("tab_order").getString(7))
                vm.collection.value=JSONObject().put("title","Álbum de teste").put("subtitle","Artista de teste").put("kind","album")
                    .put("tracks",JSONArray().put(JSONObject().put("title","Primeira música").put("artists",JSONArray().put("Artista")).put("source_url","https://example.com/song")))
            }
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithTag("tab-Playlists / Álbuns").performClick()
            compose.onNodeWithTag("collection-card").performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("Álbum de teste").assertIsDisplayed()
            compose.onNodeWithText("Artista de teste").assertIsDisplayed()
            compose.onNodeWithText("Álbum · 1 músicas").assertIsDisplayed()
            compose.onNodeWithText("Primeira música").performScrollTo().assertIsDisplayed()
        } finally {compose.runOnIdle {OndaStore.saveSettings(before);vm.collection.value=JSONObject()}}
    }
}
