package br.com.onda.mobile

import android.util.Base64
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class UnifiedPlaybackTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun categoryOrderIsNormalizedAndKeepsTabOrderAndVisibility() {
        val settings=OndaStore.defaults().put("hidden_tabs",JSONArray(listOf("Imagens")))
        val tabs=settings.getJSONArray("tab_order").toString()
        assertEquals(listOf("tools","library"),tabGroupOrder(settings))
        settings.put("tab_group_order",JSONArray(listOf("library","library","invalid")))
        OndaStore.normalizeAppearance(settings)
        assertEquals(listOf("library","tools"),tabGroupOrder(settings))
        assertEquals(tabs,settings.getJSONArray("tab_order").toString())
        assertEquals(listOf("Imagens"),hiddenTabs(settings))
        assertEquals(listOf("library","tools"),tabGroupOrder(JSONObject(settings.toString())))
        settings.put("tab_group_order",JSONArray())
        assertEquals(listOf("tools","library"),tabGroupOrder(settings))
    }
    @Test fun albumAndReleaseDateUseOneLineWithoutEmptySeparators() {
        val record=JSONObject().put("album","Discovery").put("release_date","2001-03-12")
        assertEquals("Discovery · 12/03/2001",albumReleaseText(record))
        assertEquals("12/03/2001",albumReleaseText(record,false))
        assertEquals("2001",albumReleaseText(JSONObject().put("release_date","2001")))
        assertEquals("Discovery",albumReleaseText(JSONObject().put("album","Discovery")))
        assertEquals("",albumReleaseText(JSONObject()))
    }
    @Test fun modernUsesSystemFontAndLegacyKeepsBundledInter() {
        assertEquals("ONDA Modern",OndaStore.defaults().getString("interface_font"))
        assertEquals(DEFAULT_INTERFACE_FONT,normalizeInterfaceFont("Padrão do sistema"))
        assertTrue(interfaceFonts.containsKey("ONDA Legacy"))
        assertNotEquals(interfaceFonts[DEFAULT_INTERFACE_FONT],interfaceFonts["ONDA Legacy"])
        context.resources.openRawResource(R.font.onda_modern).use {stream->assertEquals(0,stream.read());assertEquals(1,stream.read())}
        val modern=interfaceTypography(DEFAULT_INTERFACE_FONT)
        assertEquals(androidx.compose.ui.text.font.FontFamily.Default,interfaceFonts[DEFAULT_INTERFACE_FONT])
        assertEquals(androidx.compose.material3.Typography().titleMedium.fontWeight,modern.titleMedium.fontWeight)
        assertEquals(androidx.compose.material3.Typography().headlineMedium.fontWeight,modern.headlineMedium.fontWeight)
        val legacy=interfaceTypography("ONDA Legacy")
        assertEquals(androidx.compose.ui.text.font.FontWeight.SemiBold,legacy.titleMedium.fontWeight)
        assertEquals(androidx.compose.ui.text.font.FontWeight.Bold,legacy.headlineMedium.fontWeight)
    }
    @Test fun preparationPreferenceKeepsSupportedChoicesAndSafeDefault() {
        assertEquals(2,preparationAhead(JSONObject()))
        for(value in listOf(1,2,3,5)) {
            val settings=JSONObject().put("playback_prepare_ahead",value)
            OndaStore.normalizeAppearance(settings)
            assertEquals(value,preparationAhead(settings))
        }
        for(value in listOf(0,4,5000,true,"invalid"))assertEquals(2,preparationAhead(JSONObject().put("playback_prepare_ahead",value)))
    }
    @Test fun hugePlaybackCollectionIsBoundedAndAddedWithoutStartingAudio() {
        OndaStore.initialize(context)
        val scope=CoroutineScope(SupervisorJob().apply {cancel()}+Dispatchers.Main.immediate)
        val controller=JukeboxController(context,scope,{})
        try {
            controller.clearPlaybackQueue()
            val rows=(0 until 6000).map {JSONObject().put("title","Track $it").put("source_url","https://example.com/$it")}
            assertEquals(5000,controller.enqueueAll(rows));assertEquals(5000,controller.playbackQueue.value.size)
            assertEquals(0,controller.enqueueAll(rows));assertFalse(controller.state.value.playing)
        } finally {controller.clearPlaybackQueue();controller.close()}
    }
    @Test fun preparedQueueCacheSurvivesRestartWithoutKeepingRunningStatus() {
        val folder=File(context.cacheDir,"prepared-queue-${System.nanoTime()}").apply {mkdirs()}
        try {
            File(folder,"audio.wav").writeBytes(byteArrayOf(1))
            File(folder,"analysis.json").writeText("{\"beats\":[0,1],\"neighbors\":[[]]}")
            val model=JSONObject().put("cache",folder.absolutePath).put("source",File(folder,"audio.wav").absolutePath).put("media_title","Track")
            val row=JSONObject().put("_analysis","Analisando").put("_prepared_cache",preparedQueueReference(model))
            val restored=restoreQueueModel(JSONObject(row.toString()))
            assertEquals("Track",restored?.optString("media_title"));assertTrue(restored?.optBoolean("cached")==true)
            File(folder,"analysis.json").delete();assertNull(restoreQueueModel(row))
        } finally {folder.deleteRecursively()}
    }
    @Test fun mediaArtworkFallsBackFromInvalidEmbeddedPreview() {
        val image=android.graphics.Bitmap.createBitmap(4,4,android.graphics.Bitmap.Config.ARGB_8888)
        image.eraseColor(android.graphics.Color.CYAN)
        val buffer=java.io.ByteArrayOutputStream();image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,buffer);image.recycle()
        var requests=0
        val fallback=decodeMediaArtwork("not an image","https://example.com/cover.png") {requests++;buffer.toByteArray()}
        assertNotNull(fallback);assertEquals(1,requests);fallback?.recycle()
        val embedded="data:image/png;base64,"+Base64.encodeToString(buffer.toByteArray(),Base64.NO_WRAP)
        val local=decodeMediaArtwork(embedded,"https://example.com/cover.png") {fail("Embedded cover should be used");null}
        assertNotNull(local);local?.recycle()
    }
    @Test fun exportFromUntaggedCacheKeepsSongNameEffectsAndArtwork()=runBlocking {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val folder=File(context.cacheDir,"export-test-${System.nanoTime()}").apply {mkdirs()}
        val source=File(folder,"audio.wav")
        val data=ByteArray(44100*4*2)
        val header=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).put("RIFF".toByteArray()).putInt(36+data.size).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1).putShort(2).putInt(44100).putInt(176400).putShort(4).putShort(16).put("data".toByteArray()).putInt(data.size).array()
        source.outputStream().use {it.write(header);it.write(data)}
        val image=android.graphics.Bitmap.createBitmap(4,4,android.graphics.Bitmap.Config.ARGB_8888)
        image.eraseColor(android.graphics.Color.CYAN)
        val buffer=java.io.ByteArrayOutputStream();image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,buffer);image.recycle()
        val cover=Base64.encodeToString(buffer.toByteArray(),Base64.NO_WRAP)
        suspend fun call(action:String,config:JSONObject)=withContext(Dispatchers.IO){MobileEngine.call(context,"export-test-$action",action,config,EventCallback {}).also {assertFalse(it.optString("error"),it.has("error"))}}
        try {
            val record=JSONObject().put("title","Midnight Pretenders").put("artists",JSONArray().put("Tomoko Aran")).put("album","Fuyü-Kükan").put("release_date","1983-05-21")
            val config=call("effects_export_config",JSONObject().put("source",source.absolutePath).put("record",record).put("enabled",true).put("speed",85).put("reverb",25).put("cover_data",cover))
            assertEquals("Tomoko Aran - Midnight Pretenders - Slowed + Reverb",config.getString("export_name"))
            for(extension in listOf("mp3","m4a","flac","wav")) {
                val output=File(folder,config.getString("export_name")+"."+extension)
                val result=call("effects",JSONObject(config.toString()).put("output",output.absolutePath))
                assertEquals(result.toString(),0,result.getInt("code"))
                val info=call("audio_read",JSONObject().put("source",output.absolutePath));val tags=info.getJSONObject("record")
                assertEquals("Midnight Pretenders - Slowed + Reverb",tags.getString("title"));assertEquals("Tomoko Aran",tags.getJSONArray("artists").getString(0))
                assertEquals("Fuyü-Kükan",tags.getString("album"));assertEquals("1983-05-21",tags.getString("release_date"))
                assertTrue(tags.getDouble("duration")>2.5);assertTrue(info.optString("cover_preview").isNotBlank())
            }
        } finally {folder.deleteRecursively()}
    }
    @Test fun repeatButtonCyclesAllThreeModes() {
        val mode=androidx.compose.runtime.mutableStateOf("Desativada")
        compose.setContent {MaterialTheme {RepeatPlaybackButton(mode.value,{mode.value=it})}}
        compose.onNodeWithTag("playback-repeat").assertIsOff()
        for(value in listOf("Todas","Uma","Desativada")) {
            compose.onNodeWithTag("playback-repeat").performClick()
            compose.runOnIdle {assertEquals(value,mode.value)}
            compose.onNodeWithContentDescription("Repetição: $value").assertExists()
        }
        compose.onNodeWithTag("playback-repeat").assertIsOff()
    }
    @Test fun queueSearchCanCloseWithoutRemovingQueuedMusic() {
        OndaStore.initialize(context)
        val store=ViewModelStore()
        lateinit var vm:OndaViewModel
        compose.runOnUiThread {vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]}
        val count=vm.jukebox.playbackQueue.value.size
        try {
            compose.setContent {MaterialTheme {Column {PlaybackQueueSearch(vm,true)}}}
            compose.onNodeWithTag("playback-queue-search").performTextInput("Madonna")
            compose.onNodeWithTag("close-playback-queue-search").performClick()
            compose.onNodeWithTag("close-playback-queue-search").assertDoesNotExist()
            compose.runOnIdle {assertEquals(count,vm.jukebox.playbackQueue.value.size)}
        } finally {compose.runOnUiThread {store.clear()}}
    }
    @Test fun normalTransitionWithEffectsSchedulesCrossfadeWithoutTimer()=runBlocking {
        OndaStore.initialize(context)
        val old=JSONObject(OndaStore.settings.value.toString())
        OndaStore.saveSettings(JSONObject(old.toString()).put("jukebox_gradual_transition",true).put("jukebox_transition_seconds",2))
        val folder=File(context.cacheDir,"normal-transition-test").apply {mkdirs()}
        File(folder,"analysis.json").writeText("{}")
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        try {withContext(Dispatchers.Main) {
            val controller=JukeboxController(context,scope,{}, {_,_,_->JSONObject()})
            val first=JSONObject().put("_queue_id","first").put("title","First")
            val next=JSONObject().put("_queue_id","next").put("title","Next")
            val model=JSONObject().put("cache",folder.absolutePath).put("duration",20).put("beats",JSONArray((0..20).toList()))
            controller.normal=true;controller.effects.value=JSONObject().put("enabled",true).put("speed",85)
            controller.playbackQueue.value=listOf(first,next);controller.currentQueueId.value="first"
            controller.state.value=JukeboxState(model=model,index=18,playing=true)
            val field=controller.javaClass.getDeclaredField("preparedModels").apply {isAccessible=true}
            @Suppress("UNCHECKED_CAST") val prepared=field.get(controller) as MutableMap<String,JSONObject>
            prepared["next"]=model
            assertEquals(0,controller.switchMinutes.value);assertEquals(0,controller.timerMinutes.value)
            controller.javaClass.getDeclaredMethod("normalTransition").apply {isAccessible=true}.invoke(controller)
            val request=controller.javaClass.getDeclaredField("switchRequest").apply {isAccessible=true}.get(controller) as java.util.concurrent.atomic.AtomicReference<*>
            assertNotNull(request.get());controller.close()
        }} finally {scope.cancel();File(folder,"analysis.json").delete();folder.delete();OndaStore.saveSettings(old)}
    }

    @Test fun bothControlsChangeOnePlayerAndOneQueue() {
        val store=ViewModelStore()
        OndaStore.initialize(context);MobileEngine.initialize(context)
        lateinit var vm:OndaViewModel
        compose.runOnUiThread {
            vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
            vm.jukebox.stop();vm.jukebox.clearPlaybackQueue();vm.jukebox.normal=true
            vm.jukebox.setEffects("enabled",false)
        }
        try {
            compose.setContent {MaterialTheme {Column(Modifier.fillMaxSize()){Box(Modifier.weight(1f)){PlaybackPage(vm)};AndroidPlaybackSurface(vm)}}}
            compose.onNodeWithTag("unified-effects-card").assertExists()
            compose.onNodeWithText("Efeitos").performScrollTo().performClick()
            compose.runOnIdle {assertTrue(vm.jukebox.effects.value.optBoolean("enabled"))}
            compose.onNodeWithText("Jukebox infinito").performScrollTo().performClick()
            compose.runOnIdle {assertFalse(vm.jukebox.normal);assertTrue(vm.jukebox.effects.value.optBoolean("enabled"));assertFalse(vm.jukebox.state.value.playing)}
            compose.onNodeWithTag("unified-open-queue").performClick()
            compose.runOnIdle {assertTrue(vm.playbackQueueOpen.value)}
            val image=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
            File(context.getExternalFilesDir(null),"unified-android-queue.png").outputStream().use {image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};image.recycle()
        } finally {compose.runOnUiThread {vm.jukebox.stop();store.clear()}}
    }

    @Test fun actualAndroidEngineCombinesEffectsWithoutModifyingBeatAnalysis()=runBlocking {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val source=File(context.cacheDir,"unified-tone.wav")
        val samples=ByteBuffer.allocate(44100*4*8).order(ByteOrder.LITTLE_ENDIAN)
        repeat(44100*8){i->val x=(kotlin.math.sin(i*2*Math.PI*440/44100)*4000).toInt().toShort();samples.putShort(x);samples.putShort(x)}
        val header=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).put("RIFF".toByteArray()).putInt(36+samples.capacity()).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1).putShort(2).putInt(44100).putInt(176400).putShort(4).putShort(16).put("data".toByteArray()).putInt(samples.capacity()).array()
        source.outputStream().use {it.write(header);it.write(samples.array())}
        val session="unified-engine-test"
        suspend fun call(action:String,config:JSONObject)=withContext(Dispatchers.IO){MobileEngine.call(context,"unified-test-$action",action,config,EventCallback {}).also {assertFalse(it.optString("error"),it.has("error"))}}
        try {
            val model=call("jukebox_prepare",OndaStore.config().put("source",source.absolutePath))
            val analysis=File(model.getString("cache"),"analysis.json");val original=analysis.readBytes()
            val effects=JSONObject().put("enabled",true).put("speed",85).put("reverb",25).put("keep_pitch",true)
            val prepared=call("jukebox_effects",JSONObject().put("cache",model.getString("cache")).put("effects",effects))
            assertEquals("",prepared.optString("error_detail"))
            call("jukebox_open",JSONObject().put("session",session).put("cache",model.getString("cache")))
            val first=call("jukebox_chunk",JSONObject().put("session",session).put("effects",effects).put("normal",false))
            assertTrue(Base64.decode(first.getString("pcm"),Base64.NO_WRAP).isNotEmpty())
            delay(100)
            val part=call("jukebox_chunk",JSONObject().put("session",session).put("effects",effects).put("normal",false))
            assertFalse(part.optBoolean("effects_pending"));assertEquals("",part.optString("effects_error"));assertArrayEquals(original,analysis.readBytes())
        } finally {
            call("jukebox_close",JSONObject().put("session",session));source.delete()
        }
    }

    @Test fun oldEffectsQueueMergesOnceAndRestoresWithoutSound()=runBlocking {
        OndaStore.initialize(context)
        val prefs=context.getSharedPreferences("playback-sessions",0)
        val old=prefs.getString("jukebox",null)
        val source=File(context.cacheDir,"unified-migration.wav").apply {writeBytes(byteArrayOf(0))}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        try {
            prefs.edit().remove("jukebox").commit()
            withContext(Dispatchers.Main) {
                var calls=0
                val controller=JukeboxController(context,scope,{}, {_,_,_->calls++;JSONObject()})
                val data=JSONObject().put("queue",JSONArray().put(source.absolutePath)).put("source",source.absolutePath).put("position",42).put("speed",75)
                controller.migrateEffectsSession(data);controller.migrateEffectsSession(data)
                assertEquals(1,controller.playbackQueue.value.size);assertEquals(42.0,controller.playbackQueue.value.first().getDouble("_restore_seconds"),0.0)
                assertFalse(controller.state.value.playing);assertEquals(0,calls);assertEquals(75,controller.effects.value.getInt("speed"));controller.close()
            }
        } finally {
            scope.cancel();source.delete();prefs.edit().apply {if(old==null)remove("jukebox") else putString("jukebox",old)}.commit()
        }
    }
}
