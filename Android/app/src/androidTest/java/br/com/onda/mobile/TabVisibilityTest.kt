package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TabVisibilityTest {
    @Test fun hidesOnlyOptionalTabsAndKeepsSavedOrder() {
        val settings=JSONObject().put("tab_order",JSONArray(listOf("Histórico","Fila","Imagens","Pesquisar","Links e fila")))
            .put("hidden_tabs",JSONArray(listOf("Histórico","Imagens","Fila","invalid","Imagens")))
        assertEquals(listOf("Imagens","Histórico"),hiddenTabs(settings))
        val visible=visibleTabs(settings)
        assertEquals(listOf("Fila","Pesquisar","Links e fila"),(0 until visible.length()).map {visible.getString(it)})
        assertTrue(hiddenTabs(JSONObject().put("hidden_tabs","invalid")).isEmpty())
    }
    @Test fun persistedPreferencesSurviveReloadAndCanBeRestored() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val previous=JSONObject(OndaStore.settings.value.toString())
        try {
            val settings=JSONObject(previous.toString()).put("remember",true).put("hidden_tabs",JSONArray(listOf("Histórico","Imagens","Fila")))
            OndaStore.saveSettings(settings)
            val saved=JSONObject(context.getSharedPreferences("preferences",0).getString("settings","{}")!!)
            assertEquals(listOf("Imagens","Histórico"),hiddenTabs(saved))
            OndaStore.saveSettings(JSONObject(saved.toString()).put("hidden_tabs",JSONArray()))
            assertTrue(hiddenTabs(OndaStore.settings.value).isEmpty())
        } finally {OndaStore.saveSettings(previous)}
    }
}
