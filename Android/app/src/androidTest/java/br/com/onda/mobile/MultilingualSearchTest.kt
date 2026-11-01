package br.com.onda.mobile

import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class MultilingualSearchTest {
    @Test fun sharedSearchHandlesKanaAndProtectsOtherScriptsAndRecordings() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val report=JSONObject(Python.getInstance().getModule("multilingual_search_smoke").callAttr("verify").toString())
        assertTrue(report.getBoolean("kana"))
        assertTrue(report.getBoolean("multilingual"))
        assertTrue(report.getBoolean("recording_guards"))
    }
}
