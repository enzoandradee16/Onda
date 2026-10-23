package br.com.onda.mobile

import androidx.compose.runtime.*
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

internal val spacingModes=listOf("Compacto","Padrão","Confortável")
internal fun normalizedSpacing(value:String)=value.takeIf {it in spacingModes} ?: "Padrão"
internal data class SpacingValues(val text:Dp,val details:Dp,val controls:Dp,val section:Dp,val checkboxLabel:Dp,val inset:Dp)
internal fun spacingValues(value:String)=when(normalizedSpacing(value)) {
    "Compacto"->SpacingValues(1.dp,3.dp,6.dp,10.dp,3.dp,14.dp)
    "Confortável"->SpacingValues(4.dp,6.dp,12.dp,16.dp,6.dp,20.dp)
    else->SpacingValues(2.dp,4.dp,8.dp,12.dp,4.dp,16.dp)
}
internal val LocalLayoutSpacing=staticCompositionLocalOf {spacingValues("Padrão")}

/** Space changes independently of typography and Material's minimum touch targets. */
internal object LayoutSpacing {
    val text:Dp @Composable get()=LocalLayoutSpacing.current.text
    val details:Dp @Composable get()=LocalLayoutSpacing.current.details
    val controls:Dp @Composable get()=LocalLayoutSpacing.current.controls
    val section:Dp @Composable get()=LocalLayoutSpacing.current.section
    val checkboxLabel:Dp @Composable get()=LocalLayoutSpacing.current.checkboxLabel
    val inset:Dp @Composable get()=LocalLayoutSpacing.current.inset
}
