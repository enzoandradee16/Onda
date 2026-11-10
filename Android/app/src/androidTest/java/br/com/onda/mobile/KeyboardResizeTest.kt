package br.com.onda.mobile

import android.graphics.Rect
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class KeyboardResizeTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()

    @Test fun searchAndPlaybackResizeWhenKeyboardOpens() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        fun height():Int {
            var height=0
            compose.runOnUiThread {val rect=Rect();compose.activity.window.decorView.getWindowVisibleDisplayFrame(rect);height=rect.height()}
            return height
        }
        fun checkKeyboard() {
            val before=height()
            compose.onAllNodes(hasSetTextAction()).onFirst().performClick()
            compose.waitUntil(5000){height()<before-100}
            assertTrue(height()<before)
            compose.onNodeWithTag("nav-Mais").assertDoesNotExist()
            instrumentation.sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK)
            compose.waitUntil(5000){height()>=before-10}
            compose.onNodeWithTag("nav-Mais").assertExists()
        }
        compose.waitForIdle()
        checkKeyboard()
        compose.onNodeWithText("Reprodução",useUnmergedTree=true).performClick()
        compose.waitForIdle()
        checkKeyboard()
    }
}
