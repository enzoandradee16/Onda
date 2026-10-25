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
class SettingsNotificationSearchTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    @Test fun notificationSearchShowsCategoriesAndOpensRealControl() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("language","pt-BR"))}
            compose.onNodeWithTag("open-settings").performClick()
            compose.onNodeWithTag("settings-search").performTextInput("notificacoes")
            compose.onAllNodesWithText("Configurações › Geral").assertCountEquals(2)
            val target=compose.onNodeWithTag("settings-result-Downloads-Controles na notificação")
            target.performScrollTo().assertIsDisplayed()
            target.performClick()
            compose.onNodeWithText("Controles na notificação").performScrollTo().assertIsDisplayed()
            compose.onNodeWithTag("settings-result-Downloads-Controles na notificação").assertDoesNotExist()
            for((language,query) in listOf("pt-BR" to "notificacoes","en" to "notifications","es" to "notificaciones")) {
                val found=settingsSearchEntries().filter {settingsSearchMatches(query,settingsSearchText(it,language))}
                assertTrue(found.any {it.label=="Duração dos avisos" && it.category=="Geral"})
                assertTrue(found.any {it.label=="Animar avisos" && it.category=="Geral"})
                assertTrue(found.any {it.label=="Controles na notificação" && it.category=="Downloads"})
                assertTrue(found.any {it.label=="Ação ao terminar a fila" && it.category=="Downloads"})
            }
            assertTrue(settingsSearchEntries().any {it.label=="Ação ao terminar a fila" && settingsSearchMatches("notification sound",settingsSearchText(it,"en"))})
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }
}
