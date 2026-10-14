package br.com.onda.mobile

import androidx.compose.material3.ColorScheme
import androidx.compose.ui.graphics.Color

internal fun pureBlackSurfaces(base:ColorScheme,separators:Boolean):ColorScheme {
    if(separators)return base
    return base.copy(
        background=Color.Black,surface=Color.Black,surfaceTint=Color.Transparent,
        surfaceDim=Color.Black,surfaceBright=Color.Black,
        surfaceContainerLowest=Color.Black,surfaceContainerLow=Color.Black,surfaceContainer=Color.Black,
        surfaceContainerHigh=Color.Black,surfaceContainerHighest=Color.Black,surfaceVariant=Color.Black,
        outline=Color.Black,outlineVariant=Color.Black,
        primaryContainer=Color.Black,secondaryContainer=Color.Black,tertiaryContainer=Color.Black,
        errorContainer=Color.Black,onErrorContainer=base.onSurface,inverseSurface=Color.Black,inverseOnSurface=base.onSurface,
        onPrimaryContainer=base.onSurface,onSecondaryContainer=base.onSurface,onTertiaryContainer=base.onSurface
    )
}

// Dialogs remain black even when borders and separators are enabled.
@androidx.compose.runtime.Composable
internal fun ondaDialogContainerColor():Color =
    if(androidx.compose.material3.MaterialTheme.colorScheme.background==Color.Black) Color.Black
    else androidx.compose.material3.AlertDialogDefaults.containerColor
