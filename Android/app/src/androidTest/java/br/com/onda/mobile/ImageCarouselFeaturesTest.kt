package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.*
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import java.io.File

class ImageCarouselFeaturesTest {
    @get:Rule val compose=createComposeRule()
    @Test fun downloadCardOpensAllImagesOfTheSamePostAndOffersSharing()=checkGallery("photos")
    @Test fun mixedPublicationCardRendersBothImagesAndSharesReadableContent()=checkGallery("social")
    private fun checkGallery(mode:String) {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val prefix="carousel-${System.nanoTime()}"
        val url="https://example.com/$prefix"
        val config=OndaStore.config().put("url",url).put("mode",mode).put("output_uri","").put("duplicate_policy","keep")
        val files=(1..2).map {index->File(context.cacheDir,"$prefix-$index.png").also {file->
            val image=android.graphics.Bitmap.createBitmap(8,8,android.graphics.Bitmap.Config.ARGB_8888)
            image.eraseColor(if(index==1)android.graphics.Color.RED else android.graphics.Color.BLUE)
            file.outputStream().use {image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
        }}
        val uris=files.map {OndaStore.publish(it.absolutePath,config,"png")}
        val id=OndaStore.enqueue(url,prefix,options=JSONObject(OndaStore.settings.value.toString()).put("mode",mode),extra=JSONObject().put("queue_info",JSONObject().put("title",prefix)))
        OndaStore.update(id,"Concluído")
        val store=ViewModelStore();lateinit var vm:OndaViewModel
        compose.runOnIdle {vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]}
        try {
            compose.setContent {MaterialTheme {DownloadsHome(vm)}}
            compose.onNodeWithText("Concluídos").performClick()
            compose.onNodeWithTag("download-summary-$id").performScrollTo().performClick()
            fun checkPixels(color:Int) {
                compose.waitUntil(10000){compose.onNodeWithTag("gallery-image").fetchSemanticsNode().config.getOrNull(SemanticsProperties.StateDescription)=="Imagem carregada"}
                compose.waitForIdle()
                val bitmap=compose.onNodeWithTag("gallery-image").captureToImage().asAndroidBitmap()
                assertEquals(color,bitmap.getPixel(bitmap.width/2,bitmap.height/2))
            }
            checkPixels(android.graphics.Color.RED)
            compose.onNodeWithText("1 / 2").assertExists()
            compose.onNodeWithText("${prefix}-1.png").assertExists()
            compose.onNodeWithText("Próxima").performClick()
            compose.onNodeWithText("2 / 2").assertExists()
            checkPixels(android.graphics.Color.BLUE)
            compose.onNodeWithText("${prefix}-2.png").assertExists()
            compose.onNodeWithText("Compartilhar").assertExists()
            val share=OndaStore.shareIntent(uris[1].toString(),"${prefix}-2.png")
            assertEquals("image/png",share.type)
            assertTrue(share.flags and android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION!=0)
            assertEquals(uris[1],share.clipData?.getItemAt(0)?.uri)
            compose.onNodeWithText("Anterior").performClick()
            compose.onNodeWithText("1 / 2").assertExists()
            compose.onNodeWithText("Fechar").performClick()
        } finally {
            compose.runOnIdle {store.clear()}
            OndaStore.remove(setOf(id))
            OndaStore.history.value.filter {it.source==jobSource(config)}.forEach {OndaStore.removeHistory(it.id)}
            uris.forEach {context.contentResolver.delete(it,null,null)};files.forEach {it.delete()}
        }
    }
}
