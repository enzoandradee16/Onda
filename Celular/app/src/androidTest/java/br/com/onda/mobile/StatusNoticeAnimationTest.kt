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
class StatusNoticeAnimationTest {
    @get:Rule val compose=createComposeRule()
    @Test fun animatedNoticeKeepsTextUntilExitCompletesAndReappears() {
        val visible=mutableStateOf(false)
        compose.mainClock.autoAdvance=false
        compose.setContent {MaterialTheme {TopStatusNotice("Aviso animado",visible.value,false,true,{}, {visible.value=false})}}
        compose.runOnIdle {visible.value=true}
        compose.mainClock.advanceTimeBy(300)
        compose.onNodeWithText("Aviso animado").assertIsDisplayed()
        compose.runOnIdle {visible.value=false}
        compose.mainClock.advanceTimeBy(32)
        compose.onNodeWithText("Aviso animado").assertExists()
        compose.mainClock.advanceTimeBy(300)
        compose.onNodeWithText("Aviso animado").assertDoesNotExist()
        compose.runOnIdle {visible.value=true}
        compose.mainClock.advanceTimeBy(300)
        compose.onNodeWithText("Aviso animado").assertIsDisplayed()
    }
    @Test fun disabledAnimationDismissesImmediatelyAndPreservesCancel() {
        val visible=mutableStateOf(true)
        val busy=mutableStateOf(true)
        var cancelled=false
        compose.mainClock.autoAdvance=false
        compose.setContent {MaterialTheme {TopStatusNotice("Aviso sem animação",visible.value,busy.value,false,{cancelled=true},{visible.value=false})}}
        compose.mainClock.advanceTimeBy(64)
        compose.onNodeWithText("Cancelar").performClick()
        compose.runOnIdle {assertTrue(cancelled);busy.value=false}
        compose.mainClock.advanceTimeBy(64)
        compose.onNodeWithContentDescription("Fechar aviso").performClick()
        compose.mainClock.advanceTimeBy(64)
        compose.onNodeWithText("Aviso sem animação").assertDoesNotExist()
    }
    @Test fun animationPreferenceSurvivesReloadAndBelongsToGeneralReset() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val original=JSONObject(OndaStore.settings.value.toString())
        try {
            assertTrue(OndaStore.defaults().getBoolean("notice_animation"))
            OndaStore.saveSettings(JSONObject(original.toString()).put("remember",true).put("notice_animation",false))
            OndaStore.initialize(context)
            assertFalse(OndaStore.settings.value.getBoolean("notice_animation"))
            assertTrue("notice_animation" in categories.getValue("Geral"))
        } finally {OndaStore.saveSettings(original)}
    }
    @Test fun clickableGuidanceFollowsCurrentMessageAndCloseDoesNotNavigate() {
        val status=mutableStateOf("ONDA 1.1.3 disponível · Configurações → Ferramentas")
        val visible=mutableStateOf(true)
        var opened=""
        compose.setContent {MaterialTheme {TopStatusNotice(status.value,visible.value,false,false,{}, {visible.value=false}, {opened=it})}}
        compose.onNodeWithTag("app-status").assertHasClickAction().performClick()
        compose.runOnIdle {assertEquals("Ferramentas",opened);status.value="Conecte sua conta Spotify primeiro."}
        compose.onNodeWithTag("app-status").performClick()
        compose.runOnIdle {assertEquals("Contas",opened);opened=""}
        compose.onNodeWithContentDescription("Fechar aviso").performClick()
        compose.runOnIdle {assertEquals("",opened);assertFalse(visible.value);visible.value=true;status.value="Concluído"}
        compose.onNodeWithTag("app-status").assertHasNoClickAction()
    }
}
