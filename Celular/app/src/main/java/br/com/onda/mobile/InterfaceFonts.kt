package br.com.onda.mobile

import android.graphics.Typeface
import androidx.compose.material3.Typography
import androidx.compose.ui.text.font.FontFamily

const val DEFAULT_INTERFACE_FONT="Padrão do sistema"
const val FONT_PREVIEW="Onda · Sua música, do seu jeito. Aa Bb 123"
val interfaceFonts=linkedMapOf(
    DEFAULT_INTERFACE_FONT to FontFamily.Default,
    "Sem serifa" to FontFamily.SansSerif,
    "Serifada" to FontFamily.Serif,
    "Monoespaçada" to FontFamily.Monospace,
    "Condensada" to FontFamily(Typeface.create("sans-serif-condensed",Typeface.NORMAL)),
    "Cursiva" to FontFamily(Typeface.create("cursive",Typeface.NORMAL)),
    "Arredondada" to FontFamily(Typeface.create("casual",Typeface.NORMAL)))

fun interfaceTypography(name:String):Typography {
    val family=interfaceFonts[name] ?: FontFamily.Default
    val base=Typography()
    return base.copy(
        displayLarge=base.displayLarge.copy(fontFamily=family),displayMedium=base.displayMedium.copy(fontFamily=family),displaySmall=base.displaySmall.copy(fontFamily=family),
        headlineLarge=base.headlineLarge.copy(fontFamily=family),headlineMedium=base.headlineMedium.copy(fontFamily=family),headlineSmall=base.headlineSmall.copy(fontFamily=family),
        titleLarge=base.titleLarge.copy(fontFamily=family),titleMedium=base.titleMedium.copy(fontFamily=family),titleSmall=base.titleSmall.copy(fontFamily=family),
        bodyLarge=base.bodyLarge.copy(fontFamily=family),bodyMedium=base.bodyMedium.copy(fontFamily=family),bodySmall=base.bodySmall.copy(fontFamily=family),
        labelLarge=base.labelLarge.copy(fontFamily=family),labelMedium=base.labelMedium.copy(fontFamily=family),labelSmall=base.labelSmall.copy(fontFamily=family))
}
