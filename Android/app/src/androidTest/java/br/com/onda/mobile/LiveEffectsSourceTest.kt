package br.com.onda.mobile

import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Test
import org.junit.Assert.*

class LiveEffectsSourceTest {
    @Test fun inspectRealSource() {
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("live_stream") == "true")
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        MobileEngine.initialize(context)
        val query = InstrumentationRegistry.getArguments().getString("query") ?: "Moonlight on The River"
        val found = MobileEngine.call(context, "live-search", "search", OndaStore.config().put("query", query).put("provider", "Apple / iTunes"), EventCallback {})
        val record = found.getJSONArray("tracks").getJSONObject(0)
        val model = MobileEngine.call(context, "live-resolve", "jukebox_prepare", OndaStore.config().put("record", record).put("stream", true), EventCallback {})
        check(!model.has("error")) { model.optString("error") }
        val cached = MobileEngine.call(context, "live-cache", "jukebox_stream_cache", OndaStore.config().put("model", model), EventCallback {})
        check(!cached.has("error")) { cached.optString("error") }
        assertTrue(java.io.File(cached.getString("path")).isFile)
        val prepared = MobileEngine.call(context, "live-transfer", "jukebox_transfer_prepare", OndaStore.config().put("model", model), EventCallback {})
        check(!prepared.has("error")) { prepared.optString("error") }
        val effects = MobileEngine.call(context, "live-effects", "jukebox_effects", OndaStore.config()
            .put("cache", prepared.getString("cache"))
            .put("effects", JSONObject().put("enabled", true).put("speed", 85).put("reverb", 25).put("pitch_shift", 0)), EventCallback {})
        check(!effects.has("error")) { effects.optString("error") }
        assertEquals("", effects.optString("error_detail"))
        assertTrue(java.io.File(prepared.getString("cache"), "effects-85-25-False.wav").isFile)
        android.util.Log.i("ONDA-live-effects", "Cache, preparation and Slowed/reverb passed: " + record.optString("title"))
    }
}
