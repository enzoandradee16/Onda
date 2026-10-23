package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidShellTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before(){val i=InstrumentationRegistry.getInstrumentation();if(android.os.Build.VERSION.SDK_INT>=33)i.uiAutomation.grantRuntimePermission(i.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)}
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()
    private fun ready() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
    }
    @Test fun navigationLinksAndSettingsKeepExistingPreferences() {
        ready();val original=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("theme","Escuro").put("accent","Turquesa").put("hidden_tabs",org.json.JSONArray()))}
            compose.onNodeWithTag("nav-Mais").performClick()
            compose.onNodeWithTag("more-Imagens").assertIsDisplayed()
            compose.onNodeWithTag("more-Conversor").assertIsDisplayed()
            compose.onNodeWithTag("more-Editar metadados").assertIsDisplayed()
            compose.onNodeWithTag("more-Imagens").performClick()
            compose.onNodeWithText("Imagens").assertExists()
            compose.onNodeWithTag("nav-Fila").performClick()
            compose.onNodeWithContentDescription("Adicionar links").performClick()
            compose.onNodeWithTag("links-input").assertExists()
            compose.onNodeWithTag("links-input").performTextInput("https://www.instagram.com/p/example/")
            compose.onNodeWithTag("links-add").assertIsEnabled()
            compose.onNodeWithTag("links-download").assertIsEnabled()
            compose.activityRule.scenario.onActivity {it.onBackPressedDispatcher.onBackPressed()}
            compose.onNodeWithTag("nav-Mais").performClick()
            compose.onNodeWithTag("open-settings").performClick()
            compose.onNodeWithTag("settings-search").assertExists()
            compose.runOnIdle {assertEquals("Turquesa",OndaStore.settings.value.optString("accent"));assertEquals(original.optString("mode"),OndaStore.settings.value.optString("mode"))}
        } finally {compose.runOnIdle {OndaStore.saveSettings(original)}}
    }
    @Test fun moreUsesHiddenTabsWithoutChangingThem() {
        ready();val original=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("hidden_tabs",org.json.JSONArray().put("Imagens")))}
            compose.onNodeWithTag("nav-Mais").performClick()
            compose.onNodeWithTag("more-Imagens").assertDoesNotExist()
            compose.onNodeWithTag("more-Conversor").assertExists()
        } finally {compose.runOnIdle {OndaStore.saveSettings(original)}}
    }
    @Test fun screenshotsAndMiniplayerUseTheSameNavigation() {
        ready();val original=JSONObject(OndaStore.settings.value.toString())
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        val originalQueue=OndaStore.items.value
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val cover=java.io.File(context.cacheDir,"ui-album.png")
        val bitmap=android.graphics.Bitmap.createBitmap(240,240,android.graphics.Bitmap.Config.ARGB_8888)
        val canvas=android.graphics.Canvas(bitmap);canvas.drawColor(android.graphics.Color.rgb(24,34,44))
        val paint=android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);paint.color=android.graphics.Color.rgb(230,104,42);canvas.drawCircle(120f,120f,85f,paint);paint.color=android.graphics.Color.rgb(14,20,26);canvas.drawCircle(120f,120f,30f,paint)
        cover.outputStream().use {bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()
        val record=JSONObject().put("title","Music Sounds Better With You").put("artists",org.json.JSONArray().put("Stardust")).put("album","Music Sounds Better With You").put("cover_url",cover.absolutePath).put("release_date","1998").put("duration_ms",441000).put("source_url","https://example.com/song")
        fun capture(name:String){compose.waitForIdle();Thread.sleep(350);val image=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot();java.io.File(context.getExternalFilesDir(null),"redesign-$name.png").outputStream().use {image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()}
        try {
            compose.runOnIdle {
                OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("theme","Escuro").put("accent","Turquesa").put("jukebox_background",true).put("hidden_tabs",org.json.JSONArray()))
                vm.searchResults.value=listOf(record,JSONObject(record.toString()).put("title","Around the World"))
                val neighbors=org.json.JSONArray();repeat(64){neighbors.put(org.json.JSONArray().put((it+24)%64))}
                vm.jukebox.state.value=JukeboxState(title=record.getString("title"),model=JSONObject().put("source",java.io.File(context.cacheDir,"ui-audio.wav").absolutePath).put("media_title",record.getString("title")).put("media_artist","Stardust").put("cover_url",cover.absolutePath).put("neighbors",neighbors),playing=true,flow=listOf(8 to 32))
                OndaStore.items.value=listOf(DownloadItem("ui-download",record.getString("title"),JSONObject().put("catalog_record",record).put("queue_info",record),state="Baixando",progress=68f),DownloadItem("ui-finished","One More Time",JSONObject().put("catalog_record",record).put("queue_info",record),state="Concluído",progress=100f))
            }
            compose.onNodeWithTag("nav-Pesquisar").performClick();compose.onNodeWithTag("android-compact-player").assertIsDisplayed();capture("search")
            compose.onNodeWithTag("nav-Fila").performClick();compose.onNodeWithTag("download-summary-ui-download").assertIsDisplayed();capture("downloads")
            compose.onNodeWithTag("nav-Mais").performClick();capture("more")
            compose.onNodeWithTag("android-compact-player").performClick()
            compose.onNodeWithTag("android-expanded-player").assertIsDisplayed();capture("jukebox")
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("theme","Preto puro"))};capture("black")
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("theme","Claro"))};capture("light")
        } finally {compose.runOnIdle {vm.jukebox.stop();vm.searchResults.value=emptyList();OndaStore.items.value=originalQueue;OndaStore.saveSettings(original)}}
    }

    @Test fun downloadCardSizeResizesAndKeepsTheSavedChoice() {
        ready();val original=JSONObject(OndaStore.settings.value.toString());val originalQueue=OndaStore.items.value
        try {
            compose.runOnIdle {
                OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR"))
                OndaStore.items.value=listOf(DownloadItem("size-fixture","Card size fixture",JSONObject().put("queue_info",JSONObject().put("artists",org.json.JSONArray().put("Artist")))))
            }
            compose.onNodeWithTag("nav-Fila").performClick()
            val heights=mutableListOf<Float>()
            for(size in listOf("Pequeno","Médio","Grande")) {
                compose.onNodeWithTag("download-card-size").performClick()
                compose.onNodeWithText(size).performClick();compose.waitForIdle()
                heights.add(compose.onNodeWithTag("download-summary-size-fixture").fetchSemanticsNode().boundsInRoot.height)
                compose.runOnIdle {assertEquals(size,OndaStore.settings.value.optString("queue_card_size"))}
            }
            assertTrue(heights.toString(),heights[0]<heights[1] && heights[1]<heights[2])
        } finally {compose.runOnIdle {OndaStore.items.value=originalQueue;OndaStore.saveSettings(original)}}
    }

    @Test fun swipesNavigatePagesButDoNotStealSliders() {
        ready();val original=JSONObject(OndaStore.settings.value.toString())
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        fun swipe(left:Boolean) {
            compose.onNodeWithTag("page-swipe").performTouchInput {
                swipe(androidx.compose.ui.geometry.Offset(width*(if(left).85f else .15f),20f),androidx.compose.ui.geometry.Offset(width*(if(left).15f else .85f),20f),350)
            }
            compose.waitForIdle()
        }
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(original.toString()).put("language","pt-BR").put("hidden_tabs",org.json.JSONArray()))}
            compose.onNodeWithTag("nav-Pesquisar").performClick()
            swipe(true);compose.onNodeWithTag("nav-Fila").assertIsSelected()
            swipe(true);compose.onNodeWithTag("nav-Efeitos").assertIsSelected()
            swipe(true);compose.onNodeWithTag("nav-Mais").assertIsSelected()
            swipe(false);compose.onNodeWithTag("nav-Efeitos").assertIsSelected()
            compose.runOnIdle {
                val neighbors=org.json.JSONArray();repeat(64){neighbors.put(org.json.JSONArray())}
                vm.jukebox.state.value=JukeboxState(title="Gesture test",model=JSONObject().put("neighbors",neighbors))
            }
            compose.onNodeWithText("Jukebox infinito").performClick()
            compose.onNodeWithTag("jukebox-variation").assertIsDisplayed().performTouchInput {swipe(androidx.compose.ui.geometry.Offset(width*.75f,centerY),androidx.compose.ui.geometry.Offset(width*.15f,centerY),350)}
            compose.onNodeWithTag("nav-Efeitos").assertIsSelected()
            compose.runOnIdle {assertTrue("variation=${vm.jukebox.variation}",vm.jukebox.variation<45f)}
            compose.onNodeWithTag("jukebox-transition").performTouchInput {swipe(androidx.compose.ui.geometry.Offset(width*.2f,centerY),androidx.compose.ui.geometry.Offset(width*.8f,centerY),350)}
            compose.onNodeWithTag("nav-Efeitos").assertIsSelected()
            compose.runOnIdle {assertTrue("smooth=${vm.jukebox.smooth}",vm.jukebox.smooth>35f)}
        } finally {compose.runOnIdle {vm.jukebox.stop();OndaStore.saveSettings(original)}}
    }

}
