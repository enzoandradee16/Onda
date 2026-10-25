package br.com.onda.mobile
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class SettingsSearchTest {
    @get:Rule val compose=createComposeRule()
    @Test fun searchFindsAndNavigatesToCache() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        OndaStore.initialize(context)
        val previous=JSONObject(OndaStore.settings.value.toString())
        OndaStore.saveSettings(JSONObject(previous.toString()).put("check_updates",false).put("language","pt-BR"))
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        val store=androidx.lifecycle.ViewModelStore();store.put("test",vm)
        try {
            assertEquals(listOf("Geral","Aparência","Downloads","Imagens","Áudio","Contas","Ferramentas"),settingsCategoryOrder())
            assertEquals(settingsCategoryOrder(),categories.keys.toList())
            assertTrue("check_updates" in categories.getValue("Ferramentas"))
            assertFalse("check_updates" in categories.getValue("Geral"))
            assertTrue(settingsSearchEntries().any {it.category=="Downloads" && it.label=="Agendar downloads"})
            assertTrue(settingsSearchEntries().any {it.category=="Ferramentas" && it.label=="Limpar cache"})
            assertTrue(settingsSearchMatches("audio conexao","Áudio · Conexão"))
            assertFalse(settingsSearchMatches("impossivelxyz","Limpar cache"))
            compose.setContent {MaterialTheme {SettingsWindow(vm,initialCategory="Geral") {}}}
            compose.onNodeWithTag("settings-search").performTextInput("limpar cache")
            compose.onNodeWithTag("settings-result-Ferramentas-Limpar cache").performClick()
            compose.onNodeWithText("Limpar cache").assertIsDisplayed()
            compose.onNodeWithTag("settings-search").performTextInput("Tamanho máximo")
            compose.onNodeWithTag("settings-result-Imagens-Tamanho máximo").performClick()
            compose.onNodeWithText("Tamanho máximo").assertIsDisplayed()
            compose.onNodeWithContentDescription("Tamanho máximo: Original").performClick()
            compose.onNodeWithText("Até 1920 × 1080").performClick()
            assertEquals(1920,OndaStore.settings.value.optInt("image_width"))
            assertEquals(1080,OndaStore.settings.value.optInt("image_height"))

        } finally {
            instrumentation.runOnMainSync {store.clear()}
            OndaStore.saveSettings(previous)
        }
    }
}
