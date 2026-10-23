package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class StoreOptimizationTest {
    @Test fun queueMutationsPreserveActiveProgressAndDoNotReloadHistory() {
        val id=OndaStore.enqueue("https://example.com/a.mp3")
        val history=OndaStore.history.value
        val added=mutableListOf<String>()
        try {
            OndaStore.update(id,"Baixando",.42f,"42%")
            added+=OndaStore.enqueue("https://example.com/b.mp3")
            OndaStore.enqueueBatch {repeat(100) {added+=OndaStore.enqueue("https://example.com/$it.mp3")}}
            OndaStore.remove(added.toSet())
            OndaStore.refresh()
            val item=OndaStore.items.value.first {it.id==id}
            assertEquals(.42f,item.progress)
            assertEquals("42%",item.message)
            assertFalse(item.config.has("spotify_client_secret"))
            assertEquals(history,OndaStore.history.value)
            OndaStore.active.value=id
            OndaStore.remove(setOf(id))
            assertTrue(OndaStore.items.value.any {it.id==id})
        } finally {OndaStore.active.value="";OndaStore.remove((added+id).toSet())}
    }
    @Test fun abortedBatchRollsBackWithoutPublishingPartialQueue() {
        val before=OndaStore.items.value.map {it.id}
        try {
            OndaStore.enqueueBatch {OndaStore.enqueue("https://example.com/rollback");error("fixture")}
            fail("Expected rollback")
        } catch(expected:IllegalStateException) {assertEquals("fixture",expected.message)}
        OndaStore.refresh()
        assertEquals(before,OndaStore.items.value.map {it.id})
    }
    @Test fun exportedOwnedStagingCopyIsRemovedButPublishedBytesRemain() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val config=OndaStore.config().put("duplicate_policy","keep").put("output_uri","")
        val file=File(config.getString("folder"),"optimization-${System.nanoTime()}.mp3")
        file.parentFile!!.mkdirs()
        val data=ByteArray(8192) {(it%127).toByte()}
        file.writeBytes(data)
        val uri=OndaStore.publish(file.absolutePath,config,"mp3")
        try {
            context.contentResolver.openInputStream(uri)!!.use {assertArrayEquals(data,it.readBytes())}
            assertEquals(android.os.Build.VERSION.SDK_INT<29,file.exists())
        } finally {context.contentResolver.delete(uri,null,null);file.delete();OndaStore.history.value.firstOrNull {it.uri==uri.toString()}?.let {OndaStore.removeHistory(it.id)}}
    }
    @Test fun largeMatchMergePreservesOrderingUnmatchedAndFirstDuplicate() {
        val tracks=(0 until 2000).map {JSONObject().put("source_url","track-$it").put("title","old-$it")}
        val matches=tracks.filterIndexed {index,_->index%2==0}.map {JSONObject(it.toString()).put("title","matched")}
        val result=mergeTrackMatches(tracks,matches+JSONObject(matches.first().toString()).put("title","wrong duplicate"))
        assertEquals(2000,result.size)
        result.forEachIndexed {index,row->
            assertEquals("track-$index",row.getString("source_url"))
            assertEquals(if(index%2==0) "matched" else "old-$index",row.getString("title"))
        }
    }
}
