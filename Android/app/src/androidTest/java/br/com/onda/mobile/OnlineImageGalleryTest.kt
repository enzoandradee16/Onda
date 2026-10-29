package br.com.onda.mobile

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.net.ServerSocket
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean

class OnlineImageGalleryTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private class Source:AutoCloseable {
        val requests=ConcurrentLinkedQueue<String>()
        val finished=AtomicBoolean(false)
        private val server=ServerSocket(0,10,java.net.InetAddress.getByName("127.0.0.1"))
        val url="http://127.0.0.1:${server.localPort}"
        private fun png(color:Int):ByteArray {
            val bitmap=android.graphics.Bitmap.createBitmap(16,16,android.graphics.Bitmap.Config.ARGB_8888).apply {eraseColor(color)}
            val output=java.io.ByteArrayOutputStream();bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,output);bitmap.recycle();return output.toByteArray()
        }
        private val red=png(android.graphics.Color.RED)
        private val blue=png(android.graphics.Color.BLUE)
        private val thread=Thread {
            while(!server.isClosed)try {
                server.accept().use {socket->
                    val reader=socket.getInputStream().bufferedReader();val path=reader.readLine()?.split(' ')?.getOrNull(1).orEmpty()
                    while(!reader.readLine().isNullOrEmpty()){}
                    requests.add(path)
                    if(path=="/slow")Thread.sleep(1200)
                    val html=path in listOf("/post","/slow")
                    val data=if(html)"<meta property=\"og:image\" content=\"/one.png\"><meta property=\"og:image\" content=\"/two.png\">".toByteArray() else if(path=="/one.png")red else blue
                    val type=if(html)"text/html" else "image/png"
                    val output=socket.getOutputStream();output.write("HTTP/1.1 200 OK\r\nContent-Type: $type\r\nContent-Length: ${data.size}\r\nConnection: close\r\n\r\n".toByteArray());output.write(data);output.flush();finished.set(true)
                }
            }catch(_:Exception){if(server.isClosed)break}
        }.apply {isDaemon=true;start()}
        override fun close(){server.close();thread.join(3000)}
    }
    private fun vm(store:ViewModelStore):OndaViewModel {
        OndaStore.initialize(context)
        return ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
    }
    private fun checkImage(red:Boolean) {
        compose.waitUntil(15000){compose.onAllNodesWithTag("online-gallery-image").fetchSemanticsNodes().singleOrNull()?.config?.getOrNull(SemanticsProperties.StateDescription)=="Imagem carregada"}
        compose.waitForIdle()
        val image=compose.onNodeWithTag("online-gallery-image").captureToImage().asAndroidBitmap()
        val color=image.getPixel(image.width/2,image.height/2)
        if(red)assertTrue(android.graphics.Color.red(color)>240&&android.graphics.Color.blue(color)<15)
        else assertTrue(android.graphics.Color.blue(color)>240&&android.graphics.Color.red(color)<15)
    }
    @Test fun linksPreviewRendersCarouselWithoutCreatingDownloadsOrHistory() {
        Source().use {source->
            val store=ViewModelStore();lateinit var model:OndaViewModel
            compose.runOnIdle {model=vm(store)}
            val history=OndaStore.history.value.map {it.id};val queue=OndaStore.items.value.map {it.id}
            try {
                OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("mode","photos"))
                compose.setContent {MaterialTheme {Column {LinksPage(model);OnlineImageGallery(model)}}}
                compose.onNodeWithTag("links-input").performTextInput(source.url+"/post")
                compose.onNodeWithTag("online-image-preview-button").performScrollTo().performClick()
                checkImage(true);assertEquals(listOf("/post","/one.png"),source.requests.toList())
                compose.onNodeWithTag("online-gallery-image").performTouchInput {swipeLeft()};checkImage(false)
                assertEquals(listOf("/post","/one.png","/two.png"),source.requests.toList())
                compose.onNodeWithTag("online-gallery-image").performTouchInput {swipeRight()};checkImage(true)
                assertEquals(3,source.requests.size)
                compose.onNodeWithText("Baixar imagens").assertExists();compose.onNodeWithText("Compartilhar link").assertExists()
                compose.onNodeWithText("Fechar").performClick()
                assertEquals(history,OndaStore.history.value.map {it.id});assertEquals(queue,OndaStore.items.value.map {it.id})
            }finally {compose.runOnIdle {store.clear()}}
        }
    }
    @Test fun pendingDownloadCardOffersOnlinePreviewWithoutStartingDownload() {
        Source().use {source->
            val store=ViewModelStore();lateinit var model:OndaViewModel
            compose.runOnIdle {model=vm(store)}
            val id=OndaStore.enqueue(source.url+"/post",options=JSONObject(OndaStore.settings.value.toString()).put("mode","photos"),extra=JSONObject().put("queue_info",JSONObject().put("title","Online gallery fixture")))
            try {
                compose.setContent {MaterialTheme {Column {DownloadsHome(model);OnlineImageGallery(model)}}}
                compose.onNode(hasTestTag("online-image-preview-button") and hasAnyAncestor(hasTestTag("download-summary-$id"))).performScrollTo().performClick()
                checkImage(true)
                assertEquals("Pendente",OndaStore.items.value.first {it.id==id}.state)
                compose.onNodeWithText("Fechar").performClick()
            }finally {compose.runOnIdle {store.clear()};OndaStore.remove(setOf(id))}
        }
    }
    @Test fun cancelledLookupCannotOpenLateGallery() {
        Source().use {source->
            val store=ViewModelStore();lateinit var model:OndaViewModel
            compose.runOnIdle {model=vm(store)}
            try {
                compose.setContent {MaterialTheme {Column {OnlineImagePreviewButton(model,source.url+"/slow");OnlineImageGallery(model)}}}
                compose.onNodeWithTag("online-image-preview-button").performClick()
                compose.waitUntil(10000){source.requests.contains("/slow")}
                compose.onNodeWithText("Cancelar prévia").performClick()
                compose.waitUntil(5000){source.finished.get()}
                assertNull(model.onlineImageGallery.value);assertEquals("",model.onlineImageLoading.value)
            }finally {compose.runOnIdle {store.clear()}}
        }
    }
    @Test fun imagesPageUsesEmbeddedCarouselWithoutOpeningTheGalleryDialog() {
        Source().use {source->
            val store=ViewModelStore();lateinit var model:OndaViewModel
            compose.runOnIdle {model=vm(store)}
            val history=OndaStore.history.value.map {it.id};val queue=OndaStore.items.value.map {it.id}
            try {
                compose.setContent {MaterialTheme {Column {ImagesPage(model);OnlineImageGallery(model)}}}
                compose.onNodeWithTag("images-source-link").performTextInput(source.url+"/post")
                compose.onNodeWithTag("online-image-preview-button").assertDoesNotExist()
                compose.onNodeWithTag("images-search").performScrollTo().performClick()
                compose.waitUntil(15000){model.onlineImageGallery.value!=null && model.onlineImageThumbnail.value?.has("path")==true}
                compose.runOnIdle {assertTrue(model.onlineImageEmbedded.value)}
                compose.onNodeWithTag("images-inline-gallery").performScrollTo().assertIsDisplayed()
                compose.onNodeWithTag("online-gallery-image").assertDoesNotExist()
                compose.onNodeWithTag("images-inline-gallery").performTouchInput {swipeLeft()}
                compose.waitUntil(15000){model.onlineImageIndex.value==1 && model.onlineImageThumbnail.value?.has("path")==true}
                compose.onNodeWithText("2 / 2").assertExists()
                compose.onNodeWithTag("images-share-link").assertExists()
                compose.onNodeWithTag("images-download").assertExists()
                assertEquals(history,OndaStore.history.value.map {it.id});assertEquals(queue,OndaStore.items.value.map {it.id})
                compose.onNodeWithTag("images-options").performScrollTo().assertIsDisplayed()
                compose.onNodeWithText("Tamanho máximo").assertExists()
                compose.onNodeWithText("Manter proporção").assertExists()
                compose.onNodeWithTag("images-more-actions").performScrollTo().performClick()
                compose.onNodeWithText("Escolher arquivo").assertExists()
            } finally {compose.runOnIdle {model.cancelOnlineImagePreview();model.closeOnlineImages();store.clear()}}
        }
    }

}
