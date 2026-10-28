package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

@Composable internal fun PlaybackOrderControls(repeat:String,onRepeat:(String)->Unit) {
    Column(Modifier.fillMaxWidth()) {
        Select("Repetição",repeat,listOf("Desativada","Todas","Uma"),changed=onRepeat)
    }
}

@Composable internal fun ShufflePlaybackButton(checked:Boolean,onCheckedChange:(Boolean)->Unit,modifier:Modifier=Modifier) {
    IconToggleButton(checked=checked,onCheckedChange=onCheckedChange,modifier=modifier.testTag("playback-shuffle"),
        colors=IconButtonDefaults.iconToggleButtonColors(contentColor=LocalContentColor.current,checkedContentColor=MaterialTheme.colorScheme.primary)) {
        OndaIcon("shuffle","Reprodução aleatória",Modifier.size(23.dp))
    }
}

@Composable internal fun RepeatPlaybackButton(mode:String,onChange:(String)->Unit) {
    IconToggleButton(checked=mode!="Desativada",onCheckedChange={onChange(when(mode){"Desativada"->"Todas";"Todas"->"Uma";else->"Desativada"})},modifier=Modifier.testTag("playback-repeat"),
        colors=IconButtonDefaults.iconToggleButtonColors(contentColor=LocalContentColor.current,checkedContentColor=MaterialTheme.colorScheme.primary)) {
        OndaIcon(if(mode=="Uma")"repeat-one" else "repeat",translateUi("Repetição")+": "+translateUi(mode),Modifier.size(23.dp))
    }
}
