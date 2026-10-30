package br.com.onda.mobile

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.toArgb
import kotlin.math.roundToInt

internal const val CUSTOM_ACCENT = "Cor personalizada"

internal fun normalizeAccent(value: String): String? {
    val raw = value.trim()
    return if (Regex("#?[0-9a-fA-F]{6}").matches(raw)) "#" + raw.removePrefix("#").uppercase() else null
}

internal fun Color.hexRgb(): String = "#%06X".format(toArgb() and 0xFFFFFF)
internal fun accentContrast(a: Color, b: Color): Float =
    (maxOf(a.luminance(), b.luminance()) + .05f) / (minOf(a.luminance(), b.luminance()) + .05f)

internal fun readableCustomAccent(raw: String, dark: Boolean): Color {
    var color = Color(0xFF000000 or normalizeAccent(raw)!!.removePrefix("#").toLong(16))
    val surface = if (dark) Color(0xFF2B3744) else Color(0xFFE7EDF4)
    val target = if (dark) 255 else 0
    repeat(64) {
        if (accentContrast(color, surface) >= 4.5f) return color
        val argb = color.toArgb()
        fun channel(shift: Int) = (((argb shr shift) and 255) * .94f + target * .06f).roundToInt()
        color = Color(channel(16), channel(8), channel(0))
    }
    return color
}

internal fun resolvedAccent(value: String, dark: Boolean): Color =
    if (normalizeAccent(value) != null) readableCustomAccent(value, dark)
    else Color((if (dark) accents else lightAccents)[value] ?: (if (dark) accents else lightAccents).getValue("Verde-Água"))

internal fun accentInk(color: Color): Color =
    if (accentContrast(color, Color(0xFF101419)) >= accentContrast(color, Color.White)) Color(0xFF101419) else Color.White

internal fun closestAccent(value: String, dark: Boolean): String {
    if (normalizeAccent(value) == null) return value
    val color = resolvedAccent(value, dark)
    return (if (dark) accents else lightAccents).minBy { (_, argb) ->
        val other = Color(argb)
        (color.red-other.red)*(color.red-other.red) + (color.green-other.green)*(color.green-other.green) + (color.blue-other.blue)*(color.blue-other.blue)
    }.key
}

internal fun accentHsv(color: Color): FloatArray {
    val r=color.red; val g=color.green; val b=color.blue
    val top=maxOf(r,g,b); val low=minOf(r,g,b); val span=top-low
    val hue=when {
        span==0f -> 0f
        top==r -> 60f*((g-b)/span).let {if(it<0)it+6 else it}
        top==g -> 60f*((b-r)/span+2)
        else -> 60f*((r-g)/span+4)
    }
    return floatArrayOf(hue,if(top==0f)0f else span/top,top)
}
