package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AppearanceWindowTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    private fun dismissWelcome() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
    }
    @Test fun iconOpensQuickWindowAndSharesPersistedChoicesWithSettings() {
        dismissWelcome()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("language","pt-BR").put("remember",true).put("theme","Preto puro").put("accent","Verde-Água"))}
            val appearance=compose.onNodeWithTag("open-appearance").fetchSemanticsNode().boundsInRoot
            val settings=compose.onNodeWithTag("open-settings").fetchSemanticsNode().boundsInRoot
            assertTrue(appearance.right<=settings.left)
            assertEquals(appearance.top,settings.top,1f)
            compose.onNodeWithTag("open-appearance").performClick()
            compose.onNodeWithTag("appearance-dialog").assertIsDisplayed()
            compose.onNodeWithText("Preto puro").performClick()
            compose.onNodeWithText("Claro").performClick()
            compose.onNodeWithText("Verde-Água").performClick()
            compose.onNodeWithText("Azul").performClick()
            compose.runOnIdle {
                assertEquals("Claro",OndaStore.settings.value.optString("theme"))
                assertEquals("Azul",OndaStore.settings.value.optString("accent"))
                val stored=JSONObject(OndaStore.context.getSharedPreferences("preferences",0).getString("settings","{}")!!)
                assertEquals("Claro",stored.getString("theme"));assertEquals("Azul",stored.getString("accent"))
            }
            compose.onNodeWithTag("appearance-done").performClick()
            compose.onNodeWithTag("appearance-dialog").assertDoesNotExist()
            compose.onNodeWithTag("open-settings").performClick()
            compose.onNodeWithText("Aparência").performClick()
            compose.onNodeWithText("Claro").performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("Azul").performScrollTo().assertIsDisplayed()
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }
    @Test fun quickWindowAndIconFollowLanguageAndCanReopenInEachTheme() {
        dismissWelcome()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            for((language,title) in listOf("pt-BR" to "Aparência","en" to "Appearance","es" to "Apariencia")) {
                compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("language",language))}
                compose.onNodeWithTag("open-appearance").assertContentDescriptionEquals(title)
                compose.onNodeWithTag("open-appearance").performClick()
                compose.onNodeWithText(title).assertIsDisplayed()
                compose.onNodeWithTag("appearance-done").performClick()
            }
            for(theme in listOf("Claro","Escuro","Preto puro","Alto contraste")) {
                compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("theme",theme))}
                compose.onNodeWithTag("open-appearance").performClick()
                compose.onNodeWithTag("appearance-dialog").assertIsDisplayed()
                compose.onNodeWithTag("appearance-done").performClick()
            }
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }
}
