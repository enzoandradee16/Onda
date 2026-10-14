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
class MetadataOverwriteTest {
    @Test fun editingReplacesTheSameUriAndKeepsOneHistoryEntry() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val source=File(module.callAttr("create_live_audio",context.cacheDir.absolutePath).toString())
        val uri=OndaStore.publish(source.absolutePath,OndaStore.config().put("duplicate_policy","keep"),"mp3")
        val before=OndaStore.history.value.filter {it.uri==uri.toString()}
        val imported=OndaStore.importDocument(uri,"overwrite-test")
        var edited:File?=null
        try {
            val config=OndaStore.config().put("source",imported.absolutePath).put("original_uri",uri.toString())
                .put("overwrite_original",true).put("edit_metadata",true)
                .put("changes",JSONObject().put("title","Título corrigido no original"))
            val events=mutableListOf<JSONObject>()
            val result=MobileEngine.call(context,"overwrite-test","audio_edit",config,EventCallback {events+=JSONObject(it)})
            assertFalse(result.toString(),result.has("error"))
            assertFalse("An edited copy must not be published",events.any {it.optString("type")=="file"})
            edited=File(result.getString("path"))
            OndaStore.overwriteAudio(edited,config)
            assertEquals(before.map {it.id},OndaStore.history.value.filter {it.uri==uri.toString()}.map {it.id})
            val saved=OndaStore.importDocument(uri,"overwrite-readback")
            try {
                val read=MobileEngine.call(context,"overwrite-read","audio_read",JSONObject().put("source",saved.absolutePath),EventCallback {})
                assertEquals("Título corrigido no original",read.getJSONObject("record").getString("title"))
            } finally {saved.delete()}
            assertEquals(edited.length(),OndaStore.history.value.first {it.uri==uri.toString()}.size)
        } finally {
            context.contentResolver.delete(uri,null,null)
            before.forEach {OndaStore.removeHistory(it.id)}
            source.delete();imported.delete();edited?.delete()
        }
    }
    @Test fun duplicateReplacementKeepsTheExistingUri() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val source=File(context.getExternalFilesDir(null),"Onda Downloads/duplicate-safe-test.mp3")
        source.parentFile!!.mkdirs();source.writeText("original")
        val config=OndaStore.config().put("duplicate_policy","keep")
        val uri=OndaStore.publish(source.absolutePath,config,"mp3")
        try {
            source.writeText("replacement")
            val result=OndaStore.publish(source.absolutePath,JSONObject(config.toString()).put("duplicate_policy","replace"),"mp3")
            assertEquals(uri,result)
            assertEquals("replacement",context.contentResolver.openInputStream(uri)!!.use {String(it.readBytes())})
        } finally {
            context.contentResolver.delete(uri,null,null)
            OndaStore.history.value.filter {it.uri==uri.toString()}.forEach {OndaStore.removeHistory(it.id)}
            source.delete()
        }
    }
    @Test fun aChangedOriginalIsPreservedInsteadOfBeingOverwritten() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val source=File(context.cacheDir,"overwrite-original-test.mp3").apply {writeText("original")}
        val uri=OndaStore.publish(source.absolutePath,OndaStore.config().put("duplicate_policy","keep"),"mp3")
        val imported=OndaStore.importDocument(uri,"overwrite-conflict")
        val edited=File(context.cacheDir,"overwrite-edited-test.mp3").apply {writeText("edited")}
        try {
            context.contentResolver.openOutputStream(uri,"wt")!!.use {it.write("external-change".toByteArray())}
            try {replaceAudioOriginal(context,uri,imported,edited);fail("Expected a concurrent edit conflict")}
            catch(error:IllegalArgumentException) {assertTrue(error.message!!.contains("mudou durante"))}
            assertEquals("external-change",context.contentResolver.openInputStream(uri)!!.use {String(it.readBytes())})
        } finally {
            context.contentResolver.delete(uri,null,null)
            OndaStore.history.value.filter {it.uri==uri.toString()}.forEach {OndaStore.removeHistory(it.id)}
            source.delete();imported.delete();edited.delete()
        }
    }
}
