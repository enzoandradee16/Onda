package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Optional network checks: pass -e liveNetwork true to the instrumentation runner. */
@RunWith(AndroidJUnit4::class)
class LiveCatalogTest {
    @Test fun publicCatalogs() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("liveNetwork")=="true")
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val report=JSONObject()
        for(provider in listOf("Apple / iTunes","Deezer")) {
            val result=MobileEngine.call(context,"live-$provider","search",JSONObject().put("query","Stardust Music Sounds Better With You").put("provider",provider),EventCallback {})
            assertFalse(result.toString(),result.has("error"))
            assertTrue(result.toString(),result.getJSONArray("tracks").length()>0)
            val track=result.getJSONArray("tracks").getJSONObject(0)
            assertTrue(track.getString("title").isNotBlank())
            assertTrue(track.getString("cover_url").startsWith("https://"))
            report.put(provider,JSONObject().put("results",result.getJSONArray("tracks").length()).put("title",track.getString("title")))
        }
        java.io.File(context.filesDir,"live-validation.json").writeText(report.toString(2))
    }
    @Test fun youtubeMetadata() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("liveYoutube")=="true")
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val youtube=MobileEngine.call(context,"live-youtube","describe",JSONObject().put("url","https://www.youtube.com/watch?v=jNQXAC9IVRw"),EventCallback {})
        assertFalse(youtube.toString(),youtube.has("error"))
        assertTrue(youtube.toString(),youtube.optString("title").isNotBlank())
        java.io.File(context.filesDir,"youtube-validation.json").writeText(youtube.toString(2))
    }
    @Test fun spotifyWithoutApi() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("liveSpotify")=="true")
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val callback=EventCallback {raw->
            val event=JSONObject(raw)
            if(event.optString("type")=="choose_catalog") {
                val candidate=event.getJSONArray("candidates").getJSONObject(0)
                MobileEngine.reply("live-spotify",JSONObject().put("selected_id",candidate.getString("source_url")))
            }
        }
        val result=MobileEngine.call(context,"live-spotify","search",JSONObject().put("query","https://open.spotify.com/track/6xXEw4y39shgIp6pacKQFH"),callback)
        assertFalse(result.toString(),result.has("error"))
        assertEquals(1,result.getJSONArray("tracks").length())
        val track=result.getJSONArray("tracks").getJSONObject(0)
        assertTrue(track.optString("cover_url").isNotBlank())
        java.io.File(context.filesDir,"spotify-validation.json").writeText(JSONObject().put("title",track.getString("title")).put("platform",track.getString("platform")).toString(2))
    }
}
