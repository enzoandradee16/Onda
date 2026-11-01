package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class PlaybackContinuityTest {
    @get:Rule val compose = createComposeRule()

    @Test fun nativePreparationKeepsOriginalAndDisablingRestoresExactPcm() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val report = JSONObject(Python.getInstance().getModule("playback_continuity_smoke").callAttr("verify").toString())
        assertTrue(report.getBoolean("pending_keeps_original"))
        assertTrue(report.getBoolean("disabled_is_bit_exact"))
        assertTrue(report.getBoolean("neutral_is_bit_exact"))
    }

    @Test fun sliderChangesReadoutDuringDragAndCommitsOnlyOnRelease() {
        var commits = 0
        var selected = 85f
        compose.setContent {
            MaterialTheme {
                PlaybackAdjustment("Velocidade · 85%",85f,50f..150f,"continuity-speed") {
                    commits++
                    selected = it
                }
            }
        }
        val slider = compose.onNodeWithTag("continuity-speed")
        slider.performTouchInput {down(center);moveTo(androidx.compose.ui.geometry.Offset(width*.8f,centerY),200)}
        compose.runOnIdle {assertEquals(0,commits)}
        slider.assert(SemanticsMatcher("live draft") {node ->
            node.config[androidx.compose.ui.semantics.SemanticsProperties.ProgressBarRangeInfo].current != 85f
        })
        slider.performTouchInput {up()}
        compose.runOnIdle {assertEquals(1,commits);assertTrue(selected>100f)}
    }
}
