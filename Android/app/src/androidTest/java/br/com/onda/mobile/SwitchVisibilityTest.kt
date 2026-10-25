package br.com.onda.mobile

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class SwitchVisibilityTest {
    @get:Rule val compose=createComposeRule()
    @Test fun switchRemainsVisibleWhenOffOnAndDisabledAcrossThemes() {
        val checked=mutableStateOf(false)
        val enabled=mutableStateOf(true)
        val theme=mutableStateOf(0)
        compose.setContent {
            val base=darkColorScheme(primary=Color(0xFF79E2C4),onPrimary=Color.Black,onSurface=Color.White,onSurfaceVariant=Color(0xFFAFBBC9))
            val scheme=when(theme.value){0->pureBlackSurfaces(base,false);1->base;2->lightColorScheme();else->highContrastScheme()}
            MaterialTheme(colorScheme=scheme) {Surface {ToolSwitch("Controle",checked.value,enabled=enabled.value){checked.value=it}}}
        }
        for(mode in 0..3)for(active in listOf(false,true))for(available in listOf(false,true)) {
            compose.runOnIdle {theme.value=mode;checked.value=active;enabled.value=available}
            compose.waitForIdle()
            val image=compose.onNodeWithTag("switch-indicator-Controle",useUnmergedTree=true).captureToImage().toPixelMap()
            var darkest=1f;var lightest=0f
            for(y in 0 until image.height)for(x in 0 until image.width) {
                val pixel=image[x,y];val value=(pixel.red+pixel.green+pixel.blue)/3f
                darkest=minOf(darkest,value);lightest=maxOf(lightest,value)
            }
            assertTrue("mode=$mode checked=$active enabled=$available: invisible switch",lightest-darkest>.10f)
        }
        compose.runOnIdle {theme.value=0;checked.value=false;enabled.value=true}
        compose.onNodeWithText("Controle").performClick()
        compose.runOnIdle {assertTrue(checked.value)}
    }
}
