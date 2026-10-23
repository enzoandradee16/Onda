package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class QueueTitleLookupTest {
    @Test fun lateLookupNeverReplacesActiveOrManuallyNamedItems() {
        val url="https://open.spotify.com/track/303ccTay2FiDTZ9fZ2AdBt"
        val id=OndaStore.enqueue(url)
        try {
            assertTrue(OndaStore.renamePendingLink(id,url,"Artist - Song",JSONObject().put("album","Album").put("cover_url","https://example.com/cover.png")))
            OndaStore.refresh()
            assertEquals("Album",OndaStore.items.value.first {it.id==id}.config.getJSONObject("queue_info").getString("album"))
            OndaStore.updateQueueInformation(id,url,JSONObject().put("genre","House"))
            assertEquals("Artist - Song",OndaStore.items.value.first {it.id==id}.title)
            assertEquals("Album",OndaStore.items.value.first {it.id==id}.config.getJSONObject("queue_info").getString("album"))
            assertFalse(OndaStore.renamePendingLink(id,url,"Other version"))
            OndaStore.rename(id,url)
            OndaStore.update(id,"Baixando")
            assertFalse(OndaStore.renamePendingLink(id,url,"Other version"))
            OndaStore.update(id,"Pendente")
            assertFalse(OndaStore.renamePendingLink(id,"https://example.com/other","Wrong link"))
            assertFalse(OndaStore.renamePendingLink(id,url,""))
            OndaStore.remove(setOf(id))
            assertFalse(OndaStore.renamePendingLink(id,url,"Deleted"))
        } finally {OndaStore.remove(setOf(id))}
    }

    @Test fun enqueueUpdatesAndPersistsNameBeforeDownloading() {
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("liveNetwork")=="true")
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val store=androidx.lifecycle.ViewModelStore()
        var id=""
        try {
            instrumentation.runOnMainSync {
                val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
                store.put("queue-title",vm)
                id=vm.enqueueLink("https://open.spotify.com/intl-pt/track/303ccTay2FiDTZ9fZ2AdBt?si=660baa679ef94455")
            }
            val deadline=android.os.SystemClock.uptimeMillis()+30000
            while(android.os.SystemClock.uptimeMillis()<deadline && !OndaStore.items.value.first {it.id==id}.title.contains("Stardust"))android.os.SystemClock.sleep(100)
            val item=OndaStore.items.value.first {it.id==id}
            assertTrue(item.title,item.title.contains("Stardust") && item.title.contains("Music Sounds Better With You"))
            assertEquals("Pendente",item.state)
            OndaStore.refresh()
            assertEquals(item.title,OndaStore.items.value.first {it.id==id}.title)
        } finally {
            if(id.isNotBlank())OndaStore.remove(setOf(id))
            instrumentation.runOnMainSync {store.clear()}
        }
    }

    @Test fun spotifyUserLinkReturnsTitleAndArtist() {
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("liveNetwork")=="true")
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val result=MobileEngine.call(context,"queue-title-live","describe",JSONObject().put("url","https://open.spotify.com/intl-pt/track/303ccTay2FiDTZ9fZ2AdBt?si=660baa679ef94455"),EventCallback {})
        assertFalse(result.toString(),result.has("error"))
        assertTrue(result.toString(),result.optString("title").contains("Stardust"))
        assertTrue(result.toString(),result.optString("title").contains("Music Sounds Better With You"))
    }
}
