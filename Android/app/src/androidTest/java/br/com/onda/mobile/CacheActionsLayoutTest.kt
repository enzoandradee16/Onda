package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CacheActionsLayoutTest {
    @get:Rule val compose=createComposeRule()
    @Test fun refreshIsOnTheLeftAndClearIsOnTheSameRow() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val vm=OndaViewModel(androidx.test.core.app.ApplicationProvider.getApplicationContext())
        compose.setContent {LocalizedTheme("pt-BR",lightColorScheme(),Typography()) {
            Column(Modifier.width(320.dp).height(600.dp).verticalScroll(rememberScrollState())){CacheControls(vm)}
        }}
        compose.onNodeWithText("Atualizar tamanho").performScrollTo()
        val left=compose.onNodeWithText("Atualizar tamanho").fetchSemanticsNode().boundsInRoot
        val right=compose.onNodeWithText("Limpar arquivos dispensáveis").fetchSemanticsNode().boundsInRoot
        assertTrue(left.right<=right.left)
        assertTrue(kotlin.math.abs(left.center.y-right.center.y)<2f)
        compose.onNodeWithText("Limpar arquivos dispensáveis").assertIsDisplayed()
    }
}
