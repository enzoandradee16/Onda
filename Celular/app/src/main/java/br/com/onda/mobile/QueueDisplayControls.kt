package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import org.json.JSONObject

@Composable internal fun QueueDisplayControls(settings:JSONObject) = CollectionDisplayControls(settings,"queue_view","queue_card_size","Completa","queue")


@Composable private fun CollectionDisplayControls(settings:JSONObject,viewKey:String,sizeKey:String,defaultView:String,prefix:String) {
    var viewMenu by remember {mutableStateOf(false)}
    var sizeMenu by remember {mutableStateOf(false)}
    val view=settings.optString(viewKey,defaultView)
    val size=settings.optString(sizeKey,"Grande")
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.End) {
        Box {
            TextButton(onClick={viewMenu=true},contentPadding=PaddingValues(4.dp),modifier=Modifier.testTag("$prefix-view-control").a11yLabel(translateUi("Visualização da fila",LocalUiLanguage.current)+": "+translateUi(view,LocalUiLanguage.current),if(viewMenu) "Expandido" else "Recolhido")) {UiText("$view ▾",modifier=Modifier.clearAndSetSemantics {},style=MaterialTheme.typography.labelSmall)}
            DropdownMenu(expanded=viewMenu,onDismissRequest={viewMenu=false}) {
                listOf("Compacto","Completa").forEach {choice->DropdownMenuItem(text={UiText(choice)},onClick={OndaStore.saveSettings(JSONObject(settings.toString()).put(viewKey,choice));viewMenu=false})}
            }
        }
        if(view=="Completa") Box {
            TextButton(onClick={sizeMenu=true},contentPadding=PaddingValues(4.dp),modifier=Modifier.testTag("$prefix-size-control").a11yLabel(translateUi("Tamanho dos cards da fila",LocalUiLanguage.current)+": "+translateUi(size,LocalUiLanguage.current),if(sizeMenu) "Expandido" else "Recolhido")) {UiText("Cards: $size ▾",modifier=Modifier.clearAndSetSemantics {},style=MaterialTheme.typography.labelSmall)}
            DropdownMenu(expanded=sizeMenu,onDismissRequest={sizeMenu=false}) {
                listOf("Pequeno","Médio","Grande").forEach {choice->DropdownMenuItem(text={UiText(choice)},onClick={OndaStore.saveSettings(JSONObject(settings.toString()).put(sizeKey,choice));sizeMenu=false})}
            }
        }
    }
}

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
