package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.core.app.ApplicationProvider
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import kotlin.math.ln

class EqualizerBandsTest {
    @get:Rule val compose=createComposeRule()
    private val context get()=ApplicationProvider.getApplicationContext<android.content.Context>()

    @Test fun settingsMatchPythonAndLastBandActuallyProcessesPcm() {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val value=cleanEqualizerSettings(JSONObject().put("enabled",true).put("preamp",-9))
        value.getJSONArray("bands").let {bands->for(i in 0 until bands.length()) {
            val row=bands.getJSONObject(i);row.put("gain",ln(row.getDouble("frequency")/1000)/ln(2.0)).put("q",2.5)
        }}
        for(count in listOf(5,10,15)) {
            val expected=resizeEqualizerSettings(value,count)
            val report=JSONObject(Python.getInstance().getModule("equalizer_bands_smoke").callAttr("verify",value.toString(),count).toString())
            val actual=report.getJSONObject("settings")
            assertEquals(count,actual.getInt("band_count"));assertEquals(count,actual.getJSONArray("bands").length())
            assertEquals(-9.0,actual.getDouble("preamp"),.0001);assertTrue(actual.getBoolean("enabled"))
            for(i in 0 until count) for(key in listOf("frequency","gain","q")) {
                assertEquals(expected.getJSONArray("bands").getJSONObject(i).getDouble(key),actual.getJSONArray("bands").getJSONObject(i).getDouble(key),.00001)
            }
            assertEquals(.5012,report.getDouble("gain"),.02)
        }
        assertEquals(10,cleanEqualizerSettings(JSONObject()).getInt("band_count"))
        assertEquals(15,cleanEqualizerSettings(JSONObject().put("bands",JSONArray((1..15).map {JSONObject()}))).getInt("band_count"))
    }

    @Test fun dialogChangesBandCountPreservesPresetAndRestoresChosenLayout() {
        OndaStore.initialize(context)
        val previous=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnUiThread {OndaStore.saveSettings(JSONObject(previous.toString()).put("language","pt-BR").put("jukebox_equalizer",JSONObject()))}
            compose.setContent {JukeboxEqualizerDialog {}}
            fun choose(count:Int) {
                compose.onNodeWithContentDescription("Quantidade de bandas: "+OndaStore.settings.value.optJSONObject("jukebox_equalizer")?.optInt("band_count",10).let {it ?: 10}).performScrollTo().performClick()
                compose.onNodeWithText(count.toString()).performClick()
                compose.runOnIdle {assertEquals(count,OndaStore.settings.value.getJSONObject("jukebox_equalizer").getJSONArray("bands").length())}
            }
            choose(15)
            compose.onNodeWithContentDescription("Preset: Plano").performScrollTo().performClick()
            compose.onNodeWithText("Rock").performClick()
            choose(5);choose(10);choose(15)
            compose.onNodeWithContentDescription("Preset: Rock").performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("Restaurar").performClick()
            compose.runOnIdle {assertEquals(15,OndaStore.settings.value.getJSONObject("jukebox_equalizer").getInt("band_count"));assertFalse((0 until 15).any {OndaStore.settings.value.getJSONObject("jukebox_equalizer").getJSONArray("bands").getJSONObject(it).getDouble("gain")!=0.0})}
            compose.onNodeWithText("Pronto").performClick()
        } finally {compose.runOnUiThread {OndaStore.saveSettings(previous)}}
    }
}
