package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LocalizationTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before() {
            val instrumentation=InstrumentationRegistry.getInstrumentation()
            if(android.os.Build.VERSION.SDK_INT>=33) instrumentation.uiAutomation.grantRuntimePermission(instrumentation.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
        }
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()

    @Test fun sharedCatalogTranslatesMessagesAndKeepsBrand() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("Spotify connected",translateUi("Spotify conectado","en",context))
        assertEquals("Album · 14 tracks",translateUi("Álbum · 14 músicas","en",context))
        assertEquals("Search · 25 seconds",translateUi("Pesquisa · 25 segundos","en",context))
        assertEquals("Account connected. Paste your playlist link in the Playlists tab.",translateUi("Conta conectada. Cole o link da sua playlist na aba Playlists.","en",context))
        assertEquals("Settings",translateUi("Configurações","en",context))
        assertEquals("ONDA",translateUi("ONDA","en",context))
        assertEquals("Search queue · 2 of 5 completed",translateUi("Fila da pesquisa · 2 de 5 concluídas","en",context))
        assertEquals("MP3 · Completed",translateUi("MP3 · Concluído","en",context))
        assertEquals("Minha música favorita",translateUi("Minha música favorita","en",context))
        assertEquals("Configurações",translateUi("Configurações","pt-BR",context))
        assertEquals("pt-BR",normalizedLanguage("invalid"))
    }

    @Test fun settingsSwitchImmediatelyAndPersistWithoutRememberingOtherOptions() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("language","pt-BR"))}
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithText("Configurações").performScrollTo().performClick()
            compose.onNodeWithText("Geral").performClick()
            compose.onNodeWithText("Português (Brasil)").performScrollTo().performClick()
            compose.onNodeWithText("English").performClick()
            compose.onNodeWithText("Language").assertIsDisplayed()
            compose.onNodeWithText("Preferences").assertIsDisplayed()
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("remember",false))}
            val saved=JSONObject(OndaStore.context.getSharedPreferences("preferences",0).getString("settings","{}")!!)
            assertEquals("en",saved.optString("language"))
            assertFalse(saved.optBoolean("remember",true))
            assertEquals(before.optString("theme"),OndaStore.settings.value.optString("theme"))
            compose.onNodeWithText("Done").performClick()
            val pages=linkedMapOf(
                "Pesquisar" to "Find your next track.",
                "Links e fila" to "From a link to your library.",
                "Imagens" to "Download, convert and resize without cropping the image.",
                "Playlists / Álbuns" to "Your albums and playlists in your library.",
                "Efeitos" to "Your music, in a new way.",
                "Histórico" to "Your download library.")
            pages.forEach {(page,heading)->
                compose.onNodeWithTag("open-menu").performClick()
                compose.onNodeWithTag("tab-$page").performScrollTo().performClick()
                compose.onNodeWithText(heading).assertIsDisplayed()
            }
            assertTrue(compose.onAllNodesWithText("ONDA").fetchSemanticsNodes().isNotEmpty())
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("language","pt-BR"))}
            compose.onNodeWithText("Sua biblioteca de downloads.").assertIsDisplayed()
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }
}
