package br.com.onda.mobile

import androidx.compose.ui.graphics.Color
import org.junit.Assert.*
import org.junit.Test

class CustomAccentTest {
    @Test fun customColorParsingRejectsIncompleteAndTransparentValues() {
        assertEquals("#7C4DFF", normalizeAccent("  7c4dff "))
        for(value in listOf("#123", "#12345678", "##123456", "#GG0000", "")) assertNull(normalizeAccent(value))
    }

    @Test fun arbitraryColorsKeepReadableButtonsAndSurfaceContrast() {
        for(dark in listOf(false,true))for(raw in listOf("#000000","#FFFFFF","#FFFF00","#00FF00","#FF0000","#0000FF","#7C4DFF","#222A35","#E7EDF4")) {
            val color=resolvedAccent(raw,dark)
            val surface=if(dark)Color(0xFF2B3744) else Color(0xFFE7EDF4)
            assertTrue("$raw / dark=$dark",accentContrast(color,surface)>=4.5f)
            assertTrue(accentContrast(color,accentInk(color))>=4.5f)
            assertTrue(closestAccent(raw,dark) in accents.keys)
        }
    }

    @Test fun predefinedColorsKeepTheirExistingValues() {
        for((name,argb) in accents)assertEquals(Color(argb),resolvedAccent(name,true))
        for((name,argb) in lightAccents)assertEquals(Color(argb),resolvedAccent(name,false))
    }

    @Test fun colorPlaneConversionPreservesHueSaturationAndBrightness() {
        for(color in listOf(Color.Red,Color.Green,Color.Blue,Color.White,Color.Black,Color(0xFF7C4DFF))) {
            val hsv=accentHsv(color)
            assertEquals(color.hexRgb(),Color.hsv(hsv[0],hsv[1],hsv[2]).hexRgb())
        }
    }
}
