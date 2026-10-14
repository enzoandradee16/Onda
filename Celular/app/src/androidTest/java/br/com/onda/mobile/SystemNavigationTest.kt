package br.com.onda.mobile

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.core.view.WindowCompat
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class SystemNavigationTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    @Test fun navigationContrastAndIconsFollowDarkAndLightBackgrounds() {
        for(dark in listOf(true,false)) compose.runOnUiThread {
            val window=compose.activity.window
            val background=if(dark)Color.Black else Color.White
            applyNavigationBarTheme(window,background,dark)
            assertEquals(background.toArgb(),(window.decorView.background as? android.graphics.drawable.ColorDrawable)?.color ?: (window.peekDecorView().background as android.graphics.drawable.ColorDrawable).color)
            assertEquals(!dark,WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightNavigationBars)
            if(android.os.Build.VERSION.SDK_INT>=29)assertFalse(window.isNavigationBarContrastEnforced)
        }
    }
}
