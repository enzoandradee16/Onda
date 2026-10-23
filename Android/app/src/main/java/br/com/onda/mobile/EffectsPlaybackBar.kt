package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlin.math.max

/** Coordinates are always source seconds, even when the rendered audio changes speed. */
internal object EffectsTimeline {
    fun position(anchor:Double, outputMillis:Long, speed:Int, duration:Double):Double =
        (anchor + max(0L,outputMillis)/1000.0*speed/100.0).coerceIn(0.0,max(0.0,duration))
    fun remaining(position:Double,duration:Double,speed:Int):Double =
        max(0.0,duration-position)/(speed.coerceIn(50,150)/100.0)
}

@Composable internal fun EffectsPlaybackBar(
    position:Double,duration:Double,playing:Boolean,preparing:Boolean,enabled:Boolean,
    hasNext:Boolean,onPrevious:()->Unit,
    onToggle:()->Unit,onNext:()->Unit,onSeek:(Double)->Unit,onQueue:()->Unit,onStop:()->Unit,
    lyrics:@Composable ()->Unit,
) {
    var dragged by remember {mutableStateOf<Float?>(null)}
    var menu by remember {mutableStateOf(false)}
    Surface(Modifier.fillMaxWidth().testTag("effects-playback-bar"),tonalElevation=3.dp) {
        Column(Modifier.padding(horizontal=LayoutSpacing.inset,vertical=LayoutSpacing.details)) {
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceEvenly) {
                lyrics()
                IconButton(onClick=onPrevious,enabled=enabled,modifier=Modifier.testTag("effects-previous")){OndaIcon("previous","Retroceder",Modifier.size(25.dp))}
                FilledIconButton(onClick=onToggle,enabled=enabled,modifier=Modifier.size(56.dp).testTag("effects-play-pause").a11yLabel(if(preparing)"Cancelar" else if(playing)"Pausar" else "Reproduzir"),shape=RoundedCornerShape(50)) {
                    if(preparing)CircularProgressIndicator(Modifier.size(25.dp),strokeWidth=2.dp,color=MaterialTheme.colorScheme.onPrimary)
                    else OndaIcon(if(playing)"pause" else "play",if(playing)"Pausar" else "Reproduzir",Modifier.size(28.dp))
                }
                IconButton(onClick=onNext,enabled=enabled&&hasNext,modifier=Modifier.testTag("effects-next")){OndaIcon("next","Avançar",Modifier.size(25.dp))}
                IconButton(onClick=onQueue,modifier=Modifier.testTag("effects-queue")){OndaIcon("queue","Fila",Modifier.size(25.dp))}
                Box {
                    IconButton(onClick={menu=true}){OndaIcon("more","Mais",Modifier.size(25.dp))}
                    DropdownMenu(menu,{menu=false}) {DropdownMenuItem(text={UiText("Parar")},enabled=enabled,onClick={menu=false;onStop()})}
                }
            }
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                UiText(mediaClock((dragged?.toDouble() ?: position).toLong()),style=MaterialTheme.typography.labelSmall)
                RoundSlider(dragged ?: position.toFloat().coerceIn(0f,duration.toFloat().coerceAtLeast(1f)),{dragged=it},
                    valueRange=0f..duration.toFloat().coerceAtLeast(1f),enabled=enabled&&duration>0,
                    onValueChangeFinished={dragged?.let {onSeek(it.toDouble())};dragged=null},slim=true,
                    modifier=Modifier.weight(1f).testTag("effects-timeline").a11yLabel("Posição na música"))
                UiText(mediaClock(duration.toLong()),style=MaterialTheme.typography.labelSmall)
            }

        }
    }
}
