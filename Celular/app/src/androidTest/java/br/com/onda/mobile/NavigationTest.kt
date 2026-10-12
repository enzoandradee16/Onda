package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class NavigationTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()

    @Test fun spotifyConnectAppearsOnlyForSpotifyAndValidatesClientId() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val before=JSONObject(OndaStore.settings.value.toString())
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("spotify_client_id",""))}
            compose.onNodeWithTag("search-connect-spotify").assertDoesNotExist()
            compose.onNodeWithText("Deezer").performClick()
            compose.onNodeWithText("Spotify").performClick()
            compose.onNodeWithTag("search-connect-spotify").assertIsDisplayed().performClick()
            compose.onNodeWithText("Aviso").assertIsDisplayed()
            compose.onNodeWithText("Preencha o Spotify Client ID antes de conectar sua conta. O Client Secret é opcional para esta conexão.").assertIsDisplayed()
            assertFalse(vm.busy.value)
            compose.onNodeWithText("OK").performClick()
            compose.onNodeWithText("Spotify").performClick()
            compose.onNodeWithText("Apple / iTunes").performClick()
            compose.onNodeWithTag("search-connect-spotify").assertDoesNotExist()
        } finally {compose.runOnIdle {OndaStore.saveSettings(before);vm.dialogNotice.value=""}}
    }

    @Test fun navigateEveryPageAndSettings() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) {
            compose.onNodeWithText("Agora não").performClick()
        }
        val pages=linkedMapOf(
            "Pesquisar" to "Encontre sua próxima música.",
            "Links e fila" to "Do link para sua biblioteca.",
            "Imagens" to "Baixe, converta e ajuste o tamanho sem cortar a imagem.",
            "Playlists / Álbuns" to "Seus álbuns e playlists na biblioteca.",
            "Histórico" to "Sua biblioteca de downloads.",
            "Efeitos" to "Desacelere ou acelere sua música. Adicione reverb se quiser.")
        pages.forEach {(tab,content)->
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithTag("tab-$tab").performScrollTo().performClick()
            compose.onNodeWithText(content).assertIsDisplayed()
        }
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithText("Configurações").performScrollTo().performClick()
        compose.onNodeWithText("Aparência").assertExists()
        compose.onNodeWithText("Downloads").performScrollTo().performClick()
        compose.onNodeWithText("Downloads").performScrollTo().performClick()
        compose.onNodeWithText("Áudio").performScrollTo().performClick()
        compose.onNodeWithText("Contas").performScrollTo().performClick()
    }
    @Test fun presetAndPreviewButtonFollowState() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithTag("tab-Efeitos").performClick()
        compose.onNodeWithText("Clássico").performClick()
        compose.onNodeWithText("Atmosférico").performClick()
        compose.onNodeWithText("Atmosférico").assertIsDisplayed()
        capture("effects-alpha2.png")
        compose.onNodeWithTag("open-menu").performClick()
        capture("drawer-alpha2.png")
        compose.onNodeWithTag("tab-Pesquisar").performClick()
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithTag("tab-Efeitos").performClick()
        compose.onNodeWithText("Atmosférico").assertIsDisplayed()
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithTag("tab-Pesquisar").performClick()
        compose.runOnIdle {
            vm.searchResults.value=listOf(JSONObject().put("title","Prévia teste").put("preview_url","https://example.com/test.mp3"))
            vm.previewUrl.value="https://example.com/test.mp3";vm.previewActive.value=true
        }
        compose.onNodeWithText("Parar prévia").performClick()
        compose.onNodeWithText("Ouvir prévia").assertIsDisplayed()
    }

    @Test fun foregroundServiceDownloadsAndPublishes() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val fixture=JSONObject(module.callAttr("start_fixture",context.cacheDir.absolutePath).toString())
        val before=OndaStore.history.value.map {it.uri}.toSet()
        val id=OndaStore.enqueue(fixture.getString("url"),"Vídeo de teste do serviço",extra=JSONObject().put("folder",fixture.getString("folder")).put("mode","mp4").put("duplicate_policy","keep"))
        try {
            DownloadService.start(context,id)
            val deadline=System.currentTimeMillis()+30000
            while(System.currentTimeMillis()<deadline && OndaStore.items.value.firstOrNull {it.id==id}?.state !in listOf("Concluído","Erro")) Thread.sleep(200)
            assertEquals(OndaStore.messages.value.joinToString("\n"),"Concluído",OndaStore.items.value.first {it.id==id}.state)
            val saved=OndaStore.history.value.filter {it.uri !in before}
            assertEquals(1,saved.size)
            context.contentResolver.openInputStream(android.net.Uri.parse(saved.first().uri))!!.use {assertTrue(it.readBytes().size>1000)}
        } finally {
            DownloadService.stop(context)
            OndaStore.history.value.filter {it.uri !in before}.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null)}
            OndaStore.remove(setOf(id));OndaStore.clearHistory()
            module.callAttr("stop_fixture")
        }
    }

    @Test fun versionAndMetadataDialogsConfirm() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val answer=java.util.concurrent.atomic.AtomicReference<JSONObject>()
        val candidates=org.json.JSONArray().put(JSONObject().put("id","fixture-id").put("title","Versão de teste"))
        OndaStore.ask("choice-fixture",JSONObject().put("type","choose_version").put("candidates",candidates)) {answer.set(it)}
        compose.onNodeWithText("Versão de teste").performClick()
        compose.onNodeWithText("Baixar esta versão").performClick()
        assertEquals("fixture-id",answer.get().getString("selected_id"))
        val record=JSONObject().put("title","Música").put("artists",org.json.JSONArray().put("Artista")).put("album",JSONObject.NULL).put("genre",JSONObject.NULL).put("cover_url",JSONObject.NULL)
        OndaStore.ask("review-fixture",JSONObject().put("type","review_metadata").put("record",record)) {answer.set(it)}
        compose.onNodeWithText("Confirmar e baixar").performClick()
        val changes=answer.get().getJSONObject("changes")
        assertEquals("Música",changes.getString("title"))
        assertEquals("",changes.getString("cover_url"))
        assertEquals("",changes.getString("genre"))
        assertEquals("Artista",changes.getJSONArray("artists").getString(0))
    }
    private fun capture(name:String) {
        compose.waitForIdle()
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val bitmap=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        java.io.File(context.cacheDir,name).outputStream().use {bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
        bitmap.recycle()
    }
    @Test fun youtubeSessionCanBeSavedAndClosed() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val ready=java.util.concurrent.atomic.AtomicBoolean(false)
        compose.runOnIdle {android.webkit.CookieManager.getInstance().setCookie("https://www.youtube.com","ONDA_SESSION_FIXTURE=local-test; Domain=.youtube.com; Path=/; Secure") {ready.set(it)}}
        compose.waitUntil(10000) {ready.get()}
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithText("Sessão do YouTube").performScrollTo().performClick()
        compose.onNodeWithText("Usar esta sessão").assertIsDisplayed().performClick()
        val path=OndaStore.settings.value.getString("youtube_cookies_file")
        val file=java.io.File(path)
        assertTrue(file.readText().contains("ONDA_SESSION_FIXTURE\tlocal-test"))
        compose.runOnIdle {
            file.delete()
            OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("youtube_cookies_file",""))
            android.webkit.CookieManager.getInstance().removeAllCookies(null)
        }
    }
    @Test fun historyOpensDownloadedAudioInEffects() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val fixture=JSONObject(module.callAttr("start_fixture",context.cacheDir.absolutePath).toString())
        val folder=java.io.File(fixture.getString("folder")).parentFile!!
        val source=java.io.File(folder,"Histórico teste.mp3")
        val original=OndaStore.history.value
        var uri=""
        try {
            module.callAttr("create_history_audio",folder.absolutePath)
            uri=OndaStore.publish(source.absolutePath,OndaStore.config().put("folder",folder.absolutePath).put("duplicate_policy","keep"),"mp3").toString()
            assertFalse(historySupportsEffects(HistoryItem(-1,"Foto.png","","png",0)))
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithTag("tab-Histórico").performClick()
            compose.onNodeWithText("Usar nos efeitos").performScrollTo().performClick()
            val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
            compose.waitUntil(15000) {vm.effectsSource.value.isNotBlank() && !vm.busy.value}
            compose.onNodeWithText("Histórico teste.mp3").assertIsDisplayed()
            compose.onNodeWithText("Slowed · Sped Up · Reverb").assertIsDisplayed()
            assertArrayEquals(source.readBytes(),java.io.File(vm.effectsSource.value).readBytes())
            java.io.File(vm.effectsSource.value).delete()
        } finally {
            if(uri.isNotBlank()) context.contentResolver.delete(android.net.Uri.parse(uri),null,null)
            OndaStore.clearHistory();OndaStore.history.value=original
            module.callAttr("stop_fixture")
        }
    }
    @Test fun searchQueueAndWindowNoticesAreVisible() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        assertEquals("3:03",mediaClock(183));assertEquals("7:09",mediaClock(429));assertEquals("0:00",mediaClock(-1));assertEquals("61:01",mediaClock(3661))
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        val record=JSONObject().put("title","Música de pesquisa").put("artists",org.json.JSONArray().put("Artista")).put("source_url","https://example.com/audio.mp3").put("duration_ms",429000)
        val before=OndaStore.items.value.map {it.id}.toSet()
        val settings=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Pesquisar").performClick()
            compose.runOnIdle {vm.searchResults.value=listOf(record)}
            compose.onNodeWithText("7:09").assertIsDisplayed()
            compose.onNodeWithText("Adicionar à fila").performScrollTo().performClick()
            val id=OndaStore.items.value.first {it.id !in before}.id
            assertEquals("search",OndaStore.items.value.first {it.id==id}.config.getString("_origin"))
            compose.onNodeWithTag("search-queue").performScrollTo().assertIsDisplayed()
            compose.runOnIdle {OndaStore.update(id,"Baixando",40f)}
            compose.onNodeWithText("Baixando").assertIsDisplayed()
            compose.runOnIdle {OndaStore.update(id,"Concluído",100f)}
            compose.onNodeWithText("Concluído").assertIsDisplayed()
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(settings.toString()).put("spotify_client_id",""))}
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithText("Configurações").performScrollTo().performClick()
            compose.onNodeWithText("Contas").performScrollTo().performClick()
            compose.onNodeWithText("Abrir Spotify Developers").performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("Conectar").performScrollTo().performClick()
            compose.onNodeWithText("Preencha o Spotify Client ID antes de conectar sua conta. O Client Secret é opcional para esta conexão.").assertIsDisplayed()
            compose.onNodeWithText("OK").performClick()
            compose.onNodeWithText("Conectar").assertIsDisplayed()
        } finally {
            OndaStore.remove(OndaStore.items.value.filter {it.id !in before}.map {it.id}.toSet());OndaStore.saveSettings(settings)
            compose.runOnIdle {vm.dialogNotice.value="";vm.searchResults.value=emptyList()}
        }
    }
    @Test fun removeOnlyOneSearchQueueItem() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val before=OndaStore.items.value.map {it.id}.toSet()
        var first="";var second=""
        try {
            compose.runOnIdle {
                val options=OndaStore.config().put("_origin","search")
                first=OndaStore.enqueue("https://example.com/one.mp3","Primeira música",extra=options)
                second=OndaStore.enqueue("https://example.com/two.mp3","Segunda música",extra=options)
            }
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Pesquisar").performClick()
            compose.onNodeWithTag("remove-search-$first").performScrollTo().performClick()
            compose.runOnIdle {OndaStore.refresh()}
            assertFalse(OndaStore.items.value.any {it.id==first})
            assertTrue(OndaStore.items.value.any {it.id==second})
            compose.runOnIdle {OndaStore.active.value=second}
            compose.onNodeWithTag("remove-search-$second").assertIsNotEnabled()
        } finally {
            compose.runOnIdle {OndaStore.active.value="";OndaStore.remove(OndaStore.items.value.filter {it.id !in before}.map {it.id}.toSet())}
        }
    }
    @Test fun removeHistoryPreservesFilesAndOtherRecords() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val folder=java.io.File(context.cacheDir,"history-removal").apply {mkdirs()}
        val first=java.io.File(folder,"Primeiro teste.mp3").apply {writeBytes(ByteArray(100){42})}
        val second=java.io.File(folder,"Segundo teste.mp3").apply {writeBytes(ByteArray(110){43})}
        val before=OndaStore.history.value.map {it.id}.toSet()
        val uris=mutableListOf<android.net.Uri>()
        try {
            compose.runOnIdle {
                for(file in listOf(first,second)) uris+=OndaStore.publish(file.absolutePath,OndaStore.config().put("folder",folder.absolutePath).put("duplicate_policy","keep"),"mp3")
            }
            val records=OndaStore.history.value.filter {it.id !in before}
            val target=records.first {it.title==first.name}
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Histórico").performClick()
            compose.onNodeWithTag("remove-history-${target.id}").performScrollTo().performClick()
            compose.runOnIdle {OndaStore.refresh()}
            assertFalse(OndaStore.history.value.any {it.id==target.id})
            assertTrue(OndaStore.history.value.any {it.id==records.first {it.title==second.name}.id})
            context.contentResolver.openInputStream(android.net.Uri.parse(target.uri))!!.use {assertArrayEquals(first.readBytes(),it.readBytes())}
        } finally {
            uris.forEach {context.contentResolver.delete(it,null,null)}
            OndaStore.history.value.filter {it.id !in before}.forEach {OndaStore.removeHistory(it.id)}
            folder.deleteRecursively()
        }
    }
    @Test fun swipeSettingsCategories() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithText("Configurações").performScrollTo().performClick()
        compose.onNodeWithText("Aparência").assertIsSelected()
        compose.onNodeWithTag("settings-pages").performTouchInput {swipeLeft()}
        compose.waitForIdle()
        compose.onNodeWithText("Downloads").assertIsSelected()
        compose.onNodeWithTag("settings-pages").performTouchInput {swipeRight()}
        compose.waitForIdle()
        compose.onNodeWithText("Aparência").assertIsSelected()
    }
    @Test fun effectsSlidersRefreshPlayingPreview() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val folder=java.io.File(context.cacheDir,"live-effects").apply {mkdirs()}
        module.callAttr("create_live_audio",folder.absolutePath)
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            compose.runOnIdle {vm.effectsSource.value=java.io.File(folder,"Histórico teste.mp3").absolutePath}
            compose.waitUntil(15000) {!vm.busy.value}
            compose.onNodeWithText("Ouvir com efeitos").performScrollTo().performClick()
            compose.waitUntil(20000) {vm.previewUrl.value.contains("preview-") && vm.previewActive.value}
            val initial=vm.previewUrl.value
            compose.onNodeWithTag("effects-speed").performScrollTo().performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.SetProgress) {it(120f)}
            compose.onNodeWithTag("effects-reverb").performScrollTo().performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.SetProgress) {it(40f)}
            compose.waitUntil(20000) {vm.previewUrl.value!=initial && vm.previewActive.value}
            assertTrue(vm.effectsPreviewEnabled.value)
            assertTrue(java.io.File(vm.previewUrl.value).exists())
            compose.runOnIdle {vm.stopPreview()}
            val stopped=vm.previewUrl.value
            compose.onNodeWithTag("effects-speed").performScrollTo().performSemanticsAction(androidx.compose.ui.semantics.SemanticsActions.SetProgress) {it(110f)}
            Thread.sleep(700)
            assertEquals(stopped,vm.previewUrl.value)
        } finally {compose.runOnIdle {vm.stopPreview();vm.effectsSource.value=""};folder.deleteRecursively()}
    }

    @Test fun appearanceNamesMigrateAndMatchDesktop() {
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("accent","Menta").put("theme","Sistema"))}
            assertEquals("Verde-Água",OndaStore.settings.value.getString("accent"))
            assertEquals("Seguir o sistema",OndaStore.settings.value.getString("theme"))
            assertFalse(accents.containsKey("Menta"))
            assertEquals(accents.keys,lightAccents.keys)
            assertEquals("Álbuns e playlists",tabLabel("Playlists / Álbuns"))
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithText("Configurações").performScrollTo().performClick()
            compose.onNodeWithText("Verde-Água").assertIsDisplayed()
            compose.onNodeWithText("Seguir o sistema").assertIsDisplayed()
            compose.onNodeWithText("Geral").performClick()
            compose.onNodeWithText("Lembrar configurações").assertIsDisplayed()
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }

    @Test fun fontChangesAcrossInterfaceAndPersists() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("interface_font",DEFAULT_INTERFACE_FONT).put("remember",true))}
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithText("Configurações").performScrollTo().performClick()
            compose.onNodeWithTag("font-preview").performScrollTo()
            val initial=compose.onNodeWithText("Tema e cores").captureToImage().asAndroidBitmap()
            compose.onNodeWithText(DEFAULT_INTERFACE_FONT).performClick()
            compose.onNodeWithText("Monoespaçada").performClick()
            compose.waitForIdle()
            assertEquals("Monoespaçada",OndaStore.settings.value.getString("interface_font"))
            val rendered=compose.onNodeWithText("Tema e cores").captureToImage().asAndroidBitmap()
            assertFalse("A fonte precisa alterar o título da categoria, além da prévia",initial.sameAs(rendered))
            val stored=OndaStore.context.getSharedPreferences("preferences",0).getString("settings",null)!!
            assertEquals("Monoespaçada",JSONObject(stored).getString("interface_font"))
            compose.onNodeWithText("Pronto").performClick()
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithText("Configurações").performScrollTo().performClick()
            compose.onNodeWithText("Monoespaçada").assertIsDisplayed().performClick()
            compose.onNodeWithText(DEFAULT_INTERFACE_FONT).performClick()
            compose.waitForIdle()
            assertTrue(initial.sameAs(compose.onNodeWithText("Tema e cores").captureToImage().asAndroidBitmap()))
            assertTrue(categories.getValue("Aparência").contains("interface_font"))
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }

    @OptIn(androidx.compose.ui.test.ExperimentalTestApi::class)
    @Test fun enterSearchesAndOnlyLinksAcceptsNewlines() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        module.callAttr("start_enter_search_fixture")
        try {
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Pesquisar").performClick()
            compose.onNodeWithTag("music-query").performTextClearance()
            compose.onNodeWithTag("music-query").performTextInput("Primeira música")
            compose.onNodeWithTag("music-query").performKeyInput {pressKey(androidx.compose.ui.input.key.Key.Enter)}
            compose.waitUntil(15000) {vm.searchResults.value.any {it.optString("title")=="Resultado: Primeira música"}}
            assertEquals(1,module.callAttr("enter_search_count").toInt())
            compose.onNodeWithTag("music-query").assertTextContains("Primeira música")
            compose.waitUntil(5000) {!vm.busy.value}
            compose.onNodeWithTag("music-query").performTextClearance()
            compose.onNodeWithTag("music-query").performTextInput("Segunda música")
            compose.onNodeWithTag("music-query").performImeAction()
            compose.waitUntil(15000) {vm.searchResults.value.any {it.optString("title")=="Resultado: Segunda música"}}
            assertEquals(2,module.callAttr("enter_search_count").toInt())
            compose.waitUntil(5000) {!vm.busy.value}
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Links e fila").performClick()
            compose.onNodeWithTag("links-input").performTextClearance()
            compose.onNodeWithTag("links-input").performTextInput("https://example.com/one.mp3")
            compose.onNodeWithTag("links-input").performKeyInput {pressKey(androidx.compose.ui.input.key.Key.Enter)}
            compose.onNodeWithTag("links-input").performTextInput("https://example.com/two.mp3")
            compose.onNodeWithTag("links-input").assertTextContains("https://example.com/one.mp3\nhttps://example.com/two.mp3")
            assertEquals(2,module.callAttr("enter_search_count").toInt())
        } finally {
            module.callAttr("stop_enter_search_fixture")
            compose.runOnIdle {vm.searchResults.value=emptyList()}
        }
    }

}
