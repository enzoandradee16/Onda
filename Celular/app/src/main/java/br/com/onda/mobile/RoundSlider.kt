package br.com.onda.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.drawscope.Stroke

/** Keep native slider semantics, gestures and touch targets; customize only the thumb. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun RoundSlider(
    value:Float,
    onValueChange:(Float)->Unit,
    modifier:Modifier=Modifier,
    enabled:Boolean=true,
    valueRange:ClosedFloatingPointRange<Float> = 0f..1f,
    onValueChangeFinished:(()->Unit)?=null,
    slim:Boolean=false,
) {
    val colors=MaterialTheme.colorScheme
    androidx.compose.material3.Slider(
        value=value,onValueChange=onValueChange,modifier=modifier.pageSwipeExclusion(),enabled=enabled,
        valueRange=valueRange,onValueChangeFinished=onValueChangeFinished,
        track={state->
            if(slim)Canvas(Modifier.fillMaxWidth().height(5.dp)) {
                val fraction=((state.value-valueRange.start)/(valueRange.endInclusive-valueRange.start)).coerceIn(0f,1f)
                val start=androidx.compose.ui.geometry.Offset(0f,center.y)
                drawLine(colors.onSurface.copy(alpha=.2f),start,androidx.compose.ui.geometry.Offset(size.width,center.y),size.height,androidx.compose.ui.graphics.StrokeCap.Round)
                drawLine(if(enabled)colors.primary else colors.onSurface.copy(alpha=.38f),start,androidx.compose.ui.geometry.Offset(size.width*fraction,center.y),size.height,androidx.compose.ui.graphics.StrokeCap.Round)
            } else SliderDefaults.Track(sliderState=state,enabled=enabled,thumbTrackGapSize=0.dp)
        },
        thumb={Canvas(Modifier.size(24.dp)) {
            drawCircle(colors.surface,radius=11.dp.toPx())
            drawCircle(if(enabled) colors.primary else colors.onSurface.copy(alpha=.38f),radius=10.dp.toPx())
            drawCircle(colors.onSurface.copy(alpha=if(enabled).45f else .2f),radius=10.dp.toPx(),style=Stroke(1.dp.toPx()))
        }},
    )
}
