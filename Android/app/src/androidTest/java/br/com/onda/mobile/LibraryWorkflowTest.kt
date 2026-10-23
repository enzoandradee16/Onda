package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class LibraryWorkflowTest {
    @Test fun duplicateQueueCanSkipAndConfirmWithoutDownloading() {
        val settings=JSONObject(OndaStore.settings.value.toString())
        val url="https://example.com/"+UUID.randomUUID()
        val options=JSONObject(settings.toString()).put("detect_duplicates",true)
        val first=OndaStore.enqueue(url,options=options)
        var second=""
        try {
            second=OndaStore.enqueue(url+"?utm_source=share",options=options)
            assertEquals("Duplicata",OndaStore.items.value.first {it.id==second}.state)
            assertEquals("choose_queue_duplicate",OndaStore.question.value!!.event.getString("type"))
            OndaStore.answer(JSONObject().put("cancel",true))
            assertFalse(OndaStore.items.value.any {it.id==second})
            second=OndaStore.enqueue(url,options=options)
            OndaStore.answer(JSONObject().put("add",true))
            assertEquals("Pendente",OndaStore.items.value.first {it.id==second}.state)
        } finally {OndaStore.dismissQuestions("duplicate-$second");OndaStore.remove(setOf(first,second))}
    }

    @Test fun duplicateDetectionUsesPublishedSourceAcrossQueueRemoval() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val config=OndaStore.config().put("url","https://example.com/"+UUID.randomUUID()).put("duplicate_policy","keep").put("detect_duplicates",true)
        val file=File(config.getString("folder"),"history-duplicate-${UUID.randomUUID()}.mp3")
        file.parentFile!!.mkdirs();file.writeBytes(byteArrayOf(1,2,3))
        val uri=OndaStore.publish(file.absolutePath,config,"mp3")
        var id=""
        try {
            id=OndaStore.enqueue(config.getString("url"),options=config)
            assertEquals("Duplicata",OndaStore.items.value.first {it.id==id}.state)
            OndaStore.answer(JSONObject().put("cancel",true))
        } finally {
            OndaStore.dismissQuestions("duplicate-$id");OndaStore.remove(setOf(id))
            context.contentResolver.delete(uri,null,null)
            OndaStore.history.value.filter {it.uri==uri.toString()}.forEach {OndaStore.removeHistory(it.id)}
        }
    }

    @Test fun batchCopyPreservesOriginalAndUnselectedTags() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val source=File(Python.getInstance().getModule("mobile_smoke").callAttr("create_live_audio",context.cacheDir.absolutePath).toString())
        val tags=Python.getInstance().getModule("json").callAttr("loads","{\"title\":\"Batch original title\"}")
        Python.getInstance().getModule("audio_library").callAttr("write_audio",source.absolutePath,tags)
        val original=source.readBytes()
        val first=MobileEngine.call(context,"batch-read-before","audio_read",JSONObject().put("source",source.absolutePath),EventCallback {})
        val config=OndaStore.config().put("sources",JSONArray().put(JSONObject().put("source",source.absolutePath).put("output_name","Batch fixture")))
            .put("changes",JSONObject().put("album","Batch album"))
        val outputs=mutableListOf<File>()
        try {
            val result=MobileEngine.call(context,"batch-fixture","audio_batch_edit",config,EventCallback {raw->
                val event=JSONObject(raw)
                if(event.optString("type")=="file")outputs.add(File(event.getString("path")))
            })
            assertFalse(result.toString(),result.has("error"));assertEquals(0,result.getJSONArray("errors").length());assertEquals(1,outputs.size)
            assertArrayEquals(original,source.readBytes())
            val after=MobileEngine.call(context,"batch-read-after","audio_read",JSONObject().put("source",outputs.single().absolutePath),EventCallback {}).getJSONObject("record")
            assertEquals("Batch album",after.getString("album"));assertEquals(first.getJSONObject("record").getString("title"),after.getString("title"))
        } finally {outputs.forEach {it.delete()};source.delete()}
    }
    @Test fun failedQueueItemCanBeAddedAgainWithoutDuplicateQuestion() {
        val options=JSONObject(OndaStore.settings.value.toString()).put("detect_duplicates",true)
        val url="https://example.com/"+UUID.randomUUID()
        val first=OndaStore.enqueue(url,options=options)
        var second=""
        try {
            OndaStore.update(first,"Erro")
            second=OndaStore.enqueue(url,options=options)
            assertEquals("Pendente",OndaStore.items.value.first {it.id==second}.state)
        } finally {OndaStore.dismissQuestions("duplicate-$second");OndaStore.remove(setOf(first,second))}
    }
    @Test fun duplicateCanResolveMetadataWhileWaitingForConfirmation() {
        val options=JSONObject(OndaStore.settings.value.toString()).put("detect_duplicates",true)
        val url="https://example.com/"+UUID.randomUUID()
        val first=OndaStore.enqueue(url,options=options)
        val second=OndaStore.enqueue(url,options=options)
        try {
            assertTrue(OndaStore.renamePendingLink(second,url,"Artist - Track",JSONObject().put("title","Track")))
            val item=OndaStore.items.value.first {it.id==second}
            assertEquals("Artist - Track",item.title)
            assertEquals("Duplicata",item.state)
            assertEquals("Track",item.config.getJSONObject("queue_info").getString("title"))
        } finally {OndaStore.dismissQuestions("duplicate-$second");OndaStore.remove(setOf(first,second))}
    }
    @Test fun duplicateOptionsKeepQualitiesAndCollectionsIndependent() {
        val first=JSONObject().put("url","https://youtube.com/watch?v=one&list=abc").put("mode","mp3").put("playlist",true)
        assertTrue(duplicateJob(first,JSONObject(first.toString()).put("url","https://youtube.com/watch?v=two&list=abc")))
        assertFalse(duplicateJob(first,JSONObject(first.toString()).put("audio_quality","192")))
        assertFalse(duplicateJob(first,JSONObject(first.toString()).put("playlist_title","Other collection")))
        val generic=JSONObject(first.toString()).put("url","https://example.com/one?list=abc")
        assertFalse(duplicateJob(generic,JSONObject(generic.toString()).put("url","https://example.com/two?list=abc")))
    }

    @Test fun batchClearsOnlySelectedFieldsAndSkipsRepeatedSource() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val source=File(Python.getInstance().getModule("mobile_smoke").callAttr("create_live_audio",context.cacheDir.absolutePath).toString())
        val tags=Python.getInstance().getModule("json").callAttr("loads",JSONObject().put("title","Keep title").put("album","Clear album").toString())
        Python.getInstance().getModule("audio_library").callAttr("write_audio",source.absolutePath,tags)
        val before=source.readBytes();val outputs=mutableListOf<File>()
        try {
            val entry=JSONObject().put("source",source.absolutePath)
            val config=OndaStore.config().put("sources",JSONArray().put(entry).put(entry)).put("changes",JSONObject().put("album",""))
            val result=MobileEngine.call(context,"batch-clear","audio_batch_edit",config,EventCallback {raw->
                val event=JSONObject(raw);if(event.optString("type")=="file")outputs.add(File(event.getString("path")))
            })
            assertFalse(result.toString(),result.has("error"));assertEquals(1,outputs.size)
            val after=MobileEngine.call(context,"batch-clear-read","audio_read",JSONObject().put("source",outputs.single().absolutePath),EventCallback {}).getJSONObject("record")
            assertEquals("",after.getString("album"));assertEquals("Keep title",after.getString("title"))
            assertArrayEquals(before,source.readBytes())
        } finally {outputs.forEach {it.delete()};source.delete()}
    }

    @Test fun invalidBatchCoverDoesNotOverwriteOriginal() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val source=File(Python.getInstance().getModule("mobile_smoke").callAttr("create_live_audio",context.cacheDir.absolutePath).toString())
        val cover=File(context.cacheDir,"invalid-batch-cover.jpg");cover.writeText("not an image")
        val before=source.readBytes()
        try {
            val config=OndaStore.config().put("sources",JSONArray().put(JSONObject().put("source",source.absolutePath)))
                .put("changes",JSONObject()).put("cover_path",cover.absolutePath).put("overwrite_original",true)
            val result=MobileEngine.call(context,"batch-invalid-cover","audio_batch_edit",config,EventCallback {})
            assertFalse(result.toString(),result.has("error"));assertEquals(1,result.getJSONArray("errors").length())
            assertEquals(0,result.getJSONArray("results").length());assertArrayEquals(before,source.readBytes())
        } finally {source.delete();cover.delete()}
    }
    @Test fun organizationRulesUseSafeFoldersAndTrackNamesInAndroidEngine() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val py=Python.getInstance();val json=py.getModule("json")
        val record=json.callAttr("loads",JSONObject().put("title","../../Song").put("artists",JSONArray().put("../Artist"))
            .put("album","../Album").put("genre","../Genre").put("release_date","2026-01-01").put("track_number","2/10").put("disc_number",3).toString())
        val root=File(context.cacheDir,"organization-test").canonicalFile
        val folders=listOf("Álbum","Artista / Ano - Álbum","Gênero / Artista / Álbum","Formato / Artista / Álbum")
        folders.forEach {organization->
            val config=json.callAttr("loads",JSONObject().put("folder",root.absolutePath).put("organization",organization).put("mode","flac").toString())
            val result=File(py.getModule("file_output").callAttr("destination",config,record).toString()).canonicalFile
            assertTrue(result.path,result.path.startsWith(root.path+File.separator))
        }
        val clean=json.callAttr("loads",JSONObject().put("title","Song").put("track_number","2/10").put("disc_number",3).toString())
        val config=json.callAttr("loads",JSONObject().put("filename_template","Disco-Faixa - Música").toString())
        assertEquals("3-02 - Song.flac",py.getModule("output_rules").callAttr("output_filename","old.flac",config,clean).toString())
    }
}
