package br.com.onda.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.runtime.*
import kotlin.math.abs
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
@Composable
internal fun RoundSlider(
    value: Float,
    onValueChange: (Float) -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    valueRange: ClosedFloatingPointRange<Float> = 0f..1f,
    onValueChangeFinished: (() -> Unit)? = null,
    slim: Boolean = false,
    bufferedRange: ClosedFloatingPointRange<Float>? = null,
    markedRange: ClosedFloatingPointRange<Float>? = null,
    markedPoints: List<Double> = emptyList(),
    onMarkedPointMoved: ((Int, Double) -> Unit)? = null,
) {
    val colors = MaterialTheme.colorScheme
    val movePoint by rememberUpdatedState(onMarkedPointMoved)
    var markerPreview by remember { mutableStateOf<Pair<Int, Double>?>(null) }
    val markerInput = if (onMarkedPointMoved == null || markedPoints.none { it >= valueRange.start }) Modifier else
        Modifier.pointerInput(markedPoints, valueRange) {
            awaitEachGesture {
                val down = awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
                if (size.width <= 0) return@awaitEachGesture
                val span = (valueRange.endInclusive - valueRange.start).coerceAtLeast(.001f)
                fun pixel(point: Double) = size.width * (point - valueRange.start) / span
                val index = markedPoints.indices.filter { markedPoints[it] >= valueRange.start }
                    .minByOrNull { abs(down.position.x - pixel(markedPoints[it])) } ?: return@awaitEachGesture
                val offset = pixel(markedPoints[index]) - down.position.x
                if (abs(offset) > 12.dp.toPx()) return@awaitEachGesture
                down.consume()
                var moved = false
                try {
                    while (true) {
                        val event = awaitPointerEvent(PointerEventPass.Initial)
                        val change = event.changes.firstOrNull { it.id == down.id } ?: break
                        change.consume()
                        val raw = valueRange.start + ((change.position.x + offset) / size.width).coerceIn(0.0, 1.0) * span
                        val lower = if (index == 1) markedPoints[0].coerceAtLeast(valueRange.start.toDouble()) + .1 else valueRange.start.toDouble()
                        val end = markedPoints.getOrNull(1)?.takeIf { it >= 0 }
                        val upper = if (index == 0 && end != null) end - .1 else valueRange.endInclusive.toDouble()
                        val seconds = if (lower <= upper) raw.coerceIn(lower, upper) else markedPoints[index]
                        if (!change.pressed) {
                            if (moved) movePoint?.invoke(index, seconds)
                            break
                        }
                        if (abs(change.position.x - down.position.x) >= viewConfiguration.touchSlop) moved = true
                        if (moved) markerPreview = index to seconds
                    }
                } finally {
                    markerPreview = null
                }
            }
        }
    androidx.compose.material3.Slider(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier.pageSwipeExclusion(),
        enabled = enabled,
        valueRange = valueRange,
        onValueChangeFinished = onValueChangeFinished,
        track = { state ->
            if (slim) Canvas(Modifier.fillMaxWidth().height(if (onMarkedPointMoved == null) 5.dp else 24.dp).then(markerInput)) {
                val band = 5.dp.toPx()
                val fraction = ((state.value - valueRange.start) / (valueRange.endInclusive - valueRange.start)).coerceIn(
                    0f,
                    1f
                )
                val start = androidx.compose.ui.geometry.Offset(0f, center.y)
                drawLine(
                    colors.onSurface.copy(alpha = .2f),
                    start,
                    androidx.compose.ui.geometry.Offset(size.width, center.y),
                    band,
                    androidx.compose.ui.graphics.StrokeCap.Round
                )
                bufferedRange?.let { range ->
                    val span = (valueRange.endInclusive - valueRange.start).coerceAtLeast(.001f)
                    val a = ((range.start - valueRange.start) / span).coerceIn(0f, 1f)
                    val b = ((range.endInclusive - valueRange.start) / span).coerceIn(a, 1f)
                    drawLine(
                        colors.primary.copy(alpha = .35f),
                        androidx.compose.ui.geometry.Offset(size.width * a, center.y),
                        androidx.compose.ui.geometry.Offset(size.width * b, center.y),
                        band,
                        androidx.compose.ui.graphics.StrokeCap.Round
                    )
                }
                drawLine(
                    if (enabled) colors.primary else colors.onSurface.copy(alpha = .38f),
                    start,
                    androidx.compose.ui.geometry.Offset(size.width * fraction, center.y),
                    band,
                    androidx.compose.ui.graphics.StrokeCap.Round
                )
                markedRange?.let { range ->
                    val span = (valueRange.endInclusive - valueRange.start).coerceAtLeast(.001f)
                    val start = markerPreview?.takeIf { it.first == 0 }?.second?.toFloat() ?: range.start
                    val end = markerPreview?.takeIf { it.first == 1 }?.second?.toFloat() ?: range.endInclusive
                    val a = ((start - valueRange.start) / span).coerceIn(0f, 1f)
                    val b = ((end - valueRange.start) / span).coerceIn(a, 1f)
                    drawRect(
                        color = colors.primary,
                        topLeft = androidx.compose.ui.geometry.Offset(size.width * a, center.y - band / 2),
                        size = androidx.compose.ui.geometry.Size(size.width * (b - a), band),
                        style = Stroke(1.dp.toPx())
                    )
                }
                markedPoints.forEachIndexed { index, point ->
                    if (point >= valueRange.start) {
                        val tick = 1.5.dp.toPx()
                        val arm = 6.dp.toPx()
                        val span = (valueRange.endInclusive - valueRange.start).coerceAtLeast(.001f)
                        val displayed = markerPreview?.takeIf { it.first == index }?.second ?: point
                        val markerFraction = ((displayed.toFloat() - valueRange.start) / span).coerceIn(0f, 1f)
                        val x = (size.width * markerFraction).coerceIn(tick / 2, (size.width - tick / 2).coerceAtLeast(tick / 2))
                        val tip = (x + if (index == 0) arm else -arm).coerceIn(0f, size.width)
                        val top = center.y - 9.dp.toPx()
                        val bottom = center.y + 9.dp.toPx()
                        drawLine(colors.primary, androidx.compose.ui.geometry.Offset(x, top), androidx.compose.ui.geometry.Offset(x, bottom), tick)
                        for (y in listOf(top, bottom)) {
                            drawLine(colors.primary, androidx.compose.ui.geometry.Offset(x, y), androidx.compose.ui.geometry.Offset(tip, y), tick)
                        }
                    }
                }
            } else SliderDefaults.Track(sliderState = state, enabled = enabled, thumbTrackGapSize = 0.dp)
        },
        thumb = {
            Canvas(Modifier.size(24.dp)) {
                drawCircle(colors.surface, radius = 11.dp.toPx())
                drawCircle(if (enabled) colors.primary else colors.onSurface.copy(alpha = .38f), radius = 10.dp.toPx())
                drawCircle(
                    colors.onSurface.copy(alpha = if (enabled) .45f else .2f),
                    radius = 10.dp.toPx(),
                    style = Stroke(1.dp.toPx())
                )
            }
        },
    )
}
