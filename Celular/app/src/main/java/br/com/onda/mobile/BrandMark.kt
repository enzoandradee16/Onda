package br.com.onda.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.res.stringResource

/** Geometry comes from the same generated resource as the native launcher icons. */
@Composable internal fun OndaBrandMark(modifier:Modifier=Modifier,tint:Color=MaterialTheme.colorScheme.primary) {
    val data=stringResource(R.string.onda_brand_path)
    val path=remember(data){PathParser().parsePathString(data).toPath()}
    Canvas(modifier) {
        withTransform({scale(size.width/100f,size.height/64f,pivot=Offset.Zero)}) {
            drawPath(path,tint,style=Stroke(4.5f,cap=StrokeCap.Round,join=StrokeJoin.Round))
        }
    }
}
