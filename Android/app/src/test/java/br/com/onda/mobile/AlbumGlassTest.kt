package br.com.onda.mobile

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.graphics.luminance
import org.junit.Assert.*
import org.junit.Test

class AlbumGlassTest {
    @Test fun albumColorsDoNotChangeBetweenLightAndDarkThemes() {
        for(cover in listOf(Color.Red,Color.Blue,Color.Yellow,Color.White,Color.Black)) {
            assertEquals(albumGlassColors(cover,true,false),albumGlassColors(cover,false,false))
        }
    }
    private fun contrast(a:Color,b:Color):Float {
        val x=a.luminance();val y=b.luminance()
        return (maxOf(x,y)+.05f)/(minOf(x,y)+.05f)
    }
    @Test fun tintComesFromTheCoverAndIgnoresTransparentPixels() {
        assertNull(albumDominantColor(intArrayOf(0x00ff0000)))
        val blue=albumDominantColor(IntArray(100){if(it<80)0xff0044cc.toInt() else 0xffff0000.toInt()})!!
        assertTrue(blue.blue>blue.red)
        assertNotEquals(albumGlassColors(Color.Red,true,false).base,albumGlassColors(Color.Blue,true,false).base)
    }
    @Test fun textStaysLegibleAcrossAllThemesAndExtremeCoverColors() {
        val covers=listOf(Color.Black,Color.White,Color.Red,Color.Green,Color.Blue,Color.Yellow,Color.Cyan,Color.Magenta)
        for(dark in listOf(false,true))for(hc in listOf(false,true))for(cover in covers) {
            val glass=albumGlassColors(cover,dark,hc)
            for(image in listOf(Color.Black,Color.White))for(stop in listOf(glass.top,glass.base,glass.bottom)) {
                val under=image.copy(alpha=if(hc).02f else .10f).compositeOver(glass.base)
                val lens=stop.copy(alpha=.9f).compositeOver(under)
                val rendered=Color.White.copy(alpha=if(hc).01f else .045f).compositeOver(lens)
                assertTrue("Title: dark=$dark hc=$hc cover=$cover",contrast(glass.ink,rendered)>=if(hc)7f else 4.5f)
                assertTrue("Artist: dark=$dark hc=$hc cover=$cover",contrast(glass.secondary,rendered)>=if(hc)7f else 4.5f)
            }
        }
    }
    @Test fun lyricsUseCoverColorWithReadableText() {
        assertNotEquals(albumLyricsColors(Color.Blue,false).first,albumLyricsColors(Color.Red,false).first)
        for(hc in listOf(false,true))for(cover in listOf(Color.Black,Color.White,Color.Red,Color.Green,Color.Blue,Color.Yellow,Color.Cyan,Color.Magenta)) {
            val (background,ink)=albumLyricsColors(cover,hc)
            assertTrue(contrast(background,ink)>=if(hc)7f else 4.5f)
        }
    }
}
