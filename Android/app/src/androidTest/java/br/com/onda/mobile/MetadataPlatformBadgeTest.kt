package br.com.onda.mobile
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class MetadataPlatformBadgeTest {
    @get:Rule val compose=createComposeRule()
    @Test fun iconAndNameIdentifyMetadataNotAudio() {
        val record=JSONObject().put("platform","Spotify").put("source_url","https://youtube.com/watch?v=x")
        assertEquals("spotify",metadataPlatform(record))
        for(name in listOf("Apple / iTunes","AppleMusic","Apple Music","iTunes"))assertEquals("apple_music",metadataPlatform(JSONObject().put("platform",name)))
        compose.setContent {MaterialTheme {MetadataPlatformBadge(record)}}
        compose.onNodeWithText("Spotify").assertExists()
        compose.onAllNodesWithContentDescription("Spotify",substring=true).assertCountEquals(1)
    }
    @Test fun unknownOriginDoesNotPretendToBeYoutube() {
        assertEquals("",metadataPlatform(JSONObject().put("url","https://youtube.com/watch?v=x")))
        compose.setContent {MaterialTheme {MetadataPlatformBadge(JSONObject())}}
        compose.onNodeWithText("YouTube").assertDoesNotExist()
    }
    @Test fun imageIconPreservesWebsiteAndSocialPlatform() {
        compose.setContent {MaterialTheme {androidx.compose.foundation.layout.Column {
            MetadataPlatformBadge(JSONObject(),source="https://images.example.com/photo.jpg",imageMedia=true)
            MetadataPlatformBadge(JSONObject(),source="https://instagram.com/p/test",imageMedia=true)
            MetadataPlatformBadge(JSONObject(),imageMedia=true)
        }}}
        compose.onAllNodesWithContentDescription("Imagens").assertCountEquals(3)
        compose.onNodeWithText("images.example.com").assertExists()
        compose.onNodeWithContentDescription("Plataforma: Instagram").assertExists()
    }
}
