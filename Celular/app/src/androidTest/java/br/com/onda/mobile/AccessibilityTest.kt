package br.com.onda.mobile

import android.graphics.Bitmap
import android.graphics.Color
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.atomic.AtomicReference

@RunWith(AndroidJUnit4::class)
class AccessibilityTest {
    @get:Rule val compose=createComposeRule()
    @Test fun controlsExposeLocalizedNamesRolesStatesAndActions() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val language=mutableStateOf("pt-BR")
        val checked=mutableStateOf(false)
        val speed=mutableFloatStateOf(85f)
        var chosen=""
        compose.setContent {LocalizedTheme(language.value,lightColorScheme(),Typography()) {
            Column {
                Button(onClick={}){AccessibleSymbol("☰","Abrir menu de navegação")}
                Select("Idioma","pt-BR",UI_LANGUAGES){chosen=it}
                Toggle("Normalizar volume",checked.value){checked.value=it}
                Slider(speed.floatValue,{speed.floatValue=it},valueRange=50f..150f,modifier=Modifier.a11yLabel("Velocidade da música","${speed.floatValue.toInt()}%"))
            }
        }}
        for(lang in listOf("pt-BR","es","en")) {
            compose.runOnIdle {language.value=lang;checked.value=false;speed.floatValue=85f}
            compose.onNodeWithContentDescription(translateUi("Abrir menu de navegação",lang,context)).assertHasClickAction().assert(SemanticsMatcher.expectValue(SemanticsProperties.Role,Role.Button))
            compose.onAllNodesWithText("☰",useUnmergedTree=true).assertCountEquals(0)
            val selector=compose.onNodeWithContentDescription(translateUi("Idioma",lang,context)+": Português (Brasil)")
            selector.assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription,translateUi("Recolhido",lang,context))).performClick()
            selector.assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription,translateUi("Expandido",lang,context)))
            compose.onNodeWithText("English").performClick()
            compose.runOnIdle {assertEquals("en",chosen)}
            compose.onNodeWithText(translateUi("Normalizar volume",lang,context)).assertIsOff().performClick().assertIsOn()
            val slider=compose.onNodeWithContentDescription(translateUi("Velocidade da música",lang,context))
            slider.assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription,"85%"))
            slider.performSemanticsAction(SemanticsActions.SetProgress){it(90f)}
            compose.runOnIdle {assertEquals(90f,speed.floatValue)}
        }
    }
    @Test fun cropCanMoveAndZoomThroughAccessibilityActions() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val source=File(context.cacheDir,"accessible-crop-source.png")
        val bitmap=Bitmap.createBitmap(800,400,Bitmap.Config.ARGB_8888).apply {eraseColor(Color.RED)}
        android.graphics.Canvas(bitmap).drawRect(400f,0f,800f,400f,android.graphics.Paint().apply {color=Color.BLUE})
        source.outputStream().use {bitmap.compress(Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()
        val original=source.readBytes();val result=AtomicReference<String?>(null)
        val language=mutableStateOf("pt-BR")
        try {
            compose.setContent {LocalizedTheme(language.value,lightColorScheme(),Typography()) {CoverCropper(source.absolutePath,{},{result.set(it)})}}
            try {compose.waitUntil(10000) {compose.onAllNodesWithContentDescription("Área de recorte da capa").fetchSemanticsNodes().isNotEmpty()}} catch(error:Throwable) {throw AssertionError(compose.onAllNodes(isRoot(),useUnmergedTree=true).onLast().printToString(),error)}
            fun scroll(y:Float) {compose.onNode(hasScrollAction()).performSemanticsAction(SemanticsActions.ScrollBy){it(0f,y)}}
            for(lang in listOf("pt-BR","es","en")) {
                compose.runOnIdle {language.value=lang}
                scroll(2000f)
                compose.onNodeWithText(translateUi("Redefinir",lang,context)).performClick()
                scroll(-2000f)
                val node=compose.onNodeWithContentDescription(translateUi("Área de recorte da capa",lang,context))
                val actions=node.fetchSemanticsNode().config[SemanticsActions.CustomActions]
                assertEquals(4,actions.size)
                val move=actions.first {it.label==translateUi("Mover capa para a direita",lang,context)}
                scroll(2000f)
                compose.onNodeWithContentDescription(translateUi("Zoom da capa",lang,context)).performSemanticsAction(SemanticsActions.SetProgress){it(2f)}
                compose.runOnIdle {assertTrue(move.action())}
            }
            compose.onNodeWithText(translateUi("Aplicar capa","en",context)).performScrollTo().performClick()
            compose.waitUntil(10000) {result.get()!=null}
            val output=loadCoverBitmap(result.get()!!)
            assertEquals(200,output.width);assertEquals(Color.RED,output.getPixel(100,100));output.recycle()
            assertArrayEquals(original,source.readBytes())
        } finally {source.delete();result.get()?.let {File(it).delete()}}
    }

}


@RunWith(AndroidJUnit4::class)
class AccessibilityPlatformTest {
    @get:Rule val compose=createComposeRule()
    @Test fun platformAccessibilityTreeContainsActionNames() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        OndaStore.initialize(instrumentation.targetContext)
        val checked=mutableStateOf(false)
        compose.setContent {LocalizedTheme("en",lightColorScheme(),Typography()) {
            Column {
                Button(onClick={}){AccessibleSymbol("×","Fechar aviso")}
                Toggle("Normalizar volume",checked.value){checked.value=it}
            }
        }}
        fun labels(node:android.view.accessibility.AccessibilityNodeInfo?):List<String> {
            if(node==null)return emptyList()
            return listOfNotNull(node.contentDescription?.toString(),node.text?.toString())+(0 until node.childCount).flatMap {labels(node.getChild(it))}
        }
        compose.waitUntil(10000) {labels(instrumentation.uiAutomation.rootInActiveWindow).any {it.contains("Dismiss notice")}}
        assertTrue(labels(instrumentation.uiAutomation.rootInActiveWindow).any {it.contains("Normalize volume")})
        compose.onNodeWithText("Normalize volume").performClick().assertIsOn()
    }

}
