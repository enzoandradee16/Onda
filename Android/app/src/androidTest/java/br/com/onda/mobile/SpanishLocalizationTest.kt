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
class SpanishLocalizationTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before() {
            val instrumentation=InstrumentationRegistry.getInstrumentation()
            if(android.os.Build.VERSION.SDK_INT>=33) instrumentation.uiAutomation.grantRuntimePermission(instrumentation.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
        }
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()

    @Test fun catalogParityTemplatesAndLanguageCacheIsolation() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val english=JSONObject(context.assets.open("en.json").bufferedReader().use {it.readText()})
        val spanish=JSONObject(context.assets.open("es.json").bufferedReader().use {it.readText()})
        assertEquals(english.keys().asSequence().toSet(),spanish.keys().asSequence().toSet())
        assertEquals(listOf("pt-BR","es","en"),UI_LANGUAGES)
        assertEquals("pt-BR",OndaStore.defaults().optString("language"))
        for(key in spanish.keys()) assertEquals(key,spanish.getString(key),translateUi(key,"es",context))
        assertEquals("Settings",translateUi("Configurações","en",context))
        assertEquals("Configuración",translateUi("Configurações","es",context))
        assertEquals("Settings",translateUi("Configurações","en",context))
        assertEquals("MP3 · Completado",translateUi("MP3 · Concluído","es",context))
        assertEquals("Cola de búsqueda · 2 de 5 completadas",translateUi("Fila da pesquisa · 2 de 5 concluídas","es",context))
        assertEquals("Álbum · 14 canciones",translateUi("Álbum · 14 músicas","es",context))
        assertEquals("ONDA",translateUi("ONDA","es",context))
    }

    @Test fun selectorOrderPersistenceAndSpanishNavigation() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
        val before=JSONObject(OndaStore.settings.value.toString())
        try {
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(before.toString()).put("language","pt-BR"))}
            compose.onNodeWithTag("open-menu").performClick()
            compose.onNodeWithText("Configurações").performScrollTo().performClick()
            compose.onNodeWithText("Geral").performClick()
            compose.onNodeWithText("Português (Brasil)").performScrollTo().performClick()
            val portuguese=compose.onNode(hasText("Português (Brasil)") and hasAnyAncestor(isPopup())).fetchSemanticsNode().boundsInRoot.top
            val spanish=compose.onNodeWithText("Español").fetchSemanticsNode().boundsInRoot.top
            val english=compose.onNodeWithText("English").fetchSemanticsNode().boundsInRoot.top
            assertTrue(portuguese<spanish && spanish<english)
            compose.onNodeWithText("Español").performClick()
            compose.onNodeWithText("Preferencias").assertIsDisplayed()
            compose.onNodeWithText("Idioma").assertIsDisplayed()
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("remember",false))}
            val saved=JSONObject(OndaStore.context.getSharedPreferences("preferences",0).getString("settings","{}")!!)
            assertEquals("es",saved.optString("language"))
            assertFalse(saved.optBoolean("remember",true))
            compose.onNodeWithText("Listo").performClick()
            val pages=linkedMapOf(
                "Pesquisar" to "Encuentra tu próxima canción.",
                "Links e fila" to "Del enlace a tu biblioteca.",
                "Imagens" to "Descarga, convierte y cambia el tamaño sin recortar la imagen.",
                "Playlists / Álbuns" to "Tus álbumes y listas de reproducción en la biblioteca.",
                "Efeitos" to "Tu música, de una nueva forma.",
                "Metadados" to "Edita los metadatos de tu canción.",
                "Histórico" to "Tu biblioteca de descargas.")
            pages.forEach {(page,heading)->
                compose.onNodeWithTag("open-menu").performClick()
                compose.onNodeWithTag("tab-$page").performScrollTo().performClick()
                compose.onNodeWithText(heading).assertIsDisplayed()
            }
            compose.runOnIdle {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("language","pt-BR"))}
            compose.onNodeWithText("Sua biblioteca de downloads.").assertIsDisplayed()
        } finally {compose.runOnIdle {OndaStore.saveSettings(before)}}
    }
}
