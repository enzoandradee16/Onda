package br.com.onda.mobile

import android.os.Build
import android.view.Window
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.core.view.WindowCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.compose.runtime.*
import androidx.activity.compose.LocalActivity

/** Legacy adjustResize windows can consume IME insets before Compose sees them. */
@Composable internal fun rememberKeyboardVisible():Boolean {
    val activity=LocalActivity.current ?: return false
    var visible by remember(activity){mutableStateOf(false)}
    DisposableEffect(activity) {
        val decor=activity.window.decorView
        val frame=android.graphics.Rect()
        val bounds=android.graphics.Rect()
        val threshold=100*activity.resources.displayMetrics.density
        val listener=android.view.ViewTreeObserver.OnGlobalLayoutListener {
            decor.getWindowVisibleDisplayFrame(frame)
            @Suppress("DEPRECATION")
            val height=if(Build.VERSION.SDK_INT>=30)activity.windowManager.currentWindowMetrics.bounds.height()
                else {activity.windowManager.defaultDisplay.getRectSize(bounds);bounds.height()}
            val insets=ViewCompat.getRootWindowInsets(decor)
            val bars=insets?.getInsets(WindowInsetsCompat.Type.systemBars())
            val covered=height-frame.height()-(bars?.top ?: 0)-(bars?.bottom ?: 0)
            visible=insets?.isVisible(WindowInsetsCompat.Type.ime())==true || covered>threshold
        }
        decor.viewTreeObserver.addOnGlobalLayoutListener(listener)
        listener.onGlobalLayout()
        onDispose {decor.viewTreeObserver.removeOnGlobalLayoutListener(listener)}
    }
    return visible
}

@Suppress("DEPRECATION")
internal fun applyNavigationBarTheme(window:Window,background:Color,dark:Boolean) {
    val color=background.toArgb()
    // The window background also covers transparent system bars on newer Android.
    window.setBackgroundDrawable(android.graphics.drawable.ColorDrawable(color))
    window.navigationBarColor=color
    if(Build.VERSION.SDK_INT>=28)window.navigationBarDividerColor=color
    if(Build.VERSION.SDK_INT>=29)window.isNavigationBarContrastEnforced=false
    WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightNavigationBars=!dark
    WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightStatusBars=!dark
}
