package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class QueueNavigationTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before() {
            if(android.os.Build.VERSION.SDK_INT>=33) {
                val instrumentation=InstrumentationRegistry.getInstrumentation()
                instrumentation.uiAutomation.grantRuntimePermission(instrumentation.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()
    private fun ready() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
    }
    private fun navigate(name:String) {
        if(name=="Links e fila") {
            compose.onNodeWithTag("nav-Fila").performClick()
            compose.onNodeWithContentDescription("Adicionar links").performClick()
        } else {
            compose.onNodeWithTag("nav-Mais").performClick()
            compose.onNodeWithTag("more-${tabLabel(name)}").performClick()
        }
    }
    private fun fixture(test:(OndaViewModel,JSONObject)->Unit) {
        ready()
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val saved=JSONObject(OndaStore.settings.value.toString())
        val existing=OndaStore.items.value.map {it.id}.toSet()
        val history=OndaStore.history.value.map {it.uri}.toSet()
        MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val fixture=JSONObject(module.callAttr("start_fixture",context.cacheDir.absolutePath).toString())
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(saved.toString()).put("language","pt-BR").put("mode","mp4").put("schedule_enabled",false).put("detect_duplicates",false))}
            test(vm,fixture)
        } finally {
            DownloadService.stop(context)
            compose.waitUntil(15000) {!DownloadRuntime.running.get() && !vm.addingToQueue.value}
            OndaStore.remove(OndaStore.items.value.filter {it.id !in existing}.map {it.id}.toSet())
            OndaStore.history.value.filter {it.uri !in history}.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null)}
            compose.runOnIdle {vm.collection.value=JSONObject();OndaStore.saveSettings(saved)}
            module.callAttr("stop_fixture")
        }
    }
    @Test fun linksAddClosesSheetWithoutStartingAndNowStartsFromDownloads()=fixture {vm,data->
        navigate("Links e fila")
        compose.onNodeWithTag("queue-count").assertDoesNotExist()
        compose.onNodeWithTag("links-input").performTextInput(data.getString("url"))
        compose.onNodeWithTag("links-add").performScrollTo().performClick()
        compose.waitUntil(10000) {!vm.addingToQueue.value}
        compose.onNodeWithTag("links-input").assertDoesNotExist()
        assertFalse(DownloadRuntime.running.get())
        navigate("Links e fila")
        compose.onNodeWithTag("links-input").performScrollTo().performTextInput(data.getString("url"))
        compose.onNodeWithTag("links-download").performScrollTo().performClick()
        compose.waitUntil(15000) {compose.onAllNodesWithTag("links-input").fetchSemanticsNodes().isEmpty() && OndaStore.items.value.any {it.config.optString("url")==data.getString("url") && it.state in setOf("Baixando","Concluído","Erro","Aguardando escolha")}}
        compose.onNodeWithTag("links-input").assertDoesNotExist()
        assertTrue(OndaStore.items.value.any {it.config.optString("url")==data.getString("url")})
    }
    @Test fun collectionNowStartsAndOpensDedicatedQueue()=fixture {vm,data->
        compose.runOnIdle {vm.collection.value=JSONObject().put("title","Queue navigation fixture").put("tracks",JSONArray().put(JSONObject().put("source_url",data.getString("url")).put("title","Navigation fixture track").put("artists",JSONArray().put("Fixture artist"))))}
        navigate("Playlists / Álbuns")
        compose.onNodeWithText("Navigation fixture track").performScrollTo().performClick()
        compose.onNodeWithText("Baixar agora").performScrollTo().performClick()
        compose.waitUntil(15000) {compose.onAllNodesWithTag("links-input").fetchSemanticsNodes().isEmpty() && OndaStore.items.value.any {it.config.optString("url")==data.getString("url") && it.state in setOf("Baixando","Concluído","Erro","Aguardando escolha")}}
        compose.onNodeWithTag("links-input").assertDoesNotExist()
        assertTrue(OndaStore.items.value.any {it.config.optString("url")==data.getString("url")})
    }
}
