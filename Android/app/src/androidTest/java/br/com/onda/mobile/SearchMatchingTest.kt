package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SearchMatchingTest {
    @Test fun sharedSearchInvariants() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val report=JSONObject(Python.getInstance().getModule("mobile_search_smoke").callAttr("verify",context.cacheDir.absolutePath).toString())
        assertTrue(report.getBoolean("success"))
        assertEquals(10,report.getInt("checks"))
    }
}
