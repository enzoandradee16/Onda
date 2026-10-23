package br.com.onda.mobile

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class BlackDialogTest {
    @get:Rule val compose=createComposeRule()
    @Test fun popupIsBlackWithAndWithoutSeparators() {
        val separators=mutableStateOf(false)
        compose.setContent {
            val base=darkColorScheme(background=Color.Black,surfaceContainerHigh=Color(0xFF181818),surfaceTint=Color.Transparent)
            MaterialTheme(colorScheme=pureBlackSurfaces(base,separators.value)) {
                AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={},title={Text("Aviso")},text={Text("Mensagem de teste")},confirmButton={TextButton(onClick={}){Text("OK")}})
            }
        }
        for(value in listOf(false,true)) {
            compose.runOnIdle {separators.value=value}
            val pixels=compose.onNode(isDialog()).captureToImage().toPixelMap()
            assertEquals(Color.Black,pixels[pixels.width/2,20])
        }
    }
}
