package br.com.onda.mobile

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TrackCardLayoutTest {
    @get:Rule val compose=createComposeRule()
    @Test fun allThreeButtonsFitWithoutHorizontalScrolling() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        var downloads=0
        compose.setContent {MaterialTheme {
            Box(Modifier.width(340.dp).testTag("track-width")) {
                TrackCard(JSONObject().put("title","Around the World"),vm,{downloads++})
            }
        }}
        val bounds=compose.onNodeWithTag("track-width").fetchSemanticsNode().boundsInRoot
        for(label in listOf("Ouvir prévia","Adicionar à fila","Baixar agora")) {
            val button=compose.onNodeWithText(label)
            button.assertIsDisplayed()
            assertTrue(label,button.fetchSemanticsNode().boundsInRoot.right<=bounds.right)
        }
        compose.onNodeWithText("Baixar agora").performClick()
        compose.runOnIdle {assertEquals(1,downloads)}
    }
}
