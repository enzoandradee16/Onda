package br.com.onda.mobile

import android.os.Build
import android.view.Window
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.core.view.WindowCompat

@Suppress("DEPRECATION")
internal fun applyNavigationBarTheme(window:Window,background:Color,dark:Boolean) {
    val color=background.toArgb()
    // The window background also covers transparent system bars on newer Android.
    window.setBackgroundDrawable(android.graphics.drawable.ColorDrawable(color))
    window.navigationBarColor=color
    if(Build.VERSION.SDK_INT>=28)window.navigationBarDividerColor=color
    if(Build.VERSION.SDK_INT>=29)window.isNavigationBarContrastEnforced=false
    WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightNavigationBars=!dark
}
