package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class NativeLicensesTest {
    @get:Rule(order=0) val permissions = object : org.junit.rules.ExternalResource() {
        override fun before() {
            if (android.os.Build.VERSION.SDK_INT >= 33) {
                val instrumentation = androidx.test.platform.app.InstrumentationRegistry.getInstrumentation()
                instrumentation.uiAutomation.grantRuntimePermission(instrumentation.targetContext.packageName,
                    android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
    @get:Rule(order=1) val compose = createAndroidComposeRule<MainActivity>()
    @Test fun licensesAreReadableByComponent() {
        compose.waitForIdle()
        if (compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())
            compose.onNodeWithText("Agora não").performClick()
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithText("Licenças e fontes").performScrollTo().performClick()
        compose.waitUntil(10000) {
            compose.onAllNodesWithText("ffmpeg-7.1.3 / LICENSE.md").fetchSemanticsNodes().isNotEmpty()
        }
        compose.onNodeWithText("ffmpeg-7.1.3 / LICENSE.md").performScrollTo().performClick()
        compose.onNodeWithTag("license-details").performScrollToNode(hasText("Most files in FFmpeg", substring=true))
        compose.onNodeWithText("Most files in FFmpeg", substring=true).assertIsDisplayed()
        compose.onNodeWithText("Voltar").performClick()
        compose.onNodeWithText("Abrir fontes").assertIsDisplayed()
        compose.onNodeWithText("Fechar").performClick()
    }
}
