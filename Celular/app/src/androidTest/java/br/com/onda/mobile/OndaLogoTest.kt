package br.com.onda.mobile

import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class OndaLogoTest {
    @get:Rule val compose=createComposeRule()
    @Test fun logoPixelsFollowAccentChangesImmediately() {
        val accent=mutableStateOf(Color.Red)
        compose.setContent {MaterialTheme(colorScheme=darkColorScheme(primary=accent.value)) {
            OndaLogo(Modifier.size(48.dp).testTag("logo"),"Ícone ONDA")
        }}
        fun center():Color {
            val pixels=compose.onNodeWithTag("logo").captureToImage().toPixelMap()
            return pixels[pixels.width/2,pixels.height/2]
        }
        assertEquals(Color.Red,center())
        compose.runOnIdle {accent.value=Color.Blue}
        compose.waitForIdle()
        assertEquals(Color.Blue,center())
    }
}
