package br.com.onda.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/** Playback surfaces share desktop hierarchy while following the chosen Android theme. */
@Composable internal fun PlaybackCard(modifier:Modifier=Modifier,content:@Composable ColumnScope.()->Unit) {
    val colors=MaterialTheme.colorScheme
    Surface(modifier.fillMaxWidth(),shape=RoundedCornerShape(16.dp),color=colors.surfaceContainerLow,
        border=BorderStroke(1.dp,colors.outlineVariant)) {
        Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp),content=content)
    }
}

@Composable internal fun PlaybackSectionToggle(title:String,checked:Boolean,enabled:Boolean=true,changed:(Boolean)->Unit) {
    val colors=MaterialTheme.colorScheme
    Row(Modifier.fillMaxWidth().heightIn(min=48.dp).toggleable(checked,enabled=enabled,role=Role.Switch,onValueChange=changed),verticalAlignment=Alignment.CenterVertically) {
        UiText(title,Modifier.weight(1f),style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.SemiBold)
        Switch(checked,onCheckedChange=null,enabled=enabled,modifier=Modifier.testTag("switch-indicator-$title"),colors=SwitchDefaults.colors(
            checkedThumbColor=colors.onPrimary,checkedTrackColor=colors.primary,checkedBorderColor=colors.primary,
            uncheckedThumbColor=colors.onSurface,
            uncheckedTrackColor=colors.onSurface.copy(alpha=.20f).compositeOver(colors.surface),
            uncheckedBorderColor=colors.onSurfaceVariant))
    }
}

@Composable internal fun PlaybackAdjustment(label:String,value:Float,range:ClosedFloatingPointRange<Float>,tag:String,enabled:Boolean=true,changed:(Float)->Unit) {
    Column {
        UiText(label,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        RoundSlider(value,changed,valueRange=range,slim=true,enabled=enabled,
            modifier=Modifier.fillMaxWidth().height(36.dp).testTag(tag).a11yLabel(label))
    }
}
