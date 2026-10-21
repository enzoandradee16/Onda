package br.com.onda.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.font.FontWeight

/** Shared surfaces for the Android tools; all colors follow the selected theme. */
@Composable internal fun ToolCard(modifier:Modifier=Modifier,content:@Composable ColumnScope.()->Unit) {
    Surface(modifier.fillMaxWidth(),shape=RoundedCornerShape(18.dp),color=MaterialTheme.colorScheme.surfaceVariant.copy(alpha=.45f),border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant.copy(alpha=.45f))) {
        Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp),content=content)
    }
}

@Composable internal fun ToolHeading(title:String,action:(@Composable ()->Unit)?=null) {
    Row(Modifier.fillMaxWidth().padding(vertical=8.dp),verticalAlignment=Alignment.CenterVertically) {
        UiText(title,Modifier.weight(1f),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold)
        action?.invoke()
    }
}

@Composable internal fun ToolEmpty(icon:String,title:String,description:String) {
    ToolCard {
        OndaIcon(icon,modifier=Modifier.size(36.dp),tint=MaterialTheme.colorScheme.primary)
        UiText(title,style=MaterialTheme.typography.titleMedium)
        UiText(description,style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable internal fun ToolSwitch(title:String,checked:Boolean,subtitle:String="",enabled:Boolean=true,changed:(Boolean)->Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min=56.dp).toggleable(value=checked,enabled=enabled,role=androidx.compose.ui.semantics.Role.Switch,onValueChange=changed),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
            UiText(title,style=MaterialTheme.typography.bodyLarge)
            if(subtitle.isNotBlank())UiText(subtitle,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Switch(checked,onCheckedChange=null,enabled=enabled)
    }
}

@Composable internal fun ToolLink(value:String,changed:(String)->Unit,label:String,modifier:Modifier=Modifier,submit:(()->Unit)?=null) {
    val clipboard=LocalClipboardManager.current
    OutlinedTextField(value,changed,modifier.fillMaxWidth(),label={UiText(label)},singleLine=true,shape=RoundedCornerShape(16.dp),trailingIcon={
        IconButton(onClick={if(submit!=null && value.isNotBlank())submit() else clipboard.getText()?.text?.let(changed)}) {
            OndaIcon(if(submit!=null && value.isNotBlank())"chevron" else "paste",if(submit!=null && value.isNotBlank())"Carregar" else "Colar",Modifier.size(22.dp))
        }
    })
}

@Composable internal fun ToolTabs(labels:List<String>,selected:Int,onSelect:(Int)->Unit) {
    Surface(shape=RoundedCornerShape(16.dp),color=MaterialTheme.colorScheme.surfaceVariant.copy(alpha=.5f)) {
        Row(Modifier.fillMaxWidth().padding(4.dp),horizontalArrangement=Arrangement.spacedBy(4.dp)) {
            labels.forEachIndexed {index,label->
                val active=index==selected
                Surface(Modifier.weight(1f).selectable(selected=active,role=androidx.compose.ui.semantics.Role.Tab,onClick={onSelect(index)}),shape=RoundedCornerShape(12.dp),color=if(active)MaterialTheme.colorScheme.primary else androidx.compose.ui.graphics.Color.Transparent,contentColor=if(active)MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface) {
                    Box(Modifier.heightIn(min=44.dp).padding(horizontal=8.dp,vertical=10.dp),contentAlignment=Alignment.Center){UiText(label,style=MaterialTheme.typography.labelLarge)}
                }
            }
        }
    }
}
