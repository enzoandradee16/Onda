package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ErrorNoticeUiTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    @Test fun errorDialogsFollowLanguageAndKeepTrackNamesAndPaths() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
        val before=JSONObject(OndaStore.settings.value.toString())
        val vm=ViewModelProvider(compose.activity)[OndaViewModel::class.java]
        val raw="PermissionError: [Errno 13] Permission denied: '/data/user/0/onda/audio.mp3'"
        try {
            for((language,phrase) in listOf("pt-BR" to "Permissão negada","es" to "Permiso denegado","en" to "Permission denied")) {
                compose.runOnIdle {vm.dismissNotice();OndaStore.saveSettings(JSONObject(before.toString()).put("language",language));vm.showNotice("Not Found",raw,error=true)}
                compose.waitForIdle()
                compose.onNodeWithText("Not Found").assertIsDisplayed()
                compose.onNodeWithText(phrase,substring=true).assertIsDisplayed()
                compose.onNodeWithText("[Errno 13]",substring=true).assertIsDisplayed()
                compose.onNodeWithText("'/data/user/0/onda/audio.mp3'",substring=true).assertIsDisplayed()
            }
        } finally {compose.runOnIdle {vm.dismissNotice();OndaStore.saveSettings(before)}}
    }
}
