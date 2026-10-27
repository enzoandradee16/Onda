package br.com.onda.mobile

import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.ui.composed
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription

internal fun Modifier.gallerySwipe(previous:()->Unit,next:()->Unit):Modifier=composed {
    val previousAction=rememberUpdatedState(previous)
    val nextAction=rememberUpdatedState(next)
    val threshold=with(LocalDensity.current){48.dp.toPx()}
    pointerInput(Unit) {
        var distance=0f
        detectHorizontalDragGestures(
            onDragStart={distance=0f},
            onDragCancel={distance=0f},
            onDragEnd={
                if(distance < -threshold)nextAction.value()
                else if(distance > threshold)previousAction.value()
                distance=0f
            },
            onHorizontalDrag={change,amount->change.consume();distance+=amount}
        )
    }
}



@androidx.compose.runtime.Composable
internal fun androidx.compose.foundation.layout.BoxScope.GalleryArrows(index:Int,count:Int,previous:()->Unit,next:()->Unit) {
    val previousLabel=translateUi("Anterior");val nextLabel=translateUi("Próxima")
    if(count>1) {
        androidx.compose.material3.FilledTonalIconButton(onClick=previous,enabled=index>0,modifier=Modifier.align(androidx.compose.ui.Alignment.CenterStart)) {
            androidx.compose.material3.Text("‹",fontSize=32.sp,modifier=Modifier.semantics {contentDescription=previousLabel})
        }
        androidx.compose.material3.FilledTonalIconButton(onClick=next,enabled=index<count-1,modifier=Modifier.align(androidx.compose.ui.Alignment.CenterEnd)) {
            androidx.compose.material3.Text("›",fontSize=32.sp,modifier=Modifier.semantics {contentDescription=nextLabel})
        }
    }
}
