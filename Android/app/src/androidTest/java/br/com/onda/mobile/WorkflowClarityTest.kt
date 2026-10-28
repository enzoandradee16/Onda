package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class WorkflowClarityTest {
    @get:Rule val compose=createComposeRule()

    @Test fun restartUsesPrivateSeparateProcessAndDurableSessionWrites() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val info=context.packageManager.getActivityInfo(android.content.ComponentName(context,RestartActivity::class.java),0)
        assertFalse(info.exported);assertEquals(context.packageName+":restart",info.processName)
        val key="restart-durable-test"
        try {
            PlaybackSessions.save(context,key,JSONObject().put("position",42),synchronous=true)
            assertEquals(42,PlaybackSessions.load(context,key)!!.getInt("position"))
            assertTrue(File(context.applicationInfo.dataDir,"shared_prefs/playback-sessions.xml").readText().contains(key))
        } finally {context.getSharedPreferences("playback-sessions",0).edit().remove(key).commit()}
    }

    @Test fun toolListKeepsTechnicalBannersHiddenUntilRequested() {
        val row=JSONObject().put("name","ffmpeg").put("icon","ffmpeg").put("version","9.0.2").put("status","Disponível").put("available",true)
        val report=JSONObject().put("tools",JSONArray().put(row)).put("checked_at","2026-10-27T23:38:29+00:00").put("details","ffmpeg version 9.0.2 Copyright technical banner")
        compose.setContent {MaterialTheme {ToolStatusList(report)}}
        compose.onNodeWithText("9.0.2",useUnmergedTree=true).assertIsDisplayed()
        compose.onNodeWithTag("tool-raw-details").assertDoesNotExist()
        compose.onNodeWithTag("tool-technical-details").performClick()
        compose.onNodeWithTag("tool-raw-details").assertIsDisplayed()
    }

    @Test fun failedPlaybackCardOffersRetryInsteadOfPlay() {
        var retried=0
        compose.setContent {MaterialTheme {
            PlaybackQueueRow(JSONObject().put("title","Broken song"),"",0,false,false,
                {retried++},{},{},{},false,false,preparation="Erro",failed=true)
        }}
        compose.onNodeWithText("Falha na preparação").assertIsDisplayed()
        compose.onNodeWithContentDescription("Tentar novamente").performClick()
        compose.runOnIdle {assertEquals(1,retried)}
    }

    @Test fun importedReferenceReportsMissingTracksWithoutReplacingCollection() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val file=File(context.filesDir,"clarity-reference.m3u")
        file.writeText("#EXTM3U\nhttps://youtu.be/abcdefghijk\nhttps://youtu.be/ABCDEFGHIJK\n")
        try {
            val tracks=JSONArray().put(JSONObject().put("source_url","https://www.youtube.com/watch?v=abcdefghijk"))
            val result=MobileEngine.call(context,"clarity-compare","compare_collection_file",JSONObject().put("source",file.absolutePath).put("tracks",tracks),EventCallback {})
            assertFalse(result.toString(),result.has("error"))
            assertEquals(1,result.getInt("matched"));assertEquals(1,result.getInt("missing"))
            assertEquals(1,tracks.length())
        } finally {file.delete()}
    }

    @Test fun localToolCheckShowsVersionsAndRetainsVerification() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val result=MobileEngine.call(context,"clarity-tools","tools_check",JSONObject(),EventCallback {})
        assertFalse(result.toString(),result.has("error"))
        val report=result.getJSONObject("report")
        assertTrue(report.getString("checked_at").isNotBlank())
        val rows=report.getJSONArray("tools").objects()
        assertEquals("Disponível",rows.first {it.getString("name")=="ffmpeg"}.getString("status"))
        assertTrue(rows.first {it.getString("name")=="Python"}.getString("version").isNotBlank())
        val saved=MobileEngine.call(context,"clarity-tools-read","tools_status",JSONObject(),EventCallback {})
        assertEquals(report.getString("checked_at"),saved.getJSONObject("report").getString("checked_at"))
    }
}
