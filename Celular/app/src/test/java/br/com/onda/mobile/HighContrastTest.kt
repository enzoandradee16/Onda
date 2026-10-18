package br.com.onda.mobile

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import org.junit.Assert.*
import org.junit.Test

class HighContrastTest {
    private fun contrast(a:Color,b:Color):Float {
        val x=a.luminance();val y=b.luminance()
        return (maxOf(x,y)+0.05f)/(minOf(x,y)+0.05f)
    }
    @Test fun textSelectionAndOutlinesStayLegible() {
        val scheme=highContrastScheme()
        assertEquals(Color.Black,scheme.background)
        for(pair in listOf(scheme.onBackground to scheme.background,scheme.onSurface to scheme.surface,
            scheme.onSurfaceVariant to scheme.surfaceVariant,scheme.onPrimary to scheme.primary,
            scheme.onPrimaryContainer to scheme.primaryContainer,scheme.outline to scheme.surface))
            assertTrue(contrast(pair.first,pair.second)>=7f)
    }
}
