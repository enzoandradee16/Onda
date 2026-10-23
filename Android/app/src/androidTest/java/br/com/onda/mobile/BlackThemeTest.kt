package br.com.onda.mobile

import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.graphics.Color
import org.junit.Assert.*
import org.junit.Test

class BlackThemeTest {
    @Test fun flatThemeMakesCardsDialogsFieldsAndDividersBlackAndCanBeReversed() {
        val base=darkColorScheme(primary=Color.Green)
        val flat=pureBlackSurfaces(base,false)
        for(color in listOf(flat.background,flat.surface,flat.surfaceDim,flat.surfaceBright,
            flat.surfaceVariant,flat.surfaceContainerLowest,flat.surfaceContainerLow,flat.surfaceContainer,
            flat.surfaceContainerHigh,flat.surfaceContainerHighest,flat.outline,flat.outlineVariant,
            flat.primaryContainer,flat.secondaryContainer,flat.tertiaryContainer)) assertEquals(Color.Black,color)
        assertEquals(base.primary,flat.primary)
        assertEquals(base,pureBlackSurfaces(base,true))
    }
}
