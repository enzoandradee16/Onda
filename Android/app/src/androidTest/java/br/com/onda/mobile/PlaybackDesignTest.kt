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
