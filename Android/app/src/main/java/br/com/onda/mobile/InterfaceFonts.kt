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

fun normalizeInterfaceFont(name:String):String = when(name) {
    "Padr\u00c3\u00a3o do sistema" -> DEFAULT_INTERFACE_FONT
    "Monoespa\u00c3\u00a7ada" -> "Monoespaçada"
    else -> name
}

val interfaceFontSizes=listOf("85%","100%","115%","130%")
fun interfaceTypography(name:String,size:String="100%"):Typography {
    val scale=if(size in interfaceFontSizes) size.removeSuffix("%").toFloat()/100f else 1f
    val family=interfaceFonts[normalizeInterfaceFont(name)] ?: FontFamily.Default
    val base=Typography()
    return base.copy(
        displayLarge=base.displayLarge.copy(fontFamily=family,fontSize=base.displayLarge.fontSize*scale,lineHeight=base.displayLarge.lineHeight*scale),displayMedium=base.displayMedium.copy(fontFamily=family,fontSize=base.displayMedium.fontSize*scale,lineHeight=base.displayMedium.lineHeight*scale),displaySmall=base.displaySmall.copy(fontFamily=family,fontSize=base.displaySmall.fontSize*scale,lineHeight=base.displaySmall.lineHeight*scale),
        headlineLarge=base.headlineLarge.copy(fontFamily=family,fontSize=base.headlineLarge.fontSize*scale,lineHeight=base.headlineLarge.lineHeight*scale),headlineMedium=base.headlineMedium.copy(fontFamily=family,fontSize=base.headlineMedium.fontSize*scale,lineHeight=base.headlineMedium.lineHeight*scale),headlineSmall=base.headlineSmall.copy(fontFamily=family,fontSize=base.headlineSmall.fontSize*scale,lineHeight=base.headlineSmall.lineHeight*scale),
        titleLarge=base.titleLarge.copy(fontFamily=family,fontSize=base.titleLarge.fontSize*scale,lineHeight=base.titleLarge.lineHeight*scale),titleMedium=base.titleMedium.copy(fontFamily=family,fontSize=base.titleMedium.fontSize*scale,lineHeight=base.titleMedium.lineHeight*scale),titleSmall=base.titleSmall.copy(fontFamily=family,fontSize=base.titleSmall.fontSize*scale,lineHeight=base.titleSmall.lineHeight*scale),
        bodyLarge=base.bodyLarge.copy(fontFamily=family,fontSize=base.bodyLarge.fontSize*scale,lineHeight=base.bodyLarge.lineHeight*scale),bodyMedium=base.bodyMedium.copy(fontFamily=family,fontSize=base.bodyMedium.fontSize*scale,lineHeight=base.bodyMedium.lineHeight*scale),bodySmall=base.bodySmall.copy(fontFamily=family,fontSize=base.bodySmall.fontSize*scale,lineHeight=base.bodySmall.lineHeight*scale),
        labelLarge=base.labelLarge.copy(fontFamily=family,fontSize=base.labelLarge.fontSize*scale,lineHeight=base.labelLarge.lineHeight*scale),labelMedium=base.labelMedium.copy(fontFamily=family,fontSize=base.labelMedium.fontSize*scale,lineHeight=base.labelMedium.lineHeight*scale),labelSmall=base.labelSmall.copy(fontFamily=family,fontSize=base.labelSmall.fontSize*scale,lineHeight=base.labelSmall.lineHeight*scale))
}
