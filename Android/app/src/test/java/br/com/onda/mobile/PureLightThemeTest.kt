package br.com.onda.mobile

import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import org.junit.Assert.*
import org.junit.Test

class PureLightThemeTest {
    private fun contrast(a: Color, b: Color): Float =
        (maxOf(a.luminance(), b.luminance()) + .05f) / (minOf(a.luminance(), b.luminance()) + .05f)

    @Test fun pureLightRemovesSurfaceTintAndKeepsEveryAccentReadable() {
        assertEquals(accents.keys, lightAccents.keys)
        for (accent in lightAccents.values) {
            val scheme = pureLightSurfaces(lightColorScheme(primary = Color(accent)))
            val surfaces = listOf(scheme.background, scheme.surface, scheme.surfaceVariant, scheme.surfaceContainerLowest,
                scheme.surfaceContainerLow, scheme.surfaceContainer, scheme.surfaceContainerHigh, scheme.surfaceContainerHighest)
            assertTrue(surfaces.all { it == Color.White })
            assertEquals(Color.Transparent, scheme.surfaceTint)
            assertTrue(contrast(scheme.primary, scheme.onPrimary) >= 4.5f)
            assertTrue(contrast(scheme.onSurfaceVariant, scheme.surface) >= 4.5f)
        }
    }
}
