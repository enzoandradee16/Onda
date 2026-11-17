package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.core.content.FileProvider
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class MetadataEditingFlowTest {
    @Test fun previewDoesNotWriteAndUndoRestoresOriginalContentUri() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val py=Python.getInstance()
        val source=File(context.filesDir,"metadata-flow.wav")
        val scope=py.getModule("builtins").callAttr("dict")
        scope.callAttr("__setitem__","source",source.absolutePath)
        py.getModule("builtins").callAttr("exec","""
import wave
from audio_library import write_audio
with wave.open(source,'wb') as output:
    output.setparams((1,2,8000,0,'NONE',''))
    output.writeframes(b'\x01\x00'*800)
write_audio(source,{'title':'Antes','artists':['Artista']})
""".trimIndent(),scope)
        val uri=FileProvider.getUriForFile(context,context.packageName+".files",source)
        val staged=OndaStore.importDocument(uri,"audio-editor")
        val identity="metadata-flow"
        var sawPreview=false
        val config=JSONObject().put("source",staged.absolutePath).put("output_name","metadata-flow")
            .put("folder",context.getExternalFilesDir(null)!!.resolve("Onda Downloads").absolutePath)
            .put("overwrite_original",true).put("original_uri",uri.toString()).put("edit_metadata",true)
            .put("changes",JSONObject().put("title","Depois"))
        val result=MobileEngine.call(context,identity,"audio_edit",config,EventCallback {raw->
            val event=JSONObject(raw)
            if(event.optString("type")=="review_metadata_changes") {
                sawPreview=true
                assertEquals("Antes",py.getModule("audio_library").callAttr("read_audio",source.absolutePath).callAttr("__getitem__","title").toString())
                val selected=JSONObject();event.getJSONArray("entries").objects().forEachIndexed {i,row->selected.put(i.toString(),JSONArray(row.getJSONArray("fields").objects().map {it.getString("key")}))}
                MobileEngine.reply(identity,JSONObject().put("selected",selected))
            }
        })
        assertTrue(sawPreview);assertFalse(result.toString(),result.has("error"))
        val edited=File(result.getString("path"))
        OndaStore.overwriteAudio(edited,config);MetadataUndo.record(result,uri.toString())
        assertTrue(MetadataUndo.available.value)
        val cleared=MobileEngine.call(context,"cache-before-undo","cache_clear",JSONObject(),EventCallback {})
        assertFalse(cleared.toString(),cleared.has("error"));MetadataUndo.refresh();assertTrue(MetadataUndo.available.value)
        assertEquals("Depois",py.getModule("audio_library").callAttr("read_audio",source.absolutePath).callAttr("__getitem__","title").toString())
        assertEquals(1,MetadataUndo.restore())
        assertEquals("Antes",py.getModule("audio_library").callAttr("read_audio",source.absolutePath).callAttr("__getitem__","title").toString())
        assertFalse(MetadataUndo.available.value)
        staged.delete();edited.delete();source.delete()
    }

    @Test fun cacheReportCountsEffectsAndProtectsPreparedAudio() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val id=java.security.MessageDigest.getInstance("SHA-256").digest(java.util.UUID.randomUUID().toString().toByteArray()).joinToString(""){"%02x".format(it.toInt() and 255)}
        val group=File(context.filesDir,"jukebox/$id").apply {mkdirs()}
        try {
            File(group,"audio.wav").writeBytes(ByteArray(100))
            File(group,"effects-85-0-False.wav").writeBytes(ByteArray(60))
            File(group,"analysis.json").writeText("{\"title\":\"Música de verificação\"}")
            val protected=JSONArray(listOf(group.absolutePath))
            val config=JSONObject().put("_stream_cache_protected",protected)
            val report=MobileEngine.call(context,"cache-report-test","cache_report",config,EventCallback {})
            assertFalse(report.toString(),report.has("error"))
            assertTrue(report.getJSONArray("tracks").objects().first {it.getString("id")==id}.getBoolean("protected"))
            assertTrue(report.getJSONArray("categories").objects().first {it.getString("name")=="Efeitos"}.getLong("bytes")>=60)
            val cleared=MobileEngine.call(context,"cache-clear-test","cache_clear",config,EventCallback {})
            assertFalse(cleared.toString(),cleared.has("error"));assertTrue(File(group,"audio.wav").exists())
        } finally {
            assertEquals(File(context.filesDir,"jukebox").canonicalFile,group.canonicalFile.parentFile)
            group.deleteRecursively()
        }
    }
}
