package br.com.onda.mobile

import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test

class VideoLimitsTest {
    @Test fun nativeVideoLimitsPreserveAudioAndAvoidRepeatedConversion() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val report=Python.getInstance().getModule("mobile_video_limits_smoke").callAttr("verify",context.cacheDir.absolutePath).toString()
        println("ONDA_VIDEO_LIMITS=$report")
        val rows=JSONArray(report)
        assertEquals(2,rows.length())
        for(index in 0 until rows.length()) {
            val row=rows.getJSONObject(index)
            assertEquals(480,minOf(row.getInt("width"),row.getInt("height")))
            assertTrue(row.getDouble("fps")<=24.01)
            assertEquals("aac",row.getString("audio"))
        }
    }
}
