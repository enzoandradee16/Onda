package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class MobileRuntimeTest {
    @Test fun nativeDownloadAndEffects() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val events=mutableListOf<JSONObject>()
        val callback=EventCallback {synchronized(events) {events+=JSONObject(it)}}
        val report=Python.getInstance().getModule("mobile_smoke").callAttr("verify",context.cacheDir.absolutePath,callback).toString()
        File(context.filesDir,"mobile-validation.json").writeText(report)
        println("ONDA_VALIDATION=$report")
        assertTrue(JSONObject(report).getBoolean("effects_tags_and_cover"))
        assertTrue(events.any {it.optString("type")=="done"})
        val source=File(JSONObject(report).getString("folder"),"Artista - Música - Slowed + Reverb.mp3")
        val config=OndaStore.config().put("folder",source.parent).put("duplicate_policy","keep")
        val first=OndaStore.publish(source.absolutePath,config,"mp3")
        try {
            context.contentResolver.openInputStream(first)!!.use {assertEquals(source.length(),it.readBytes().size.toLong())}
            val skipped=OndaStore.publish(source.absolutePath,JSONObject(config.toString()).put("duplicate_policy","skip"),"mp3")
            assertEquals(first,skipped)
        } finally {
            context.contentResolver.delete(first,null,null)
            OndaStore.clearHistory()
        }
    }
    @Test fun encryptedCredentialsAndQueuePersistence() {
        val key="instrumentation-${System.nanoTime()}"
        SecureVault.put(key,"fixture-secret")
        assertEquals("fixture-secret",SecureVault.get(key))
        SecureVault.remove(key)
        assertNull(SecureVault.get(key))
        val id=OndaStore.enqueue("https://example.com/fixture.mp4","Teste isolado")
        try {
            OndaStore.refresh()
            assertTrue(OndaStore.items.value.any {it.id==id})
            assertFalse(OndaStore.items.value.first {it.id==id}.config.has("spotify_client_secret"))
        } finally {OndaStore.remove(setOf(id))}
    }
    @Test fun spotifyAuthorizationReturn() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        assertTrue(Python.getInstance().getModule("mobile_smoke").callAttr("verify_spotify_return",EventCallback {}).toBoolean())
        val intent=spotifyBrowserIntent()
        assertTrue(intent.flags and android.content.Intent.FLAG_ACTIVITY_NO_HISTORY != 0)
        val link=android.content.Intent(android.content.Intent.ACTION_VIEW,android.net.Uri.parse("onda://spotify-return")).setPackage(context.packageName)
        assertNotNull(context.packageManager.resolveActivity(link,0))
    }
}
