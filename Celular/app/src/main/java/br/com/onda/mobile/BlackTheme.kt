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

// Explicit foreground/container pairs keep text, selection and outlines legible.
internal fun highContrastScheme():ColorScheme = androidx.compose.material3.darkColorScheme(
    primary=Color.Yellow,onPrimary=Color.Black,primaryContainer=Color(0xFF003366),onPrimaryContainer=Color.White,
    secondary=Color.Yellow,onSecondary=Color.Black,secondaryContainer=Color(0xFF003366),onSecondaryContainer=Color.White,
    tertiary=Color.Cyan,onTertiary=Color.Black,tertiaryContainer=Color(0xFF003366),onTertiaryContainer=Color.White,
    background=Color.Black,onBackground=Color.White,surface=Color.Black,onSurface=Color.White,
    surfaceVariant=Color(0xFF202020),onSurfaceVariant=Color.White,
    surfaceDim=Color.Black,surfaceBright=Color(0xFF202020),surfaceTint=Color.Transparent,
    surfaceContainerLowest=Color.Black,surfaceContainerLow=Color.Black,surfaceContainer=Color.Black,
    surfaceContainerHigh=Color(0xFF202020),surfaceContainerHighest=Color(0xFF202020),
    outline=Color.White,outlineVariant=Color.White,
    error=Color(0xFFFFB3B3),onError=Color.Black,errorContainer=Color(0xFF660000),onErrorContainer=Color.White,
    inverseSurface=Color.White,inverseOnSurface=Color.Black,inversePrimary=Color(0xFF003366)
)
