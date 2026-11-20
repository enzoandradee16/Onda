package br.com.onda.mobile

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class MetadataChoiceLayoutTest {
    @get:Rule val compose = createComposeRule()

    @Test fun compactCardsFormatDatesAndKeepSingleSelectionInBothThemes() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val vm = OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        val dark = mutableStateOf(true)
        val event = JSONObject().put("type", "choose_catalog").put(
            "candidates",
            JSONArray(
                (1..3).map { index ->
                    JSONObject().put("source_url", "test:$index").put("title", "Beijo (Interlude)")
                        .put("artists", JSONArray(listOf("Earth, Wind & Fire"))).put(
                            "album",
                            if (index ==
                                2
                            ) "The Eternal Dance" else "All 'N All"
                        )
                        .put(
                            "release_date",
                            "1977-11-21T08:00:00Z"
                        ).put("platform", if (index == 3) "Deezer" else "Apple / iTunes")
                        .put(
                            "genre",
                            "R&B/soul"
                        ).put("duration_ms", 80000).put("track_number", index).put("disc_number", 1)
                }
            )
        )
        var reply: JSONObject? = null
        val question = Question("metadata-style", event) { reply = it }
        compose.runOnIdle { OndaStore.question.value = question }
        compose.setContent {
            val colors = if (dark.value) pureBlackSurfaces(
                darkColorScheme(primary = Color(0xFF74DFC3)),
                false
            ) else lightColorScheme(primary = Color(0xFF176B58))
            LocalizedTheme("pt-BR", colors, Typography()) { ChoiceWindow(question, vm) }
        }
        compose.onNodeWithText("Usar estes metadados").assertIsNotEnabled()
        compose.onAllNodesWithText("1977-11-21T08:00:00Z", substring = true).assertCountEquals(0)
        compose.onAllNodesWithText("21/11/1977", substring = true).assertCountEquals(3)
        val radios = hasClickAction() and SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.RadioButton)
        compose.onAllNodes(radios).assertCountEquals(3)
        compose.onAllNodes(radios)[0].performClick().assertIsSelected()
        compose.onAllNodes(radios)[1].performScrollTo().performClick().assertIsSelected()
        compose.onAllNodes(radios)[0].assertIsNotSelected()
        compose.onNodeWithText("Usar estes metadados").assertIsEnabled()
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        for (light in listOf(false, true)) {
            compose.runOnIdle { dark.value = !light }
            compose.waitForIdle()
            val bitmap = instrumentation.uiAutomation.takeScreenshot()
            val values = android.content.ContentValues().apply {
                put(
                    android.provider.MediaStore.Downloads.DISPLAY_NAME,
                    "metadata-popup-${if(light)"light" else "dark"}.png"
                )
                put(android.provider.MediaStore.Downloads.MIME_TYPE, "image/png")
                put(android.provider.MediaStore.Downloads.RELATIVE_PATH, "Download/ONDA-QA-tests")
            }
            val uri = context.contentResolver.insert(
                android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                values
            )!!
            context.contentResolver.openOutputStream(uri)!!.use {
                bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it)
            }
            bitmap.recycle()
        }
        compose.onNodeWithText("Usar estes metadados").performClick()
        compose.runOnIdle { assertEquals("test:2", reply!!.getString("selected_id")) }
    }
}
