package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class ToolsStorageTest {
    @Test fun savedCollectionsSurviveReloadAndConcurrentChanges()=runBlocking {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        assumeTrue(context.packageName.endsWith(".uitest"))
        OndaStore.initialize(context)
        val previous=CollectionsLibrary.read()
        val first=JSONObject().put("title","First").put("_collection_url","https://example.com/one")
        val second=JSONObject().put("title","Second").put("_collection_url","https://example.com/two")
        try {
            CollectionsLibrary.write(emptyList())
            val a=async {CollectionsLibrary.save(first)};val b=async {CollectionsLibrary.save(second)};a.await();b.await()
            assertEquals(2,CollectionsLibrary.read().size)
            CollectionsLibrary.save(JSONObject(first.toString()).put("title","Updated"))
            assertEquals(2,CollectionsLibrary.read().size)
            assertEquals("Updated",CollectionsLibrary.read().first {CollectionsLibrary.identity(it)==CollectionsLibrary.identity(first)}.optString("title"))
            CollectionsLibrary.remove(second)
            assertEquals(listOf("Updated"),CollectionsLibrary.read().map {it.optString("title")})
        } finally {CollectionsLibrary.write(previous)}
    }
    @Test fun downloadDatesSurviveReloadAndClearingAllowsAnotherDownload() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        assumeTrue(context.packageName.endsWith(".uitest"))
        OndaStore.initialize(context)
        assumeTrue(OndaStore.history.value.isEmpty())
        val fixture=File(context.cacheDir,"date-fixture.png")
        val bitmap=android.graphics.Bitmap.createBitmap(8,8,android.graphics.Bitmap.Config.ARGB_8888)
        fixture.outputStream().use {bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()
        val created=mutableListOf<android.net.Uri>()
        try {
            val config=OndaStore.config(includeSecrets=false).put("output_uri","").put("organization","Pasta de destino")
            created+=OndaStore.publish(fixture.absolutePath,config,"png")
            val date=OndaStore.history.value.single().completedAt
            assertTrue(date>0)
            OndaStore.initialize(context)
            assertEquals(date,OndaStore.history.value.single().completedAt)
            OndaStore.clearHistory()
            assertTrue(OndaStore.history.value.isEmpty())
            created+=OndaStore.publish(fixture.absolutePath,config,"png")
            assertTrue(OndaStore.history.value.single().completedAt>=date)
        } finally {
            OndaStore.history.value.toList().forEach {OndaStore.removeHistory(it.id)}
            created.forEach {context.contentResolver.delete(it,null,null)}
            fixture.delete()
        }
    }
}
