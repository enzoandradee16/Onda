package br.com.onda.mobile
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class DownloadDefaultsTest {
    @Test fun independentDefaultsAndQueuePolicy() {
        assertFalse(OndaStore.defaults().getBoolean("simple_download_ui"));assertTrue(OndaStore.defaults().getBoolean("social_best_quality"))
        for(simple in listOf(false,true)) {
            val source=JSONObject().put("url","https://www.instagram.com/p/x").put("mode","mp3").put("simple_download_ui",simple).put("social_best_quality",true)
            val result=effectiveDownloadOptions(source)
            assertEquals("social",result.getString("mode"));assertTrue(result.isNull("height"));assertEquals("mp3",source.getString("mode"))
        }
        val source=JSONObject().put("url","https://open.spotify.com/track/x").put("mode","m4a").put("simple_download_ui",true)
        assertEquals("320 kbps",effectiveDownloadOptions(source).getString("audio_quality"))
        assertEquals("mp3",effectiveDownloadOptions(source).getString("mode"))
    }
    @Test fun operationsAndOtherHostsUnaffected() {
        val source=JSONObject().put("url","https://instagram.com.evil.test/x").put("mode","m4a").put("social_best_quality",true)
        assertEquals("m4a",effectiveDownloadOptions(source).getString("mode"))
        source.put("_operation","video_convert").put("simple_download_ui",true)
        assertEquals(source.toString(),effectiveDownloadOptions(source).toString())
    }
}
