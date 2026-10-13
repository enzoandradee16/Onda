package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.time.LocalTime

@RunWith(AndroidJUnit4::class)
class AdvancedFeatureTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    private fun ready() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
    }
    @Test fun nativeEditingNormalizationLyricsAndTransfer() {
        ready();val context=InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        assertTrue(Python.getInstance().getModule("mobile_advanced_smoke").callAttr("verify",context.cacheDir.absolutePath).toBoolean())
    }
    @Test fun queueOrderSurvivesReloadAndScheduleHandlesMidnight() {
        ready()
        val a=OndaStore.enqueue("https://example.com/a.mp3");val b=OndaStore.enqueue("https://example.com/b.mp3")
        try {
            OndaStore.move(b,0);OndaStore.refresh();assertEquals(b,OndaStore.items.value.first().id)
            val options=JSONObject().put("schedule_enabled",true).put("schedule_start","22:00").put("schedule_stop","07:00")
            assertTrue(scheduleAllowed(options,LocalTime.of(23,0)));assertTrue(scheduleAllowed(options,LocalTime.of(6,59)))
            assertFalse(scheduleAllowed(options,LocalTime.of(7,0)));assertFalse(scheduleAllowed(options,LocalTime.of(21,59)))
        } finally {OndaStore.remove(setOf(a,b))}
    }
    @Test fun parallelQueueCompletesTwoRealDownloads() {
        ready();val context=InstrumentationRegistry.getInstrumentation().targetContext;MobileEngine.initialize(context)
        val fixture=JSONObject(Python.getInstance().getModule("mobile_smoke").callAttr("start_fixture",context.cacheDir.absolutePath).toString())
        val options=JSONObject(OndaStore.settings.value.toString());val before=JSONObject(options.toString())
        options.put("mode","mp3").put("concurrent_downloads","2").put("normalize_volume",true).put("duplicate_policy","keep")
        OndaStore.saveSettings(options)
        val a=OndaStore.enqueue(fixture.getString("url"),options=options);val b=OndaStore.enqueue(fixture.getString("url"),options=options)
        val past=OndaStore.history.value.map {it.id}.toSet()
        try {
            DownloadService.batch(context,listOf(a,b));var simultaneous=false
            val deadline=android.os.SystemClock.uptimeMillis()+90000
            while(android.os.SystemClock.uptimeMillis()<deadline) {
                if(DownloadRuntime.ids.size==2)simultaneous=true
                if(OndaStore.items.value.filter {it.id in setOf(a,b)}.all {it.state in listOf("Concluído","Erro")} && !OndaStore.running.value)break
                android.os.SystemClock.sleep(50)
            }
            assertTrue("Dois downloads devem executar simultaneamente",simultaneous)
            val items=OndaStore.items.value.filter {it.id in setOf(a,b)}
            assertTrue(items.joinToString {it.state+": "+it.message},items.all {it.state=="Concluído"})
            val downloaded=OndaStore.history.value.filter {it.id !in past}
            assertEquals(2,downloaded.size);assertEquals(2,downloaded.map {it.uri}.distinct().size)
        } finally {
            DownloadService.stop(context);OndaStore.remove(setOf(a,b));OndaStore.saveSettings(before)
            OndaStore.history.value.filter {it.id !in past}.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null);OndaStore.removeHistory(it.id)}
            Python.getInstance().getModule("mobile_smoke").callAttr("stop_fixture")
        }
    }

    @Test fun historyEditorSavesCopyThroughTheDialog() {
        ready();val context=InstrumentationRegistry.getInstrumentation().targetContext;MobileEngine.initialize(context)
        val module=Python.getInstance().getModule("mobile_smoke")
        val fixture=JSONObject(module.callAttr("start_fixture",context.cacheDir.absolutePath).toString())
        val source=java.io.File(module.callAttr("create_history_audio",java.io.File(fixture.getString("folder")).parent).toString())
        val before=OndaStore.history.value.map {it.id}.toSet()
        val options=OndaStore.config().put("duplicate_policy","keep")
        OndaStore.publish(source.absolutePath,options,"mp3")
        val vm=androidx.lifecycle.ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        try {
            compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Histórico").performClick()
            compose.onNodeWithText("Pesquisar no histórico").performTextInput("Histórico teste")
            compose.onAllNodesWithText("Editar metadados").onFirst().performScrollTo().performClick()
            compose.waitUntil(15000) {!vm.busy.value && compose.onAllNodesWithText("Música").fetchSemanticsNodes().isNotEmpty()}
            compose.onNodeWithText("Música").performScrollTo().performTextReplacement("Título corrigido no Android")
            compose.onNodeWithText("Normalizar volume (−16 LUFS)").performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("Salvar cópia editada").performScrollTo().assertIsEnabled().performClick()
            compose.waitUntil(30000) {!vm.busy.value}
            assertEquals("Mensagem: ${vm.dialogNotice.value}; status: ${vm.status.value}",2,OndaStore.history.value.count {it.id !in before})
            compose.onNodeWithTag("app-status").assertTextEquals("Cópia editada salva na pasta de destino.").assertIsDisplayed()
            compose.onNodeWithText("Escolher outro arquivo").performScrollTo().performClick()
            assertEquals(2,OndaStore.history.value.count {it.id !in before})
        } finally {
            InstrumentationRegistry.getInstrumentation().runOnMainSync {vm.stopPreview()}
            OndaStore.history.value.filter {it.id !in before}.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null);OndaStore.removeHistory(it.id)}
            module.callAttr("stop_fixture")
        }
    }

    @Test fun reopeningPreservesAnExistingScheduledRequest() {
        ready();val context=InstrumentationRegistry.getInstrumentation().targetContext
        val before=JSONObject(OndaStore.settings.value.toString())
        val clock=LocalTime.now();val formatter=java.time.format.DateTimeFormatter.ofPattern("HH:mm")
        val options=JSONObject(before.toString()).put("schedule_enabled",true)
            .put("schedule_start",clock.plusHours(1).format(formatter)).put("schedule_stop",clock.plusHours(2).format(formatter))
        val manager=androidx.work.WorkManager.getInstance(context)
        fun pending()=manager.getWorkInfosForUniqueWork("onda-scheduled-downloads").get(10,java.util.concurrent.TimeUnit.SECONDS).filter {!it.state.isFinished}.map {it.id}.toSet()
        try {
            OndaStore.saveSettings(options);val original=pending();assertEquals(1,original.size)
            DownloadSchedule.configure(context,options,keepExisting=true);assertEquals(original,pending())
            DownloadSchedule.configure(context,options);assertNotEquals(original,pending())
        } finally {OndaStore.saveSettings(before)}
    }
}
