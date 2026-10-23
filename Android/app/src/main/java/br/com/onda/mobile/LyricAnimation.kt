package br.com.onda.mobile

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch

/** Same reveal as the PC: 30 ms preparation, then 180 ms back to the active verse. */
@Composable internal fun Modifier.lyricAnimation(lineKey:Any,style:String,emphasized:Boolean=true,muted:Boolean=false):Modifier {
    val opacity=remember {Animatable(if(muted).55f else 1f)}
    val scale=remember {Animatable(1f)}
    val shift=remember {Animatable(0f)}
    val distance=with(LocalDensity.current){10.dp.toPx()}
    LaunchedEffect(lineKey,style,emphasized,muted) {
        val target=if(muted).55f else 1f
        if(style=="Desativada") {
            opacity.snapTo(target);scale.snapTo(1f);shift.snapTo(0f)
            return@LaunchedEffect
        }
        scale.snapTo(1f);shift.snapTo(0f)
        if(emphasized) {
            opacity.snapTo(1f)
            coroutineScope {
                launch {opacity.animateTo(.3f,tween(30))}
                launch {scale.animateTo(if(style=="Zoom").96f else 1f,tween(30))}
                launch {shift.animateTo(if(style=="Deslizar")distance else 0f,tween(30))}
            }
            coroutineScope {
                launch {opacity.animateTo(1f,tween(180))}
                launch {scale.animateTo(1f,tween(180))}
                launch {shift.animateTo(0f,tween(180))}
            }
        } else opacity.animateTo(target,tween(180))
    }
    return graphicsLayer {alpha=opacity.value;scaleX=scale.value;scaleY=scale.value;translationY=shift.value}
}
