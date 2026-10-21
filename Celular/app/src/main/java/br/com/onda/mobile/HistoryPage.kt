package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONArray
import org.json.JSONObject

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun HistoryPage(vm: OndaViewModel,onEditMetadata:(HistoryItem)->Unit) {
    LaunchedEffect(Unit) {invalidateHistoryDetails()}
    val history by OndaStore.history.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var filter by rememberSaveable {mutableStateOf("")}
    var kind by rememberSaveable {mutableStateOf("Todos")}
    var showOptions by remember {mutableStateOf(false)}
    if(showOptions)ModalBottomSheet(onDismissRequest={showOptions=false},sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true)) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).navigationBarsPadding().padding(20.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            ToolHeading("Histórico")
            Select("Visualização do histórico",settings.optString("history_view","Compacto"),listOf("Compacto","Completa")){OndaStore.saveSettings(JSONObject(settings.toString()).put("history_view",it))}
            Select("Tamanho dos cards do histórico",settings.optString("history_card_size","Grande"),listOf("Pequeno","Médio","Grande")){OndaStore.saveSettings(JSONObject(settings.toString()).put("history_card_size",it))}
            TextButton(onClick={OndaStore.clearHistory();showOptions=false}){UiText("Limpar histórico")}
            Button(onClick={showOptions=false},modifier=Modifier.fillMaxWidth()){UiText("Pronto")}
        }
    }
    var selectionMode by rememberSaveable {mutableStateOf(false)}
    var selected by remember {mutableStateOf(setOf<Long>())}
    var batch by remember {mutableStateOf<List<String>?>(null)}
    batch?.let {BatchMetadataEditor(vm,it){batch=null}}
    val visible=remember(history,filter,kind){history.filter {it.title.contains(filter,true) && (kind=="Todos" || historyKind(it.mode)==kind)}}
    var exported by remember {mutableStateOf("")}
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")){uri->if(uri!=null)runCatching {OndaStore.context.contentResolver.openOutputStream(uri)?.use {it.write(exported.toByteArray())}}.onFailure {vm.showNotice("Exportar histórico","Não foi possível salvar o histórico.")}}
    LazyColumn(Modifier.fillMaxSize().testTag("history-list").imePadding().padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(12.dp),contentPadding=PaddingValues(bottom=20.dp)) {
        item {ToolHeading("Histórico") {Row {IconButton(onClick={exported=JSONArray(visible.map {JSONObject().put("title",it.title).put("uri",it.uri).put("format",it.mode).put("source",it.source).put("completed_at",it.completedAt)}).toString(2);export.launch("ONDA-historico.json")}){OndaIcon("download","Exportar histórico",Modifier.size(24.dp))};IconButton(onClick={showOptions=true}){OndaIcon("more-vertical","Opções do histórico",Modifier.size(22.dp))}}}}
        item {OutlinedTextField(filter,{filter=it},label={UiText("Pesquisar no histórico")},modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(16.dp),singleLine=true,leadingIcon={OndaIcon("search",modifier=Modifier.size(20.dp))})}
        item {Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)){listOf("Todos","Áudio","Vídeo","Imagens").forEach {label->FilterChip(kind==label,{kind=label},label={UiText(label)},colors=FilterChipDefaults.filterChipColors(selectedContainerColor=MaterialTheme.colorScheme.primary,selectedLabelColor=MaterialTheme.colorScheme.onPrimary))}}}
        item {Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText(if(selectionMode)"${selected.size} selecionados" else "${visible.size} arquivos",Modifier.weight(1f),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant);TextButton(onClick={selectionMode=!selectionMode;selected=emptySet()}){UiText(if(selectionMode)"Concluir" else "Selecionar")}}}
        if(selectionMode)item {ToolCard {
            TextButton(onClick={selected=visible.filter {historyKind(it.mode)=="Áudio"}.map {it.id}.toSet()}){UiText("Selecionar áudios visíveis")}
            TextButton(onClick={selected=emptySet()}){UiText("Limpar seleção")}
            OutlinedButton(enabled=selected.isNotEmpty(),onClick={batch=history.filter {it.id in selected && historyKind(it.mode)=="Áudio"}.map {it.uri}.distinct()}){UiText("Editar metadados em lote")}
        }}
        if(visible.isEmpty())item {ToolEmpty("history",if(history.isEmpty())"Seu histórico está vazio" else "Nenhum resultado","Os arquivos baixados e convertidos aparecem aqui.")}
        visible.forEachIndexed {index,item->
            val day=historyDay(item.completedAt)
            if(index==0 || day!=historyDay(visible[index-1].completedAt))item(key="day-${item.id}"){UiText(day,style=MaterialTheme.typography.titleMedium,modifier=Modifier.padding(top=8.dp))}
            item(key=item.id) {HistoryToolCard(item,settings,vm,selectionMode,item.id in selected,{checked->selected=if(checked)selected+item.id else selected-item.id},onEditMetadata)}
        }
    }
}
