package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class LayoutSpacingTest {
    @Test fun defaultsAndInvalidModesKeepCurrentLayout() {
        assertEquals("Padrão",normalizedSpacing("unknown"))
        assertEquals(spacingValues("Padrão"),spacingValues("unknown"))
        assertEquals(8f,spacingValues("Padrão").controls.value)
        assertEquals(4f,spacingValues("Padrão").checkboxLabel.value)
    }
    @Test fun densityChangesGapsIndependentlyOfTextAndTouchSizes() {
        val compact=spacingValues("Compacto");val normal=spacingValues("Padrão");val comfortable=spacingValues("Confortável")
        assertTrue(compact.controls<normal.controls)
        assertTrue(normal.controls<comfortable.controls)
        assertTrue(compact.checkboxLabel.value>0)
        assertTrue(normal.checkboxLabel<comfortable.checkboxLabel)
    }
}
