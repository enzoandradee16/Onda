package br.com.onda.mobile

import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File

class ImageBackgroundTest {
    @Test fun nativeModelRemovesBackgroundAndExportsTransparentPng()=runBlocking<Unit> {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val source=File(context.getExternalFilesDir(null),"background-review-input.jpg")
        org.junit.Assume.assumeTrue(source.isFile)
        val config=OndaStore.config(JSONObject().put("mode","photos").put("image_format","JPG").put("image_remove_background",true)).put("source",source.absolutePath).put("name","photo.jpg")
        assertTrue(config.getJSONObject("image_options").getBoolean("remove_background"))
        val result=withContext(Dispatchers.IO){MobileEngine.call(context,"background-image-review","image_preview",config,EventCallback {})}
        assertFalse(result.toString(),result.has("error"))
        val file=File(result.getString("path"))
        try {
            val bitmap=android.graphics.BitmapFactory.decodeFile(file.absolutePath)
            assertNotNull(bitmap);assertTrue(bitmap.hasAlpha());assertEquals(800,bitmap.width);assertEquals(657,bitmap.height)
            assertTrue(android.graphics.Color.alpha(bitmap.getPixel(0,0))<10)
            assertTrue(android.graphics.Color.alpha(bitmap.getPixel(400,300))>240)
            bitmap.recycle();assertEquals("PNG",result.getString("format"))
        } finally {file.delete()}
    }
    @Test fun editsReturnComparisonAndQueueRemovalCanBeUndone()=runBlocking<Unit> {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val source=File(context.getExternalFilesDir(null),"background-review-input.jpg")
        org.junit.Assume.assumeTrue(source.isFile)
        val before=source.readBytes()
        val config=OndaStore.config(JSONObject().put("mode","photos").put("image_format","PNG").put("image_crop","1:1").put("image_rotation",90).put("image_background","color").put("image_background_color","#123456"))
            .put("source",source.absolutePath).put("name","photo.jpg")
        val result=withContext(Dispatchers.IO){MobileEngine.call(context,"image-edits-review","image_preview",config,EventCallback {})}
        assertFalse(result.toString(),result.has("error"))
        val edited=android.graphics.BitmapFactory.decodeFile(result.getString("path"))
        val original=android.graphics.BitmapFactory.decodeFile(result.getString("original_preview"))
        assertEquals(657,edited.width);assertEquals(657,edited.height)
        assertEquals(800,original.width);assertEquals(657,original.height)
        assertArrayEquals(before,source.readBytes())
        edited.recycle();original.recycle()
        File(result.getString("path")).delete();File(result.getString("original_preview")).delete()
        withContext(Dispatchers.Main) {
            val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main)
            val gate=CompletableDeferred<Unit>()
            val controller=JukeboxController(context,scope,{},callOverride={_,_,_->gate.await();JSONObject()})
            try {
                controller.clearPlaybackQueue()
                controller.enqueueAll(listOf(JSONObject().put("title","A").put("source_url","https://example.com/a"),JSONObject().put("title","B").put("source_url","https://example.com/b")))
                controller.removeQueued(1)
                assertTrue(controller.canUndoQueueRemoval.value)
                controller.undoQueueRemoval()
                assertEquals(listOf("A","B"),controller.playbackQueue.value.map {it.optString("title")})
                assertFalse(controller.canUndoQueueRemoval.value)
            } finally {scope.cancel()}
        }
    }

}
