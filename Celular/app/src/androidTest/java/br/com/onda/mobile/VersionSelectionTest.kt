package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class VersionSelectionTest {
    @Test fun manualRetryOverridesAutomaticForOnlyThisItem() {
        val settings=JSONObject().put("auto_match",true).put("confirm_version",false)
        val config=applyVersionSelection(JSONObject().put("_manual_version",true),settings)
        assertFalse(config.getBoolean("auto_match"))
        assertTrue(config.getBoolean("confirm_version"))
        assertTrue(settings.getBoolean("auto_match"))
        assertTrue(applyVersionSelection(JSONObject(),settings).getBoolean("auto_match"))
    }
    @Test fun queuedItemsUseCurrentAutomaticSetting() {
        val queued=JSONObject().put("auto_match",false).put("confirm_version",true).put("mode","flac").put("audio_quality","320 kbps")
        val current=JSONObject().put("auto_match",true).put("confirm_version",true)
        val config=applyVersionSelection(JSONObject(queued.toString()),current)
        assertTrue(config.getBoolean("auto_match"))
        assertFalse(config.getBoolean("confirm_version"))
        assertEquals("flac",config.getString("mode"))
        assertEquals("320 kbps",config.getString("audio_quality"))
        assertFalse(queued.getBoolean("auto_match"))
    }
    @Test fun disablingAutomaticRestoresCurrentConfirmationPreference() {
        val queued=JSONObject().put("auto_match",true).put("confirm_version",false)
        val current=JSONObject().put("auto_match",false).put("confirm_version",true)
        val config=applyVersionSelection(queued,current)
        assertFalse(config.getBoolean("auto_match"))
        assertTrue(config.getBoolean("confirm_version"))
    }
    @Test fun savedAlbumOptionsCannotOverrideGlobalSelection() {
        val current=JSONObject().put("auto_match",true).put("confirm_version",true)
        val album=JSONObject().put("auto_match",false).put("mode","mp3")
        assertTrue(applyVersionSelection(album,current).getBoolean("auto_match"))
    }
}
