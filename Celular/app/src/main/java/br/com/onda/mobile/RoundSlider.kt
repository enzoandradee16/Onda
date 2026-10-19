package br.com.onda.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** Keep native slider semantics, gestures and touch targets; customize only the thumb. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun RoundSlider(
    value:Float,
    onValueChange:(Float)->Unit,
    modifier:Modifier=Modifier,
    enabled:Boolean=true,
    valueRange:ClosedFloatingPointRange<Float> = 0f..1f,
    onValueChangeFinished:(()->Unit)?=null,
) {
    val colors=MaterialTheme.colorScheme
    androidx.compose.material3.Slider(
        value=value,onValueChange=onValueChange,modifier=modifier,enabled=enabled,
        valueRange=valueRange,onValueChangeFinished=onValueChangeFinished,
        thumb={Canvas(Modifier.size(24.dp)) {
            drawCircle(if(enabled) colors.primary else colors.onSurface.copy(alpha=.38f),radius=10.dp.toPx())
        }},
    )
}
