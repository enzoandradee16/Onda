package br.com.onda.mobile

import android.graphics.Bitmap
import androidx.core.content.FileProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class LocalImageImportTest {
    @Test fun grantedContentUriCanBeImportedAndPreviewed() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val source=File(context.cacheDir,"local-import-test.png")
        source.outputStream().use {Bitmap.createBitmap(40,30,Bitmap.Config.ARGB_8888).compress(Bitmap.CompressFormat.PNG,100,it)}
        val uri=FileProvider.getUriForFile(context,"${context.packageName}.files",source)
        val imported=OndaStore.importDocument(uri,"image")
        try {
            assertArrayEquals(source.readBytes(),imported.readBytes())
            val config=OndaStore.config().put("source",imported.absolutePath).put("name","local.png")
                .put("image_options",JSONObject().put("format","Original").put("keep_ratio",true))
            val result=MobileEngine.call(context,"local-image-import-test","image_preview",config,EventCallback {})
            assertFalse(result.toString(),result.has("error"))
            assertEquals(40,result.getInt("width"));assertEquals(30,result.getInt("height"))
        } finally {source.delete();imported.delete()}
    }
    @Test fun permissionRequestMatchesAndroidVersionAndSupportsLimitedPhotos() {
        assertTrue(photoPermissions(32).contains(android.Manifest.permission.READ_EXTERNAL_STORAGE))
        assertArrayEquals(arrayOf(android.Manifest.permission.READ_MEDIA_IMAGES),photoPermissions(33))
        assertTrue(photoPermissions(34).contains(android.Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED))
    }
}
