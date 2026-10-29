package br.com.onda.mobile

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.ui.layout.onSizeChanged
import java.util.WeakHashMap
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.gestures.scrollBy
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import kotlinx.coroutines.*
import kotlin.math.abs

private class QueueDragPreview {
    var from by mutableIntStateOf(-1)
    var target by mutableIntStateOf(-1)
    var distance by mutableFloatStateOf(0f)
    fun displacement(index:Int):Float=when {
        from<0||target<0->0f
        from<target&&index>from&&index<=target->-distance
        from>target&&index>=target&&index<from->distance
        else->0f
    }
    fun clear(){from=-1;target=-1;distance=0f}
}
private val queueDragPreviews=WeakHashMap<LazyListState,QueueDragPreview>()

@Composable internal fun DraggableQueueCard(state:LazyListState,index:Int,count:Int,enabled:Boolean=true,move:(Int,Int)->Unit,content:@Composable BoxScope.()->Unit) {
    val moveAction by rememberUpdatedState(move)
    val latestIndex by rememberUpdatedState(index)
    val latestCount by rememberUpdatedState(count)
    val scope=rememberCoroutineScope()
    var offset by remember {mutableFloatStateOf(0f)}
    var start by remember {mutableFloatStateOf(0f)}
    var dragging by remember {mutableStateOf(false)}
    val preview=remember(state){queueDragPreviews.getOrPut(state){QueueDragPreview()}}
    var cardHeight by remember {mutableIntStateOf(0)}
    val shifted by animateFloatAsState(if(dragging)0f else preview.displacement(index),tween(140),label="queue-gap")
    val color=if(dragging)MaterialTheme.colorScheme.surface else Color.Transparent
    Box(Modifier.fillMaxWidth().onSizeChanged {cardHeight=it.height}.zIndex(if(dragging)10f else 0f).graphicsLayer {translationY=if(dragging)offset else if(preview.from>=0)shifted else 0f;shadowElevation=if(dragging)6.dp.toPx() else 0f}.background(color).pointerInput(state,enabled) {
        var scrolling:Job?=null
        fun updateTarget(){
            val target=state.layoutInfo.visibleItemsInfo.minByOrNull {abs(it.offset+it.size/2f-(start+offset))}?.index
            if(target!=null && target in 0 until latestCount)preview.target=target
        }
        try {
            if(enabled)detectDragGesturesAfterLongPress(
                onDragStart={
                    offset=0f;dragging=true;preview.from=latestIndex;preview.target=latestIndex;preview.distance=cardHeight.toFloat()+state.layoutInfo.mainAxisItemSpacing
                    start=state.layoutInfo.visibleItemsInfo.firstOrNull {it.index==latestIndex}?.let {it.offset+it.size/2f} ?: 0f
                    scrolling=scope.launch {
                        while(isActive) {
                            val viewport=state.layoutInfo;val y=start+offset
                            val scroll=when {y<viewport.viewportStartOffset+60->-18f;y>viewport.viewportEndOffset-60->18f;else->0f}
                            if(scroll!=0f){val consumed=state.scrollBy(scroll);start-=consumed;offset+=consumed;updateTarget()}
                            delay(40)
                        }
                    }
                },
                onDragCancel={scrolling?.cancel();offset=0f;dragging=false;preview.clear()},
                onDragEnd={
                    scrolling?.cancel()
                    val target=state.layoutInfo.visibleItemsInfo.minByOrNull {abs(it.offset+it.size/2f-(start+offset))}?.index
                    offset=0f;dragging=false;preview.clear()
                    if(target!=null && target in 0 until latestCount && target!=latestIndex)moveAction(latestIndex,target)
                },
                onDrag={change,amount->change.consume();offset+=amount.y;updateTarget()}
            )
        } finally {scrolling?.cancel();if(preview.from==latestIndex)preview.clear();offset=0f;dragging=false}
    },content=content)
}

@Composable internal fun QueueDragHandle(state:LazyListState,index:Int,count:Int,enabled:Boolean=true,itemLabel:String="",modifier:Modifier=Modifier,icon:String="drag",move:(Int,Int)->Unit) {
    val label=translateUi("Arrastar para reorganizar")
    val up=translateUi("Mover para cima");val down=translateUi("Mover para baixo")
    Box(modifier.size(24.dp).semantics {
        role=Role.Button
        if(!enabled)disabled()
        contentDescription=if(itemLabel.isBlank())label else "$label: $itemLabel"
        customActions=listOf(CustomAccessibilityAction(up){if(index>0){move(index,index-1);true}else false},CustomAccessibilityAction(down){if(index+1<count){move(index,index+1);true}else false})
    },contentAlignment=androidx.compose.ui.Alignment.Center) {OndaIcon(icon,modifier=Modifier.size(16.dp),tint=if(enabled)MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha=.38f))}
}
