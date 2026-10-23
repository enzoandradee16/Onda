package br.com.onda.mobile

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import org.junit.Assert.*
import org.junit.Test

class JukeboxGraphColorsTest {
    @Test fun graphIsVisibleWithoutPureBlackSeparators() {
        val base=darkColorScheme(primary=Color(0xFF65DFBD))
        val black=pureBlackSurfaces(base,false)
        assertEquals(Color.Black,black.outline)
        for(scheme in listOf(base,black,highContrastScheme())) {
            val (ring,links)=jukeboxGraphColors(scheme)
            assertTrue(ring.luminance()>scheme.surface.luminance()+.15f)
            assertTrue(links.luminance()>scheme.surface.luminance()+.1f)
            assertEquals(1f,ring.alpha,0f)
            assertEquals(1f,links.alpha,0f)
        }
    }
    @Test fun lightThemeRetainsVisibleGeometry() {
        val scheme=lightColorScheme(primary=Color(0xFFBD2738))
        val (ring,links)=jukeboxGraphColors(scheme)
        assertTrue(ring.luminance()<scheme.surface.luminance()-.2f)
        assertTrue(links.luminance()<scheme.surface.luminance()-.2f)
    }
}
