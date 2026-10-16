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

@RunWith(AndroidJUnit4::class)
class VideoConverterTest {
    @get:Rule val compose=createComposeRule()
    @Test fun nativeConverterExportsAllThreeFormatsAndPreservesInput() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val result=JSONObject(Python.getInstance().getModule("video_converter_smoke").callAttr("verify",context.cacheDir.absolutePath).toString())
        assertTrue(result.getBoolean("success"));assertTrue(result.getBoolean("original_preserved"))
        assertEquals(3,result.getJSONArray("formats").length())
    }
    @Test fun converterHasOwnTabAndRequiresAnInput() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        assertTrue("Conversor de vídeos" in OndaStore.defaults().getJSONArray("tab_order").let {a->(0 until a.length()).map {a.getString(it)}})
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        compose.setContent {MaterialTheme {VideoConverterPage(vm)}}
        compose.onNodeWithTag("converter-choose").assertExists()
        compose.onNodeWithTag("converter-start").assertIsNotEnabled()
    }
}
