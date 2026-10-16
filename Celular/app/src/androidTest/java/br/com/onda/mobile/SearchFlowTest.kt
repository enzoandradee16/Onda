package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SearchFlowTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before() {
            if(android.os.Build.VERSION.SDK_INT>=33) {
                val instrumentation=androidx.test.platform.app.InstrumentationRegistry.getInstrumentation()
                instrumentation.uiAutomation.grantRuntimePermission(instrumentation.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()
    @Test fun filtersAreReachableWithoutStartingNetworkSearch() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
        compose.onNodeWithTag("open-menu").performClick()
        compose.onNodeWithTag("tab-Pesquisar").performClick()
        compose.onNodeWithText("Filtros").performClick()
        compose.onNodeWithText("Filtros da busca").assertIsDisplayed()
        compose.onNodeWithText("Ano ou intervalo").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Duração ou intervalo").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Voltar").performClick()
        compose.onNodeWithTag("music-query").assertIsDisplayed()
    }
}
