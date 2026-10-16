package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
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
class LayoutSpacingUiTest {
    @get:Rule val compose=createComposeRule()
    @Test fun appearanceChoiceAppliesLiveAndSurvivesReload() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val original=JSONObject(OndaStore.settings.value.toString())
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        try {
            OndaStore.saveSettings(JSONObject(original.toString()).put("remember",true).put("language","pt-BR").put("interface_spacing","Padrão"))
            compose.setContent {
                val settings by OndaStore.settings.collectAsState()
                LocalizedTheme("pt-BR",MaterialTheme.colorScheme,MaterialTheme.typography,settings.optString("interface_spacing")) {
                    SettingsWindow(vm,"Aparência") {}
                }
            }
            compose.onNodeWithText("Padrão").performScrollTo().performClick()
            compose.onNodeWithText("Confortável").performClick()
            compose.runOnIdle {assertEquals("Confortável",OndaStore.settings.value.getString("interface_spacing"))}
            compose.onNodeWithText("Confortável").performClick()
            compose.onNode(hasText("Compacto") and hasAnyAncestor(isPopup())).performClick()
            compose.runOnIdle {
                assertEquals("Compacto",OndaStore.settings.value.getString("interface_spacing"))
                OndaStore.initialize(context)
                assertEquals("Compacto",OndaStore.settings.value.getString("interface_spacing"))
                assertTrue("interface_spacing" in categories.getValue("Aparência"))
            }
        } finally {OndaStore.saveSettings(original)}
    }
}
