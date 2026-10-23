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
class SecondaryLocalizationTest {
    @get:Rule val compose=createComposeRule()
    @Test fun downloadPopupTranslatesFallbackWithoutChangingSongOrArtist() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        compose.setContent {
            LocalizedTheme("en",darkColorScheme(),MaterialTheme.typography) {
                TrackDownloadDialog(JSONObject().put("title","Original").put("artists",org.json.JSONArray(listOf("Spotify conectado"))),JSONObject(),{}, {_,_->})
            }
        }
        compose.onNodeWithText("Choose a format").assertIsDisplayed()
        compose.onNodeWithText("Album not provided").assertIsDisplayed()
        compose.onNodeWithText("Original").assertIsDisplayed()
        compose.onNodeWithText("Spotify conectado").assertIsDisplayed()
        compose.onNodeWithText("Download now").assertIsDisplayed()
        compose.onNodeWithText("Álbum não informado").assertDoesNotExist()
    }
}
