package br.com.onda.mobile

import androidx.compose.material3.*
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

@RunWith(AndroidJUnit4::class)
class MetadataChangesLayoutTest {
    @get:Rule val compose = createComposeRule()

    @Test fun uncheckedFieldsAreExcludedFromSaveReply() {
        OndaStore.initialize(InstrumentationRegistry.getInstrumentation().targetContext)
        val fields = JSONArray().put(
            JSONObject().put("key", "title").put("label", "Título").put("before", "Antes").put("after", "Depois")
        )
            .put(
                JSONObject().put(
                    "key",
                    "album"
                ).put("label", "Álbum").put("before", "Antigo").put("after", "Novo álbum")
            )
        val report = JSONObject().put(
            "type",
            "review_metadata_changes"
        ).put("entries", JSONArray().put(JSONObject().put("name", "Música.wav").put("fields", fields)))
        var reply: JSONObject? = null
        val question = Question("preview-test", report) { reply = it }
        compose.runOnIdle { OndaStore.question.value = question }
        compose.setContent {
            LocalizedTheme("pt-BR", lightColorScheme(), Typography()) { MetadataChangesWindow(question) }
        }
        compose.onNodeWithText("Atual: Antes").assertIsDisplayed()
        compose.onNodeWithText("Novo: Depois").assertIsDisplayed()
        compose.onNodeWithContentDescription("Título").performClick()
        compose.onNodeWithText("Salvar alterações").performClick()
        compose.runOnIdle {
            assertEquals(
                listOf("album"),
                reply!!.getJSONObject("selected").getJSONArray("0").let { a ->
                    (0 until a.length()).map { a.getString(it) }
                }
            )
        }
    }
}
