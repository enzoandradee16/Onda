package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

@Composable internal fun FailureSummaryWindow(ids:List<String>,vm:OndaViewModel,onClose:()->Unit) {
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    var searchStarted by remember {mutableStateOf(false)}
    val selectedIds=remember(ids) {ids.toHashSet()}
    val snapshot=remember(ids) {OndaStore.items.value.filter {it.id in selectedIds}.map {it.copy(config=JSONObject(it.config.toString()))}}
    var selected by remember {mutableStateOf<String?>(null)}
    var query by remember {mutableStateOf("")}
    var provider by remember {mutableStateOf("Deezer")}
    var results by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    var candidate by remember {mutableStateOf<JSONObject?>(null)}
    var revision by remember {mutableIntStateOf(0)}
    var report by remember {mutableStateOf("")}
    var retrying by remember {mutableStateOf(false)}
    val scope=rememberCoroutineScope()
    val language=LocalUiLanguage.current
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) {uri->
        if(uri!=null)scope.launch {
            try {withContext(Dispatchers.IO) {OndaStore.context.contentResolver.openOutputStream(uri)?.use {it.write(report.toByteArray(Charsets.UTF_8))} ?: error("Não foi possível salvar a lista")}}
            catch(error:Exception) {vm.showNotice("Salvar lista",uiExceptionMessage(error,"Não foi possível salvar a lista"))}
        }
    }
    val item=queue.firstOrNull {it.id==selected}
    fun search() {
        val id=selected ?: return
        if(query.trim().length<2 || busy)return
        revision++;val request=revision;results=emptyList();candidate=null;searchStarted=true
        vm.operation("search",OndaStore.config().put("query",query.trim()).put("provider",provider)) {result->
            if(request==revision && selected==id)results=result.optJSONArray("tracks")?.objects() ?: emptyList()
        }
    }
    Dialog(onDismissRequest=onClose) {
        Surface(shape=MaterialTheme.shapes.large,color=ondaDialogContainerColor()) {
            Column(Modifier.fillMaxWidth().heightIn(max=650.dp).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                UiText("Falhas da fila",style=MaterialTheme.typography.titleLarge)
                if(selected==null) {
                    UiText("${snapshot.size} downloads falharam")
                    UiText("Salve a lista ou escolha outros metadados para os itens de áudio. Depois, tente novamente.")
                    LazyColumn(Modifier.weight(1f,false).testTag("failure-list")) {
                        items(snapshot,key={it.id}) {failed->
                            Column(Modifier.fillMaxWidth().padding(vertical=8.dp)) {
                                UiText(failed.title,style=MaterialTheme.typography.titleSmall)
                                UiErrorText(failed.message.ifBlank {"Motivo não informado"})
                                UiText(failed.config.optString("url"),style=MaterialTheme.typography.bodySmall)
                                TextButton(onClick={selected=failed.id;query=failed.title;results=emptyList();candidate=null;searchStarted=false},enabled=failed.config.optString("mode") in failureAudioModes && !failed.config.optBoolean("playlist"),modifier=Modifier.testTag("failure-metadata-${failed.id}")) {UiText("Escolher metadados")}
                            }
                            HorizontalDivider()
                        }
                    }
                    TextButton(onClick={report=failureReportText(snapshot){translateError(it,language)};export.launch("ONDA-falhas.txt")}) {UiText("Salvar lista")}
                    TextButton(onClick={
                        val pending=queue.filter {it.id in selectedIds && it.state in setOf("Erro","Pendente") && it.id !in DownloadRuntime.ids}.map {it.id}
                        retrying=true
                        scope.launch {
                            try {
                                withContext(Dispatchers.IO) {OndaStore.retry(pending.toSet())}
                                if(pending.isNotEmpty())DownloadService.batch(OndaStore.context,pending)
                                onClose()
                            } catch(error:kotlinx.coroutines.CancellationException) {throw error}
                            catch(error:Exception) {vm.showNotice("Falhas da fila",uiExceptionMessage(error,"Não foi possível tentar novamente"))}
                            finally {retrying=false}
                        }
                    },enabled=!retrying && queue.any {it.id in selectedIds && it.state in setOf("Erro","Pendente")}) {UiText("Tentar novamente")}
                } else {
                    UiText(item?.title ?: "Música",style=MaterialTheme.typography.titleSmall)
                    OutlinedTextField(value=query,onValueChange={query=it},label={UiText("Música ou artista")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                    Row {TextButton(onClick={provider="Deezer"}) {UiText("Deezer")};TextButton(onClick={provider="Apple / iTunes"}) {UiText("Apple / iTunes")}}
                    UiText(provider,style=MaterialTheme.typography.labelSmall)
                    TextButton(onClick={search()},enabled=!busy && query.trim().length>=2) {UiText("Pesquisar metadados")}
                    if(searchStarted)UiText(status,maxLines=3,style=MaterialTheme.typography.bodySmall)
                    LazyColumn(Modifier.weight(1f,false).testTag("failure-catalog-results")) {
                        items(results) {record->
                            TextButton(onClick={candidate=record},modifier=Modifier.fillMaxWidth()) {
                                UiText((if(candidate===record)"✓ " else "")+record.optString("title")+" · "+record.stringList("artists")+" · "+record.cleanString("album"))
                            }
                        }
                    }
                    UiText("A escolha substituirá a fonte de metadados deste item; formato e pasta serão mantidos.")
                    TextButton(onClick={candidate?.let {record->selected?.let {id->if(OndaStore.useFailureMetadata(id,record)){revision++;selected=null;results=emptyList();candidate=null}}}},enabled=candidate!=null && item?.state in setOf("Erro","Pendente")) {UiText("Usar estes metadados")}
                    TextButton(onClick={revision++;selected=null;results=emptyList();candidate=null}) {UiText("Voltar")}
                }
                TextButton(onClick=onClose) {UiText("Fechar")}
            }
        }
    }
}
