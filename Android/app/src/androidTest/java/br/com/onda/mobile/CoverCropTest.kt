package br.com.onda.mobile

import android.graphics.Bitmap
import android.graphics.Color
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.semantics.SemanticsActions
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
class CoverCropTest {
    @get:Rule val compose=createComposeRule()
    @Test fun cropClampsMovementAndPreservesOriginal() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val bitmap=Bitmap.createBitmap(1600,800,Bitmap.Config.ARGB_8888)
        bitmap.eraseColor(Color.RED)
        android.graphics.Canvas(bitmap).drawRect(800f,0f,1600f,800f,android.graphics.Paint().apply {color=Color.BLUE})
        val output=File(context.cacheDir,"crop-test.png")
        try {
            saveCoverCrop(bitmap,2f,Offset(-100000f,100000f),output)
            val cropped=loadCoverBitmap(output.absolutePath)
            assertEquals(400,cropped.width);assertEquals(400,cropped.height)
            assertEquals(Color.BLUE,cropped.getPixel(200,200))
            assertEquals(Color.RED,bitmap.getPixel(0,0));assertEquals(1600,bitmap.width)
            cropped.recycle()
        } finally {bitmap.recycle();output.delete()}
    }
    @Test fun cropDialogAppliesZoomAndResetBeforeConfirming() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val source=File(context.cacheDir,"crop-dialog-source.png")
        val bitmap=Bitmap.createBitmap(800,400,Bitmap.Config.ARGB_8888).apply {eraseColor(Color.GREEN)}
        source.outputStream().use {bitmap.compress(Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()
        val original=source.readBytes();val result=AtomicReference<String?>(null)
        try {
            compose.setContent {MaterialTheme {CoverCropper(source.absolutePath,onCancel={fail("Unexpected cancellation")},onApply={result.set(it)})}}
            compose.waitUntil(10000) {compose.onAllNodes(hasText("Aplicar capa") and isEnabled()).fetchSemanticsNodes().isNotEmpty()}
            compose.onNode(SemanticsMatcher.keyIsDefined(androidx.compose.ui.semantics.SemanticsProperties.ProgressBarRangeInfo)).performSemanticsAction(SemanticsActions.SetProgress) {it(3f)}
            compose.onNodeWithText("Redefinir").performScrollTo().performClick()
            compose.onNode(SemanticsMatcher.keyIsDefined(androidx.compose.ui.semantics.SemanticsProperties.ProgressBarRangeInfo)).assertRangeInfoEquals(androidx.compose.ui.semantics.ProgressBarRangeInfo(1f,1f..4f))
            compose.onNode(SemanticsMatcher.keyIsDefined(androidx.compose.ui.semantics.SemanticsProperties.ProgressBarRangeInfo)).performSemanticsAction(SemanticsActions.SetProgress) {it(2f)}
            compose.onNodeWithText("Aplicar capa").performScrollTo().performClick()
            compose.waitUntil(10000) {result.get()!=null}
            val cropped=loadCoverBitmap(result.get()!!)
            assertEquals(200,cropped.width);assertEquals(200,cropped.height);cropped.recycle()
            assertArrayEquals(original,source.readBytes())
        } finally {source.delete();result.get()?.let {File(it).delete()}}
    }
}
