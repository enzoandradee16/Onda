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

@Composable internal fun HistoryDisplayControls(settings:JSONObject) = CollectionDisplayControls(settings,"history_view","history_card_size","Compacto","history",true)

@Composable private fun CollectionDisplayControls(settings:JSONObject,viewKey:String,sizeKey:String,defaultView:String,prefix:String,history:Boolean=false) {
    var viewMenu by remember {mutableStateOf(false)}
    var sizeMenu by remember {mutableStateOf(false)}
    val view=settings.optString(viewKey,defaultView)
    val size=settings.optString(sizeKey,"Grande")
    Row(Modifier.fillMaxWidth(),horizontalArrangement=if(history)Arrangement.Center else Arrangement.End) {
        if(history)TextButton(onClick={OndaStore.clearHistory()},contentPadding=PaddingValues(4.dp),modifier=Modifier.testTag("clear-history-control")) {UiText("Limpar histórico",style=MaterialTheme.typography.labelSmall)}
        Box {
            TextButton(onClick={viewMenu=true},contentPadding=PaddingValues(4.dp),modifier=Modifier.testTag("$prefix-view-control").a11yLabel(translateUi(if(history) "Visualização do histórico" else "Visualização da fila",LocalUiLanguage.current)+": "+translateUi(view,LocalUiLanguage.current),if(viewMenu) "Expandido" else "Recolhido")) {UiText("$view ▾",modifier=Modifier.clearAndSetSemantics {},style=MaterialTheme.typography.labelSmall)}
            DropdownMenu(expanded=viewMenu,onDismissRequest={viewMenu=false}) {
                listOf("Compacto","Completa").forEach {choice->DropdownMenuItem(text={UiText(choice)},onClick={OndaStore.saveSettings(JSONObject(settings.toString()).put(viewKey,choice));viewMenu=false})}
            }
        }
        if(view=="Completa") Box {
            TextButton(onClick={sizeMenu=true},contentPadding=PaddingValues(4.dp),modifier=Modifier.testTag("$prefix-size-control").a11yLabel(translateUi(if(history) "Tamanho dos cards do histórico" else "Tamanho dos cards da fila",LocalUiLanguage.current)+": "+translateUi(size,LocalUiLanguage.current),if(sizeMenu) "Expandido" else "Recolhido")) {UiText("Cards: $size ▾",modifier=Modifier.clearAndSetSemantics {},style=MaterialTheme.typography.labelSmall)}
            DropdownMenu(expanded=sizeMenu,onDismissRequest={sizeMenu=false}) {
                listOf("Pequeno","Médio","Grande").forEach {choice->DropdownMenuItem(text={UiText(choice)},onClick={OndaStore.saveSettings(JSONObject(settings.toString()).put(sizeKey,choice));sizeMenu=false})}
            }
        }
    }
}
