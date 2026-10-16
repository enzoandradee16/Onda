package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class LargeQueueTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun thirteenHundredTracksStayOrderedAndSurviveDatabaseReload() {
        val prefix=UUID.randomUUID().toString()
        val options=JSONObject(OndaStore.settings.value.toString()).put("detect_duplicates",true)
        val ids=mutableListOf<String>()
        val started=System.nanoTime()
        try {
            repeat(13) {chunk->OndaStore.enqueueBatch {repeat(100) {index->
                val number=chunk*100+index
                ids+=OndaStore.enqueue("https://example.com/$prefix/$number","Track $number",options,JSONObject().put("playlist_title",prefix))
            }}}
            assertEquals(1300,ids.size)
            assertEquals(ids,OndaStore.items.value.filter {it.id in ids}.map {it.id})
            assertTrue(OndaStore.items.value.filter {it.id in ids}.all {it.state=="Pendente"})
            OndaStore.refresh()
            assertEquals(ids,OndaStore.items.value.filter {it.id in ids}.map {it.id})
            val second=OndaStore.enqueue("https://example.com/$prefix/1299","Repeat",options,JSONObject().put("playlist_title",prefix));ids+=second
            assertEquals("Duplicata",OndaStore.items.value.first {it.id==second}.state)
            OndaStore.answer(JSONObject().put("cancel",true))
            android.util.Log.i("ONDA-LargeQueue","1300 tracks inserted and reloaded in ${(System.nanoTime()-started)/1000000} ms")
        } finally {ids.forEach {OndaStore.dismissQuestions("duplicate-$it")};OndaStore.remove(ids.toSet())}
    }
    @Test fun largeServiceRequestUsesTinyIntentAndRetainsEntireSelection() {
        val ids=(0 until 20000).map {UUID.randomUUID().toString()}
        val intent=DownloadBatchFiles.intent(context,ids)
        val parcel=android.os.Parcel.obtain()
        try {
            intent.writeToParcel(parcel,0)
            assertTrue("Intent must not contain the whole playlist",parcel.dataSize()<2048)
            assertEquals(ids.toSet(),DownloadBatchFiles.consume(context,intent.getStringExtra("batch_token")!!))
            assertFalse(intent.hasExtra("batch"))
        } finally {parcel.recycle();DownloadBatchFiles.discard(context,intent)}
    }
    @Test fun queuedItemsUseCurrentSessionAndRespectRemoval() {
        val old=JSONObject(OndaStore.settings.value.toString())
        val stored=JSONObject().put("cookies_file","old-general").put("youtube_cookies_file","old-youtube").put("youtube_user_agent","old-agent").put("mode","flac")
        try {
            OndaStore.saveSettings(JSONObject(old.toString()).put("cookies_file","current-general").put("youtube_cookies_file","current-youtube").put("youtube_user_agent","current-agent"))
            val live=OndaStore.executionConfig(stored)
            assertEquals("current-youtube",live.getString("youtube_cookies_file"));assertEquals("current-agent",live.getString("youtube_user_agent"));assertEquals("flac",live.getString("mode"))
            assertEquals("old-youtube",stored.getString("youtube_cookies_file"))
            OndaStore.saveSettings(JSONObject(old.toString()).put("cookies_file","").put("youtube_cookies_file","").put("youtube_user_agent",""))
            assertEquals("",OndaStore.executionConfig(stored).getString("youtube_cookies_file"))
        } finally {OndaStore.saveSettings(old)}
    }
    @Test fun cookieExportRequiresLoginRejectsControlCharactersAndLoadsInPython() {
        val anonymous=youtubeCookieEntries(listOf("CONSENT=YES; VISITOR_INFO1_LIVE=visitor"))
        assertFalse(hasYouTubeLogin(anonymous))
        val entries=youtubeCookieEntries(listOf("SID=test-session; SAPISID=token=with=equals; BAD=abc\tdef; __Host-test=host","SID=secondary"))
        assertTrue(hasYouTubeLogin(entries));assertFalse(entries.containsKey("BAD"));assertEquals("test-session",entries["SID"])
        assertEquals("token=with=equals",entries["SAPISID"])
        val file=File(context.cacheDir,"youtube-cookie-fixture.txt")
        try {
            file.writeText(youtubeCookieFile(entries));MobileEngine.initialize(context)
            val jar=Python.getInstance().getModule("http.cookiejar").callAttr("MozillaCookieJar")
            jar.callAttr("load",file.absolutePath,true,true)
            assertEquals(3,jar.callAttr("__len__").toInt())
            assertTrue(file.readText().contains("www.youtube.com\tFALSE\t/\tTRUE\t0\t__Host-test"))
        } finally {file.delete()}
    }
    @Test fun backendUsesSessionAgentButDoesNotLeakYouTubeSessionIntoSocialDownloads() {
        MobileEngine.initialize(context);val py=Python.getInstance();val json=py.getModule("json")
        fun options(url:String):JSONObject {
            val config=json.callAttr("loads",JSONObject().put("url",url).put("cookies_file","general.txt").put("youtube_cookies_file","youtube.txt").put("youtube_user_agent","Session agent").toString())
            val params=json.callAttr("loads","{\"http_headers\":{\"Referer\":\"keep\"}}")
            val result=py.getModule("mobile_backend").callAttr("session_options",params,config)
            return JSONObject(json.callAttr("dumps",result).toString())
        }
        val youtube=options("https://youtube.com/watch?v=test")
        assertEquals("youtube.txt",youtube.getString("cookiefile"));assertEquals("Session agent",youtube.getJSONObject("http_headers").getString("User-Agent"));assertEquals("keep",youtube.getJSONObject("http_headers").getString("Referer"))
        val instagram=options("https://instagram.com/p/test/")
        assertEquals("general.txt",instagram.getString("cookiefile"));assertFalse(instagram.getJSONObject("http_headers").has("User-Agent"))
    }
    @Test fun collectionViewModelQueuesAllTracksAndRecoversFromInvalidRow()=runBlocking {
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        val group=UUID.randomUUID().toString()
        val rows=(0 until 1250).map {JSONObject().put("source_url","https://example.com/$group/$it").put("title","Song $it").put("artists",JSONArray().put("Artist"))}
        try {
            withContext(Dispatchers.Main) {vm.queueCollection(rows,JSONObject(OndaStore.settings.value.toString()),group,false)}
            withTimeout(60000) {while(vm.addingToQueue.value)delay(50)}
            assertEquals(1250,OndaStore.items.value.count {it.config.optString("playlist_title")==group})
            withContext(Dispatchers.Main) {vm.queueCollection(rows.take(100)+JSONObject(),JSONObject(OndaStore.settings.value.toString()).put("detect_duplicates",false),group+"-invalid",false)}
            withTimeout(60000) {while(vm.addingToQueue.value)delay(50)}
            assertEquals(100,OndaStore.items.value.count {it.config.optString("playlist_title")==group+"-invalid"})
            assertNotNull(vm.dialogNotice.value)
        } finally {OndaStore.remove(OndaStore.items.value.filter {it.config.optString("playlist_title").startsWith(group)}.map {it.id}.toSet());withContext(Dispatchers.Main) {vm.player.release()}}
    }
}
