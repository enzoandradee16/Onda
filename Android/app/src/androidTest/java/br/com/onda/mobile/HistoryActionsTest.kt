package br.com.onda.mobile

import android.content.Context
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class HistoryActionsTest {
    @get:Rule val compose=createComposeRule()
    @Test fun platformShortLinksAndMetadataPriority() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        for((source,key) in listOf("https://vt.tiktok.com/test/" to "tiktok","https://vm.tiktok.com/test/" to "tiktok","https://k.kwai.com/p/test" to "kwai","https://kwai-video.com/p/test" to "kwai","https://www.instagram.com/reel/test" to "instagram","https://fb.watch/test" to "facebook","https://x.com/a/status/1" to "twitter","spotify:track:test" to "spotify"))assertEquals(key,identifyPlatform(source).key)
        assertEquals("spotify",identifyPlatform("https://youtube.com/watch?v=x","Spotify").key)
        assertEquals("link",identifyPlatform("https://instagram.com.other.example/test").key)
        assertEquals("",identifyPlatform("https://instagram.com@other.example/test").key)
        assertEquals("",identifyPlatform("file:///song.mp3").key)
        assertEquals("Vídeo",historyKind("original","movie.webm"))
        assertEquals("Áudio",historyKind("original","song.flac"))
        assertEquals("Imagens",historyKind("photos","picture.avif"))
    }
    @OptIn(ExperimentalTestApi::class)
    @Test fun filtersAndBothRemovalActionsPreserveDownloadedFiles() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val saved=JSONObject(OndaStore.settings.value.toString())
        val first=System.currentTimeMillis()
        val folder=File(context.cacheDir,"history-actions-$first").apply {mkdirs()}
        val files=listOf("fixture-audio.mp3","fixture-video.mp4","fixture-image.gif").map {File(folder,it).apply {writeBytes(byteArrayOf(1,2,3))}}
        val ids=(0..2).map {first+it}
        val db=context.openOrCreateDatabase("onda.sqlite3",Context.MODE_PRIVATE,null)
        files.forEachIndexed {i,file->
            db.execSQL("INSERT INTO history(id,title,uri,mode,size) VALUES(?,?,?,?,?)",arrayOf<Any>(ids[i],file.name,android.net.Uri.fromFile(file).toString(),listOf("mp3","original","photos")[i],file.length()))
            db.execSQL("INSERT INTO history_sources(history_id,source,mode) VALUES(?,?,?)",arrayOf<Any>(ids[i],listOf("https://vt.tiktok.com/test/","https://kwai-video.com/p/test","https://www.instagram.com/p/test")[i],""))
        }
        db.close();OndaStore.refresh()
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        try {
            OndaStore.settings.value=JSONObject(saved.toString()).put("language","pt-BR")
            compose.setContent {MaterialTheme {HistoryPage(vm,{})}}
            compose.onNodeWithText("Pesquisar no histórico").performTextInput("fixture-")
            for((label,index) in listOf("Áudio" to 0,"Vídeo" to 1,"Imagens" to 2)) {
                compose.onNodeWithTag("history-filter-$label").performScrollTo().performClick()
                compose.onNodeWithTag("history-card-${ids[index]}").performScrollTo().assertExists()
                ids.filter {it!=ids[index]}.forEach {compose.onNodeWithTag("history-card-$it").assertDoesNotExist()}
            }
            compose.onNodeWithTag("history-filter-Áudio").performScrollTo().performClick()
            compose.onNodeWithContentDescription("Plataforma: TikTok").assertExists()
            compose.onNodeWithTag("remove-history-button-${ids[0]}").performScrollTo().performClick()
            compose.waitUntil(5000) {OndaStore.history.value.none {it.id==ids[0]}}
            compose.onNodeWithTag("history-filter-Vídeo").performScrollTo().performClick()
            compose.onNodeWithContentDescription("Plataforma: Kwai").assertExists()
            compose.onNodeWithTag("history-card-${ids[1]}").performScrollTo().performMouseInput {click(button=MouseButton.Secondary)}
            compose.onNodeWithTag("remove-history-${ids[1]}").performClick()
            compose.waitUntil(5000) {OndaStore.history.value.none {it.id==ids[1]}}
            assertTrue(OndaStore.history.value.any {it.id==ids[2]})
            files.forEach {assertArrayEquals(byteArrayOf(1,2,3),it.readBytes())}
        } finally {
            ids.forEach {OndaStore.removeHistory(it)}
            OndaStore.saveSettings(saved)
            files.forEach {it.delete()};folder.delete()
        }
    }
}
