package br.com.onda.mobile

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.util.Base64
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.File

/** Real playback controls remain usable after the Android layout changes. */
class PlaybackDesignTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext

    private fun screen(body:(OndaViewModel)->Unit) {
        val store=ViewModelStore()
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val previous=JSONObject(OndaStore.settings.value.toString())
        lateinit var vm:OndaViewModel
        compose.runOnUiThread {
            context.getSharedPreferences("preferences",0).edit().putBoolean("welcome_seen",true).commit()
            OndaStore.saveSettings(JSONObject(previous.toString()).put("theme","Escuro").put("language","pt-BR").put("check_updates",false).put("interface_font_size","100%"))
            vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
            vm.jukebox.stop();vm.jukebox.clearPlaybackQueue();vm.jukebox.state.value=JukeboxState();vm.jukebox.normal=true
            vm.jukebox.setEffects("enabled",false);vm.jukebox.setEffects("speed",85);vm.jukebox.setEffects("reverb",25);vm.jukebox.setEffects("keep_pitch",false)
        }
        try {
            compose.setContent {OndaApp(vm)}
            compose.onNodeWithTag("nav-Efeitos").performClick()
            body(vm)
        } finally {compose.runOnUiThread {vm.jukebox.stop();store.clear();OndaStore.saveSettings(previous)}}
    }

    @Test fun openedUserPlaylistStartsFromCollectionsWithAnExistingQueue()=screen {vm->
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("live_stream")=="true")
        val server=AndroidStreamingParityTest.AudioServer(120)
        try {
            compose.runOnIdle {vm.jukebox.setVolume(0f);vm.jukebox.prepare(record=JSONObject().put("title","Previous local playback").put("source_url",server.url).put("duration_ms",120000),autoPlay=true)}
            compose.waitUntil(90000){vm.jukebox.audioReady.value}
            val result=kotlinx.coroutines.runBlocking(kotlinx.coroutines.Dispatchers.IO){MobileEngine.call(context,"user-playlist-test","collection",OndaStore.config().put("url","https://open.spotify.com/playlist/3QVBmvKuaiT3uuGlFsWCMA").put("playlist_limit",2),EventCallback {})}
            assertFalse(result.toString(),result.has("error"))
            val records=result.getJSONArray("tracks").objects();assertTrue(records.isNotEmpty())
            val oldCount=vm.jukebox.playbackQueue.value.size
            compose.runOnIdle {vm.collection.value=result.put("_collection_url","https://open.spotify.com/playlist/3QVBmvKuaiT3uuGlFsWCMA")}
            compose.onNodeWithTag("nav-Mais").performClick()
            compose.onNodeWithTag("more-list").performScrollToNode(hasTestTag("more-Coleção"));compose.onNodeWithTag("more-Coleção").performClick()
            compose.onNodeWithTag("collection-list").performScrollToNode(hasText("Usar em reprodução"));compose.onNodeWithText("Usar em reprodução").performClick()
            compose.waitUntil(120000){vm.jukebox.playbackQueue.value.size>oldCount && vm.jukebox.currentQueueId.value==vm.jukebox.playbackQueue.value[oldCount].optString("_queue_id") && vm.jukebox.audioReady.value}
            compose.onNodeWithTag("nav-Efeitos").assertIsSelected()
            compose.runOnIdle {assertTrue(vm.jukebox.state.value.playing);assertFalse(vm.jukebox.state.value.paused);assertEquals(records.first().getString("title"),vm.jukebox.state.value.title);assertTrue(requireNotNull(vm.jukebox.state.value.model).optString("cover_url").isNotBlank());assertNotEquals(result.optString("cover_url"),requireNotNull(vm.jukebox.state.value.model).optString("cover_url"))}
        } finally {server.close()}
    }

    @Test fun collectionPreparationFailureIsVisibleWithPreviousTrackLoaded()=screen {vm->
        val server=AndroidStreamingParityTest.AudioServer(120)
        try {
            compose.runOnIdle {vm.jukebox.setVolume(0f);vm.jukebox.prepare(record=JSONObject().put("title","Previous track").put("source_url",server.url).put("duration_ms",120000),autoPlay=true)}
            compose.waitUntil(90000){vm.jukebox.audioReady.value}
            val old=vm.jukebox.currentQueueId.value
            compose.runOnIdle {vm.collection.value=JSONObject().put("title","Collection with missing source").put("tracks",JSONArray().put(JSONObject().put("title","Missing file").put("_local_source",File(context.cacheDir,"nonexistent-collection-track.wav").absolutePath)))}
            compose.onNodeWithTag("nav-Mais").performClick();compose.onNodeWithTag("more-list").performScrollToNode(hasTestTag("more-Coleção"));compose.onNodeWithTag("more-Coleção").performClick()
            compose.onNodeWithTag("collection-list").performScrollToNode(hasText("Usar em reprodução"));compose.onNodeWithText("Usar em reprodução").performClick()
            compose.waitUntil(30000){vm.jukebox.state.value.playbackError.isNotBlank()}
            compose.onNodeWithTag("playback-request-error").assertIsDisplayed()
            compose.runOnIdle {assertEquals(old,vm.jukebox.currentQueueId.value);assertEquals("",vm.jukebox.pendingPlaybackId.value);assertTrue(vm.jukebox.state.value.playing)}
        } finally {server.close()}
    }

    @Test fun spotifyTabEnqueuesDirectlyAndAfterOpeningCollection()=screen {vm->
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("live_stream")=="true")
        val identity="3QVBmvKuaiT3uuGlFsWCMA"
        val url="https://open.spotify.com/playlist/$identity"
        val server=AndroidStreamingParityTest.AudioServer(120)
        fun awaitPlayback(start:Int) {
            try {compose.waitUntil(45000){vm.jukebox.playbackQueue.value.size>start}}
            catch(error:Throwable){throw AssertionError("Playlist was not enqueued: busy=${vm.busy.value}, status=${vm.status.value}, notice=${vm.dialogNotice.value}, tracks=${vm.collection.value.optJSONArray("tracks")?.length()}",error)}
            try {compose.waitUntil(90000){vm.jukebox.state.value.playbackError.isNotBlank() || (vm.jukebox.currentQueueId.value==vm.jukebox.playbackQueue.value[start].optString("_queue_id") && vm.jukebox.audioReady.value)}}
            catch(error:Throwable){throw AssertionError("Playback did not start: pending=${vm.jukebox.pendingPlaybackId.value}, message=${vm.jukebox.state.value.message}, error=${vm.jukebox.state.value.playbackError}, target=${vm.jukebox.playbackQueue.value[start].optString("_analysis")}",error)}
            assertEquals("aruarian dance",vm.jukebox.playbackQueue.value[start].optString("title"))
            val error=vm.jukebox.state.value.playbackError
            if(error.isNotBlank()) {
                assertTrue(error,error.contains("YouTube exigiu uma verificação"))
                compose.onNodeWithTag("playback-request-error").assertIsDisplayed()
                android.util.Log.w("OndaSpotifyTest","Playlist enqueued; live audio blocked by YouTube verification")
            } else compose.runOnIdle {assertTrue(vm.jukebox.state.value.playing);assertFalse(vm.jukebox.state.value.paused)}
        }
        try {
            compose.runOnIdle {vm.jukebox.setVolume(0f);vm.jukebox.prepare(record=JSONObject().put("title","Existing queue track").put("source_url",server.url).put("duration_ms",120000),autoPlay=true)}
            compose.waitUntil(90000){vm.jukebox.audioReady.value}
            compose.runOnIdle {
                vm.spotifyConnected.value=true;vm.spotifyPlaylistsLoaded.value=true
                vm.spotifyPlaylists.value=listOf(JSONObject().put("id",identity).put("title","Yo").put("source_url",url))
                vm.collection.value=JSONObject()
            }
            compose.onNodeWithTag("nav-Mais").performClick();compose.onNodeWithTag("more-list").performScrollToNode(hasTestTag("more-Coleção"));compose.onNodeWithTag("more-Coleção").performClick()
            var start=vm.jukebox.playbackQueue.value.size
            compose.onNodeWithText("Usar em reprodução").performScrollTo().assertIsEnabled().performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.OnClick){it()}
            awaitPlayback(start)
            compose.onNodeWithTag("nav-Efeitos").assertIsSelected()
            compose.onNodeWithTag("nav-Mais").performClick();compose.onNodeWithTag("more-list").performScrollToNode(hasTestTag("more-Coleção"));compose.onNodeWithTag("more-Coleção").performClick()
            compose.onNodeWithText("Abrir coleção").performScrollTo().assertIsEnabled().performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.OnClick){it()}
            compose.waitUntil(30000){!vm.busy.value}
            start=vm.jukebox.playbackQueue.value.size
            compose.onNodeWithText("Usar em reprodução").performScrollTo()
            compose.waitUntil(5000){compose.onAllNodesWithText("Usar em reprodução").filter(isEnabled()).fetchSemanticsNodes().size==1}
            compose.onNodeWithText("Usar em reprodução").assertIsEnabled().performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.OnClick){it()}
            awaitPlayback(start)
        } finally {server.close()}
    }

    @Test fun presetPitchExportAndJukeboxAreAvailableOnThePlaybackPage()=screen {vm->
        compose.onNodeWithTag("playback-search-input").assertExists().performTextInput("Artista ou playlist")
        compose.onNodeWithTag("playback-search-submit").assertIsEnabled()
        compose.onNodeWithTag("playback-open-file").assertIsEnabled()
        compose.onNodeWithText("Efeitos").performScrollTo().performClick()
        compose.runOnIdle {assertTrue(vm.jukebox.effects.value.optBoolean("enabled"))}
        compose.onNodeWithText("Clássico").performScrollTo().performClick()
        compose.onNodeWithText("Slowed leve").performClick()
        compose.runOnIdle {assertEquals(90,vm.jukebox.effects.value.optInt("speed"))}
        compose.onNodeWithText("Manter tom").performScrollTo().performClick()
        compose.runOnIdle {assertTrue(vm.jukebox.effects.value.optBoolean("keep_pitch"))}
        compose.onNodeWithTag("unified-effects-export").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("Jukebox infinito").performScrollTo().performClick()
        compose.runOnIdle {assertFalse(vm.jukebox.normal)}
        compose.onNodeWithTag("playback-jukebox-graph").performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("unified-open-queue").performClick()
        compose.onNodeWithTag("playback-queue-page").assertIsDisplayed()
    }

    @Test fun selectedTrackAndControlsRenderAcrossThemesAndLargeText()=screen {vm->
        val bitmap=Bitmap.createBitmap(300,300,Bitmap.Config.ARGB_8888)
        val canvas=Canvas(bitmap);canvas.drawColor(android.graphics.Color.rgb(13,32,61))
        val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply {color=android.graphics.Color.rgb(239,201,115);textSize=34f;textAlign=Paint.Align.CENTER;isFakeBoldText=true}
        canvas.drawText("STARDUST",150f,154f,paint)
        val bytes=ByteArrayOutputStream().also {bitmap.compress(Bitmap.CompressFormat.PNG,100,it)}.toByteArray();bitmap.recycle()
        val record=JSONObject().put("_queue_id","preview").put("title","Music Sounds Better With You").put("artists",JSONArray(listOf("Stardust"))).put("album","Music Sounds Better With You").put("release_date","1998-07-20")
        val model=JSONObject().put("source",File(context.cacheDir,"playback-layout-preview.wav").absolutePath).put("duration",416).put("media_title",record.getString("title")).put("media_artist","Stardust").put("album",record.getString("album")).put("media_cover",Base64.encodeToString(bytes,Base64.NO_WRAP)).put("beats",JSONArray((0..64).map {it*6.5})).put("neighbors",JSONArray((0 until 64).map {JSONArray(listOf((it+1)%64))}))
        compose.runOnIdle {vm.jukebox.playbackQueue.value=listOf(record);vm.jukebox.currentQueueId.value="preview";vm.jukebox.state.value=JukeboxState(title=record.getString("title"),model=model,index=20,phase=.5f)}
        for((theme,font) in listOf("Escuro" to "100%","Claro" to "130%","Preto puro" to "100%","Alto contraste" to "115%")) {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("theme",theme).put("interface_font_size",font))}
            compose.waitForIdle()
            compose.onNodeWithTag("effects-track-information").performScrollTo().assertIsDisplayed()
            compose.onNodeWithTag("android-compact-player").assertIsDisplayed()
            if(InstrumentationRegistry.getArguments().getString("onda.capture","true")=="true") {
                val capture=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
                File(context.getExternalFilesDir(null),"playback-design-${theme.replace(' ','-')}-$font.png").outputStream().use {capture.compress(Bitmap.CompressFormat.PNG,100,it)};capture.recycle()
            }
            compose.onNodeWithTag("unified-effects-export").performScrollTo().assertIsEnabled()
            compose.onNodeWithTag("playback-jukebox-graph").performScrollTo().assertIsDisplayed()
        }
    }
    @Test fun queueFromAnotherPageDoesNotNavigateToPlaybackAndReturnsToThatPage()=screen {vm->
        compose.onNodeWithTag("nav-Pesquisar").performClick().assertIsSelected()
        compose.runOnIdle {vm.openPlaybackQueue();assertFalse(vm.effectsNavigation.value)}
        compose.onNodeWithTag("playback-queue-page").assertIsDisplayed()
        compose.onNodeWithTag("nav-Pesquisar").assertIsSelected()
        compose.onNodeWithTag("playback-search-input").assertDoesNotExist()
        compose.onNodeWithTag("queue-page-actions").performClick()
        compose.onNodeWithText("Fechar fila").performClick()
        compose.onNodeWithTag("playback-queue-page").assertDoesNotExist()
        compose.onNodeWithTag("nav-Pesquisar").assertIsSelected()
        compose.onNodeWithTag("playback-search-input").assertDoesNotExist()
    }
    @Test fun queuePageKeepsHistorySearchReorderingAndOnePlayer()=screen {vm->
        fun row(id:String,title:String)=JSONObject().put("_queue_id",id).put("title",title).put("artists",JSONArray(listOf("Stardust"))).put("duration_ms",416000).put("_analysis","Erro")
        val source=File(context.cacheDir,"queue-layout-preview.wav").absolutePath
        val model=JSONObject().put("source",source).put("duration",416).put("media_title","Current track").put("media_artist","Stardust").put("beats",JSONArray((0..64).map {it*6.5}))
        compose.runOnIdle {
            vm.jukebox.playbackQueue.value=listOf(row("previous","Previous track"),row("current","Current track"),row("next1","Next one"),row("next2","Next two"))
            vm.jukebox.currentQueueId.value="current";vm.jukebox.state.value=JukeboxState(title="Current track",model=model,index=20,phase=.5f)
        }
        compose.onNodeWithTag("playback-search-input").performTextInput("Saved query")
        compose.onNodeWithTag("unified-open-queue").performClick()
        compose.onNodeWithTag("playback-queue-page").assertIsDisplayed()
        compose.onNodeWithTag("queue-current-card").assertIsDisplayed()
        compose.onNodeWithTag("queue-track-next1").assertIsDisplayed()
        compose.onNodeWithTag("queue-track-previous").assertDoesNotExist()
        assertEquals(1,compose.onAllNodesWithTag("android-compact-player").fetchSemanticsNodes().size)
        compose.onNodeWithTag("queue-current-cover-progress").assertIsDisplayed()
        compose.onNodeWithTag("queue-upcoming-list").performTouchInput {swipe(start=androidx.compose.ui.geometry.Offset(width*.9f,height*.95f),end=androidx.compose.ui.geometry.Offset(width*.1f,height*.95f))}
        compose.onNodeWithTag("queue-tab-recent").assertIsSelected()
        compose.onNodeWithTag("queue-track-previous").assertIsDisplayed()
        compose.onNodeWithTag("queue-recent-list").performTouchInput {swipe(start=androidx.compose.ui.geometry.Offset(width*.1f,height*.95f),end=androidx.compose.ui.geometry.Offset(width*.9f,height*.95f))}
        compose.onNodeWithTag("queue-tab-upcoming").assertIsSelected()
        compose.runOnIdle {assertEquals(listOf("previous","current","next1","next2"),vm.jukebox.playbackQueue.value.map {it.optString("_queue_id")})}
        compose.onNodeWithTag("compact-player-queue").performClick()
        compose.onNodeWithTag("playback-queue-page").assertDoesNotExist()
        compose.onNodeWithTag("playback-search-input").assertTextContains("Saved query")
        compose.onNodeWithTag("compact-player-queue").performClick()
        compose.onNodeWithTag("playback-queue-page").assertIsDisplayed()
        val clock=compose.onNodeWithTag("compact-player-times").fetchSemanticsNode().boundsInRoot
        val progress=compose.onNodeWithTag("compact-player-progress").fetchSemanticsNode().boundsInRoot
        assertTrue("Time labels must appear above the progress bar: $clock / $progress",clock.center.y<progress.center.y)
        val move=compose.onNodeWithContentDescription("Arrastar para reorganizar: Next one",useUnmergedTree=true)
            .fetchSemanticsNode().config[androidx.compose.ui.semantics.SemanticsActions.CustomActions].first {it.label=="Mover para baixo"}
        compose.runOnIdle {assertTrue(move.action())}
        compose.runOnIdle {assertEquals(listOf("previous","current","next2","next1"),vm.jukebox.playbackQueue.value.map {it.optString("_queue_id")});assertEquals("current",vm.jukebox.currentQueueId.value)}
        compose.onNodeWithTag("queue-tab-recent").performClick().assertIsSelected()
        compose.onNodeWithTag("queue-track-previous").assertIsDisplayed()
        compose.onNodeWithTag("queue-track-next1").assertDoesNotExist()
        compose.onNodeWithTag("queue-toggle-search").performClick()
        compose.onNodeWithTag("playback-queue-search").assertExists()
        compose.onNodeWithTag("queue-toggle-search").performClick()
        compose.onNodeWithTag("playback-queue-search").assertDoesNotExist()
        compose.runOnIdle {vm.jukebox.playbackQueue.value=vm.jukebox.playbackQueue.value+row("added","Added track")}
        compose.onNodeWithTag("queue-tab-upcoming").assertIsSelected()
        compose.onNodeWithTag("queue-track-added").assertExists()
        if(InstrumentationRegistry.getArguments().getString("onda.capture","true")=="true") {
            val image=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
            File(context.getExternalFilesDir(null),"playback-queue-page.png").outputStream().use {image.compress(Bitmap.CompressFormat.PNG,100,it)};image.recycle()
        }
        compose.onNodeWithTag("queue-page-actions").performClick()
        compose.onNodeWithText("Fechar fila").performClick()
        compose.onNodeWithTag("playback-queue-page").assertDoesNotExist()
        compose.onNodeWithTag("unified-effects-card").assertExists()
        compose.onNodeWithTag("playback-search-input").assertTextContains("Saved query")
        compose.runOnIdle {assertEquals(5,vm.jukebox.playbackQueue.value.size)}
        compose.onNodeWithTag("compact-player-queue").performClick()
        compose.onNodeWithTag("queue-swipe-added").performScrollTo().performTouchInput {swipeLeft()}
        compose.runOnIdle {
            assertFalse(vm.jukebox.playbackQueue.value.any {it.optString("_queue_id")=="added"})
            assertEquals("current",vm.jukebox.currentQueueId.value)
        }
        compose.onNodeWithTag("queue-tab-indicator").assertIsDisplayed()
        compose.onNodeWithTag("compact-player-queue").performClick()
        compose.onNodeWithTag("compact-player-expand").performClick()
        compose.onNodeWithTag("android-expanded-player").assertIsDisplayed()
        compose.onNodeWithTag("expanded-player-queue").performScrollTo().performClick()
        compose.onNodeWithTag("expanded-player-queue-sheet").assertIsDisplayed()
        compose.onNodeWithTag("android-expanded-player").assertExists()
        compose.runOnIdle {assertFalse(vm.playbackQueueOpen.value)}
        compose.onNodeWithTag("queue-page-actions").performClick()
        compose.onNodeWithText("Fechar fila").performClick()
        compose.onNodeWithTag("expanded-player-queue-sheet").assertDoesNotExist()
        compose.onNodeWithTag("android-expanded-player").assertIsDisplayed()
        compose.onNodeWithContentDescription("Recolher reprodução").performScrollTo().performClick()
        compose.onNodeWithTag("android-expanded-player").assertDoesNotExist()
        compose.onNodeWithTag("unified-effects-card").assertExists()
    }

}
