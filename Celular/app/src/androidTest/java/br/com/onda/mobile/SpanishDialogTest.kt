package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SpanishDialogTest {
    @get:Rule val compose=createComposeRule()
    @Test fun spanishPopupPreservesOriginalSongData() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        compose.setContent {
            LocalizedTheme("es",darkColorScheme(),MaterialTheme.typography) {
                TrackDownloadDialog(JSONObject().put("title","Configurações").put("artists",org.json.JSONArray(listOf("Original"))),JSONObject(),{}, {_,_->})
            }
        }
        compose.onNodeWithText("Elige el formato").assertIsDisplayed()
        compose.onNodeWithText("Álbum no indicado").assertIsDisplayed()
        compose.onNodeWithText("Configurações").assertIsDisplayed()
        compose.onNodeWithText("Original").assertIsDisplayed()
        compose.onNodeWithText("Descargar ahora").assertIsDisplayed()
        compose.onNodeWithText("Álbum não informado").assertDoesNotExist()
    }
}
