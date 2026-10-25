package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class StorageRegressionTest {
    @Test fun lyricsCollisionsAndFailedCollectionItems() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        assertTrue(Python.getInstance().getModule("mobile_advanced_smoke")
            .callAttr("verify_storage",context.cacheDir.absolutePath).toBoolean())
    }
}
