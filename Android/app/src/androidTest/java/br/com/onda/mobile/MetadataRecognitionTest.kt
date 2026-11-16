package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MetadataRecognitionTest {
    @Test fun copiesFullTagsWithoutPuttingLargePayloadOnSystemClipboard() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        androidx.test.core.app.ActivityScenario.launch(MainActivity::class.java).use {
            val source=context.getExternalFilesDir(null)!!.resolve("Raebs Lament.mp3").absolutePath
            val output=MetadataClipboard.newCopyFile()
            val copied=MobileEngine.call(context,"copy-tags-test","audio_tags_copy",org.json.JSONObject().put("source",source).put("clipboard_path",output.absolutePath),EventCallback {})
            assertFalse(copied.toString(),copied.has("error"))
            // Valid JSON whitespace makes the payload exceed Android's Binder limit.
            output.appendText(" ".repeat(1100000))
            instrumentation.runOnMainSync {MetadataClipboard.publish(output.absolutePath)}
            var draft:java.io.File?=null
            instrumentation.runOnMainSync {
                assertTrue(MetadataClipboard.available())
                draft=MetadataClipboard.draft()
            }
            val pasted=MobileEngine.call(context,"paste-tags-test","audio_tags_paste",org.json.JSONObject().put("clipboard_path",draft!!.absolutePath),EventCallback {})
            assertFalse(pasted.toString(),pasted.has("error"))
            assertEquals("Raeb's Lament",pasted.getJSONObject("record").getString("title"))
            assertTrue(java.io.File(pasted.getString("cover_path")).isFile)
            instrumentation.runOnMainSync {
                (context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager).setPrimaryClip(android.content.ClipData.newPlainText("texto","comum"))
                assertFalse(MetadataClipboard.available())
            }
            listOf(output,draft!!,java.io.File(pasted.getString("cover_path"))).forEach {file->file.delete()}
        }
    }

    @Test fun identifiesSameLocalFileByNameAndCreatesChromaprint() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val py=Python.getInstance()
        val scope=py.getModule("builtins").callAttr("dict")
        scope.callAttr("__setitem__","source",context.getExternalFilesDir(null)!!.resolve("Raebs Lament.mp3").absolutePath)
        py.getModule("builtins").callAttr("exec","""
import json, threading
from audio_library import read_audio
from filename_metadata import search
from android_fingerprint import fingerprint
record=read_audio(source)
found=search({'source':source,'filename':'Raebs Lament.mp3','record':record},threading.Event())
diagnostic=json.dumps({'record':record,'anchor':found['anchor'],'warnings':found['warnings'],'count':len(found['candidates'])},ensure_ascii=False)
if not found['candidates']:
    raise AssertionError(diagnostic)
fp=fingerprint(source,threading.Event())
verified=len(fp['fingerprint'])>20 and fp['duration']>0
""".trimIndent(),scope)
        android.util.Log.i("ONDA-metadata-test",scope.callAttr("__getitem__","diagnostic").toString())
        assertTrue(scope.callAttr("__getitem__","verified").toBoolean())
    }

    @Test fun backendIdentifiesNameAndAudioWithCatalogConfirmation() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val source=context.getExternalFilesDir(null)!!.resolve("Raebs Lament.mp3").absolutePath
        val record=MobileEngine.call(context,"read-tags","audio_read",org.json.JSONObject().put("source",source),EventCallback {})
        assertFalse(record.toString(),record.has("error"))
        for(action in listOf("audio_name_lookup","audio_fingerprint_lookup")) {
            var confirmed=false
            val identity="metadata-$action"
            val result=MobileEngine.call(context,identity,action,org.json.JSONObject().put("source",source).put("filename","Raebs Lament.mp3").put("record",record.getJSONObject("record")),EventCallback {raw->
                val event=org.json.JSONObject(raw)
                if(event.optString("type")=="choose_catalog") {
                    confirmed=true
                    MobileEngine.reply(identity,org.json.JSONObject().put("selected_id",event.getJSONArray("candidates").getJSONObject(0).getString("source_url")))
                }
            })
            assertFalse(result.toString(),result.has("error"))
            assertTrue(result.toString(),confirmed)
            assertTrue(result.toString(),result.getJSONArray("matches").length()>0)
        }
    }
}
