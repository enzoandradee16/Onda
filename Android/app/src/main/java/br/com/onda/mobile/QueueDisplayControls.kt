package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import org.json.JSONObject

/** Size remains directly available on the redesigned downloads screen. */
@Composable internal fun DownloadCardSizeControl(settings:JSONObject,compact:Boolean=false) {
    var open by remember {mutableStateOf(false)}
    val size=settings.optString("queue_card_size","Grande")
    Row(if(compact)Modifier else Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.End) {
        Box {
            TextButton(onClick={open=true},modifier=Modifier.testTag("download-card-size").a11yLabel(translateUi("Tamanho dos cards")+": "+translateUi(size))) {if(compact)Text(translateUi(size)+" ▾",style=MaterialTheme.typography.labelSmall) else UiText("Cards: $size ▾",style=MaterialTheme.typography.labelSmall)}
            DropdownMenu(expanded=open,onDismissRequest={open=false}) {
                listOf("Pequeno","Médio","Grande").forEach {choice->DropdownMenuItem(text={UiText(choice)},onClick={OndaStore.saveSettings(JSONObject(settings.toString()).put("queue_card_size",choice));open=false})}
            }
        }
    }
}
