package br.com.onda.mobile

import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.layout.ContentScale
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** One downloads screen. Management controls extend the summary rather than replacing it. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun DownloadsHome(vm:OndaViewModel) {
    var completed by rememberSaveable {mutableStateOf(false)}
    var query by rememberSaveable {mutableStateOf("")}
    var searching by rememberSaveable {mutableStateOf(false)}
    var stateFilter by rememberSaveable {mutableStateOf("Todos")}
    var selectionMode by rememberSaveable {mutableStateOf(false)}
    var selected by remember {mutableStateOf(setOf<String>())}
    var menu by remember {mutableStateOf(false)}
    var organize by remember {mutableStateOf(false)}
    var showLogs by remember {mutableStateOf(false)}
    var clear by remember {mutableStateOf(false)}
    var metadataBatch by remember {mutableStateOf<List<String>?>(null)}
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val running by OndaStore.running.collectAsStateWithLifecycle()
    val pauseReason by OndaStore.queuePause.collectAsStateWithLifecycle()
    val logs by OndaStore.messages.collectAsStateWithLifecycle()
    val history by OndaStore.history.collectAsStateWithLifecycle()
    val listState=rememberLazyListState()
    val matcher=remember(query,stateFilter){QueueMatcher(query,stateFilter)}
    val shown=remember(queue,matcher,completed){queue.filter {(it.state=="Concluído")==completed && matcher.matches(it.title,it.state,it.config)}}
    val shownIds=remember(shown){shown.map {it.id}.toSet()}
    LaunchedEffect(shownIds){selected=selected.intersect(shownIds)}
    LaunchedEffect(shown){OndaStore.selectAll.collect {selectionMode=true;selected=shown.filterNot {it.config.optBoolean("_immediate")}.map {it.id}.toSet()}}
    var tick by remember {mutableLongStateOf(0L)}
    val owner=LocalLifecycleOwner.current
    LaunchedEffect(owner,running){if(running)owner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED){while(true){tick++;delay(1000)}}}
    val connected=remember(tick,pauseReason){queueConnected()}
    val finished=queue.count {it.state=="Concluído"}
    val timing=remember(queue,running,tick){OndaStore.queueTiming.snapshot(queue.size-finished,queue.isNotEmpty())}
    val remaining=timing.remaining?.let {if(it==0L)"00:00" else "≈ "+queueDuration(it)} ?: if(running)translateUi("Calculando…") else "—"
    val metadataUris=history.filter {record->historyKind(record.mode,record.title)=="Áudio" && queue.any {item->item.id in selected && item.state=="Concluído" && jobSource(item.config).isNotBlank() && jobSource(item.config)==record.source && item.config.optString("mode").equals(record.mode,true)}}.map {it.uri}.distinct()
    metadataBatch?.let {sources->
        if(sources.size>1)BatchMetadataEditor(vm,sources){metadataBatch=null}
        else Dialog(onDismissRequest={metadataBatch=null}) {Surface(shape=MaterialTheme.shapes.large){Column(Modifier.fillMaxWidth().fillMaxHeight(.9f)){
            TextButton(onClick={metadataBatch=null}){UiText("Pronto")}
            Box(Modifier.weight(1f)){MetadataPage(vm,sources.single())}
        }}}
    }
    if(organize)DownloadsOrganization(queue,stateFilter,{stateFilter=it;completed=it=="Concluídos"},{organize=false})
    if(showLogs)AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={showLogs=false},title={UiText("Ver detalhes")},text={Column(Modifier.heightIn(max=420.dp).verticalScroll(rememberScrollState())){UiText(logs.takeLast(100).joinToString("\n").ifBlank {translateUi("Nenhum detalhe disponível.")},style=MaterialTheme.typography.bodySmall)}},confirmButton={TextButton(onClick={showLogs=false}){UiText("Pronto")}})
    if(clear)AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={clear=false},title={UiText("Limpar fila?")},text={UiText("Remove todos os itens, exceto o download em andamento. Seus arquivos são preservados.")},confirmButton={TextButton(onClick={OndaStore.remove(queue.map {it.id}.toSet());clear=false}){UiText("Limpar")}},dismissButton={TextButton(onClick={clear=false}){UiText("Cancelar")}})
    Column(Modifier.fillMaxSize().padding(horizontal=24.dp).testTag("downloads-home")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
            UiText("Downloads",Modifier.weight(1f),style=MaterialTheme.typography.headlineMedium,fontWeight=FontWeight.Bold)
            DownloadCardSizeControl(settings,compact=true)
            Box {
                IconButton(onClick={menu=true},modifier=Modifier.testTag("downloads-menu")){OndaIcon("more","Mais ações",Modifier.size(24.dp))}
                DropdownMenu(menu,{menu=false}) {
                    DropdownMenuItem(text={UiText("Buscar na fila")},onClick={searching=true;menu=false})
                    DropdownMenuItem(text={UiText("Filtrar e ordenar")},onClick={organize=true;menu=false})
                    DropdownMenuItem(text={UiText(if(selectionMode)"Concluir seleção" else "Selecionar")},enabled=shown.isNotEmpty(),onClick={selectionMode=!selectionMode;selected=emptySet();menu=false})
                    DropdownMenuItem(text={UiText("Tentar novamente")},enabled=queue.any {it.state in listOf("Erro","Cancelado")},onClick={OndaStore.retry(queue.filter {it.state in listOf("Erro","Cancelado")}.map {it.id}.toSet());menu=false})
                    DropdownMenuItem(text={UiText("Cancelar fila")},enabled=running,onClick={DownloadService.stop(OndaStore.context);menu=false})
                    DropdownMenuItem(text={UiText("Limpar fila")},enabled=queue.isNotEmpty(),onClick={clear=true;menu=false})
                    DropdownMenuItem(text={UiText("Ver detalhes")},onClick={showLogs=true;menu=false})
                }
            }
        }
        val interrupted=queue.filter {it.config.optBoolean("_interrupted")&&it.state=="Pendente"}
        if(interrupted.isNotEmpty()&&!running) {
            UiText("Há downloads interrompidos. Retome de onde pararam quando a plataforma permitir.",style=MaterialTheme.typography.bodySmall)
            OutlinedButton(onClick={DownloadService.batch(OndaStore.context,interrupted.map {it.id})}){UiText("Retomar interrompidos")}
        }
        Box(Modifier.fillMaxWidth().padding(vertical=16.dp)) {
            ToolTabs(listOf("Em andamento","Concluídos"),if(completed)1 else 0){completed=it==1;stateFilter="Todos";selected=emptySet()}
        }
        if(searching)OutlinedTextField(query,{query=it},label={UiText("Buscar na fila")},singleLine=true,shape=RoundedCornerShape(16.dp),modifier=Modifier.fillMaxWidth().padding(bottom=12.dp).testTag("queue-search"),trailingIcon={IconButton(onClick={query="";searching=false}){OndaIcon("close","Limpar filtros",Modifier.size(20.dp))}})
        if(stateFilter!="Todos")TextButton(onClick={stateFilter="Todos"},modifier=Modifier.testTag("downloads-clear-filter")){UiText("${translateUi("Estado")}: ${translateUi(stateFilter)} · ${translateUi("Limpar filtros")}")}
        if(!completed && queue.any {it.state=="Pendente"} && !running)Button(onClick={DownloadService.start(OndaStore.context)},modifier=Modifier.fillMaxWidth().padding(bottom=8.dp)){UiText("Baixar fila")}
        if(running)Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText("Concluídos: $finished/${queue.size} · Restantes: ${queue.size-finished}",Modifier.weight(1f),style=MaterialTheme.typography.labelSmall);TextButton(onClick={DownloadService.control(OndaStore.context,if(DownloadRuntime.paused)"resume" else "pause")}){UiText(if(DownloadRuntime.paused)"Retomar fila" else "Pausar fila")}}
        if(running)UiText("Tempo decorrido: ${queueDuration(timing.elapsed)} · Tempo restante: $remaining",style=MaterialTheme.typography.labelSmall,modifier=Modifier.padding(bottom=8.dp).testTag("queue-time"))
        if(selectionMode) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText("${selected.size} selecionados",Modifier.weight(1f),style=MaterialTheme.typography.labelSmall);TextButton(onClick={selected=shown.filterNot {it.config.optBoolean("_immediate")}.map {it.id}.toSet()}){UiText("Selecionar visíveis")};TextButton(onClick={selectionMode=false;selected=emptySet()}){UiText("Pronto")}}
            Row(Modifier.horizontalScroll(rememberScrollState())) {
                TextButton(enabled=selected.isNotEmpty(),onClick={OndaStore.remove(selected);selected=emptySet()},modifier=Modifier.testTag("downloads-remove-selected")){UiText("Remover selecionados")}
                TextButton(enabled=queue.any {it.id in selected && it.state in listOf("Erro","Cancelado")},onClick={OndaStore.retry(selected)}){UiText("Tentar novamente")}
                TextButton(enabled=metadataUris.isNotEmpty(),onClick={metadataBatch=metadataUris}){UiText("Editar metadados")}
            }
        }
        NavigableList(Modifier.weight(1f),navigationId="queue",state=listState,verticalArrangement=Arrangement.spacedBy(12.dp)) {
            if(shown.isEmpty())item {UiText(if(query.isNotBlank() || stateFilter!="Todos")"Nenhum item corresponde aos filtros." else if(completed)"Nenhum download concluído" else "Nenhum download na fila",style=MaterialTheme.typography.titleMedium,modifier=Modifier.padding(top=24.dp));if(query.isBlank() && stateFilter=="Todos")UiText("Use + para adicionar links ou encontre músicas na pesquisa.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
            itemsIndexed(shown,key={_,it->it.id}) {index,item->
                DraggableQueueCard(listState,index,shown.size,enabled=!completed&&!selectionMode&&item.state=="Pendente",move={from,to->OndaStore.movePendingBefore(shown[from].id,shown[to].id)}) {
                    DownloadSummaryCard(item,vm,settings,selectionMode,item.id in selected,{checked->selected=if(checked)selected+item.id else selected-item.id},queueActivity(item,running,settings,connected,pauseReason))
                    if(!completed&&!selectionMode)QueueDragHandle(listState,index,shown.size,enabled=item.state=="Pendente",itemLabel=item.title,modifier=Modifier.align(Alignment.BottomEnd).padding(end=12.dp,bottom=6.dp)){from,to->OndaStore.movePendingBefore(shown[from].id,shown[to].id)}
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun DownloadsOrganization(queue:List<DownloadItem>,filter:String,onFilter:(String)->Unit,onDismiss:()->Unit) {
    var order by rememberSaveable {mutableStateOf(queueOrders.first())}
    var space by remember {mutableStateOf<QueueSpace?>(null)}
    LaunchedEffect(queue){space=withContext(Dispatchers.IO){queueSpace(queue,true)}}
    ModalBottomSheet(onDismissRequest=onDismiss,sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true)) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).navigationBarsPadding().padding(24.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            ToolHeading("Filtrar e ordenar")
            Select("Estado",filter,queueFilters){onFilter(it)}
            Select("Ordenar pendentes",order,queueOrders){order=it}
            Text(space?.text(LocalUiLanguage.current) ?: translateUi("Calculando…"),style=MaterialTheme.typography.bodySmall)
            if(space?.low==true)UiText("Espaço possivelmente insuficiente",color=MaterialTheme.colorScheme.error)
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                TextButton(onClick={onFilter("Todos")}){UiText("Limpar filtros")}
                Button(onClick={OndaStore.sortPending(order);onDismiss()},modifier=Modifier.weight(1f)){UiText("Aplicar")}
            }
        }
    }
}

@Composable private fun DownloadSummaryCard(item:DownloadItem,vm:OndaViewModel,settings:JSONObject,selectionMode:Boolean,selected:Boolean,onSelect:(Boolean)->Unit,activity:String) {
    var menu by remember {mutableStateOf(false)}
    val cardSize=settings.optString("queue_card_size","Grande")
    val coverSide=when(cardSize){"Pequeno"->56.dp;"Médio"->80.dp;else->100.dp}
    val cardPadding=when(cardSize){"Pequeno"->10.dp;"Médio"->12.dp;else->16.dp}
    LaunchedEffect(item.id,item.config.optString("url")){if(item.config.optJSONObject("queue_info")==null && item.config.optJSONObject("catalog_record")==null)vm.loadQueueInformation(item)}
    val info=item.config.optJSONObject("queue_info") ?: item.config.optJSONObject("catalog_record")
    val artists=info?.optJSONArray("artists")?.let {a->(0 until a.length()).joinToString(", "){a.optString(it)}}.orEmpty()
    val immediate=item.config.optBoolean("_immediate")
    val imageMedia=historyKind(item.config.optString("mode"),item.title)=="Imagens"
    val published by OndaStore.history.collectAsStateWithLifecycle()
    val initialImage=remember(published,item.id,item.state) {if(item.state=="Concluído")published.filter {historyKind(it.mode,it.title)=="Imagens" && it.source==jobSource(item.config)}.minByOrNull {it.id} else null}
    var imagePreview by remember(item.id){mutableStateOf(false)}
    if(imagePreview && initialImage!=null)HistoryImageGallery(initialImage,vm){imagePreview=false}
    var repairLink by remember(item.id){mutableStateOf(false)}
    var replacement by remember(item.id){mutableStateOf(item.config.optString("url"))}
    var invalidLink by remember(item.id){mutableStateOf(false)}
    if(repairLink)AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={repairLink=false},title={UiText("Atualizar link")},text={OutlinedTextField(replacement,{replacement=it;invalidLink=false},label={UiText("Cole o link atualizado.")},isError=invalidLink,singleLine=true,modifier=Modifier.testTag("repair-download-link"))},confirmButton={TextButton(onClick={if(OndaStore.replaceDownloadLink(item.id,replacement)){repairLink=false;DownloadService.start(OndaStore.context,item.id)}else invalidLink=true}){UiText("Tentar novamente")}},dismissButton={TextButton(onClick={repairLink=false}){UiText("Cancelar")}})
    val modifier=Modifier.fillMaxWidth().testTag("download-summary-${item.id}").then(if(selectionMode && !immediate)Modifier.toggleable(selected,role=Role.Checkbox,onValueChange=onSelect) else Modifier)
    Surface(shape=RoundedCornerShape(18.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,modifier=modifier.onSecondaryClick(item.id){menu=true}.then(if(initialImage!=null&&!selectionMode)Modifier.clickable(onClickLabel=translateUi("Ver imagens")){imagePreview=true} else Modifier)) {
        Row(Modifier.padding(cardPadding).heightIn(min=coverSide),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalAlignment=Alignment.CenterVertically) {
            if(selectionMode && !immediate)Checkbox(selected,null)
            Box(Modifier.size(coverSide).clip(RoundedCornerShape(10.dp)).testTag("queue-cover-${item.id}"),contentAlignment=Alignment.Center){
                val artwork=initialImage?.uri ?: info?.cleanString("cover_url").orEmpty()
                if(artwork.isBlank())OndaIcon(if(imageMedia)"image" else "album",modifier=Modifier.size(32.dp)) else AsyncImage(artwork,translateUi(if(initialImage!=null)"Prévia da imagem" else "Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Crop)
            }
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                Text(songCardTitle(info?.cleanString("title")?.ifBlank {item.title} ?: item.title,artists),fontWeight=FontWeight.Medium,maxLines=if(cardSize=="Pequeno")1 else 2,overflow=TextOverflow.Ellipsis,style=if(cardSize=="Pequeno")MaterialTheme.typography.bodyMedium else MaterialTheme.typography.titleSmall)
                if(artists.isNotBlank())Text(artists,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                if(cardSize!="Pequeno" && !info?.cleanString("album").isNullOrBlank())Text(info!!.cleanString("album"),maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                info?.let {ReleaseDateLabel(it)}
                MetadataPlatformBadge(info,source=item.config.optString("url"),imageMedia=imageMedia)
                if(initialImage==null && canPreviewOnlineImages(item.config))OnlineImagePreviewButton(vm,item.config.optString("url"))
                if(initialImage!=null)TextButton(onClick={imagePreview=true},modifier=Modifier.testTag("download-image-preview-${item.id}")){UiText("Ver imagens")}
                if(item.state=="Erro") {
                    val advice=failureAdvice(item.message)
                    UiText(advice.first,style=MaterialTheme.typography.bodySmall)
                    TextButton(onClick={when(advice.second) {
                        "Atualizar link"->{replacement=item.config.optString("url");invalidLink=false;repairLink=true}
                        "Verificar acesso"->runCatching {OndaStore.context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,android.net.Uri.parse(item.config.optString("url"))).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.showNotice("Verificar acesso","Não foi possível abrir a origem.")}
                        else->{OndaStore.retry(setOf(item.id));DownloadService.start(OndaStore.context,item.id)}
                    }}){UiText(advice.second)}
                }
                if(item.state in listOf("Baixando","Aguardando escolha"))Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    if(activity.startsWith("Baixando") && item.progress>0) {
                        LinearProgressIndicator(progress={item.progress/100},modifier=Modifier.weight(1f).height(4.dp),strokeCap=StrokeCap.Round,drawStopIndicator={})
                        Text("${item.progress.toInt()}%",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    } else LinearProgressIndicator(modifier=Modifier.weight(1f).height(4.dp),strokeCap=StrokeCap.Round)
                } else UiText(item.state,style=MaterialTheme.typography.labelSmall,color=if(item.state=="Erro")MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
                if(activity.isNotBlank() && item.state in listOf("Baixando","Pausado","Aguardando escolha"))UiText(activity,style=MaterialTheme.typography.bodySmall,maxLines=2,overflow=TextOverflow.Ellipsis)
            }
            if(item.state=="Concluído")OndaIcon("check","Concluído",Modifier.size(22.dp),tint=MaterialTheme.colorScheme.primary)
            Box {IconButton(onClick={menu=true},modifier=Modifier.testTag("download-menu-${item.id}")){OndaIcon("more","Mais ações",Modifier.size(21.dp))};DropdownMenu(menu,{menu=false}) {
                DropdownMenuItem(text={UiText("Baixar agora")},enabled=item.state=="Pendente",onClick={DownloadService.start(OndaStore.context,item.id);menu=false})
                DropdownMenuItem(text={UiText("Tentar novamente")},enabled=item.state in listOf("Erro","Cancelado"),onClick={OndaStore.retry(setOf(item.id));menu=false})
                if(item.state=="Erro" && item.message.contains("Nenhuma versão suficientemente compatível",ignoreCase=true))DropdownMenuItem(text={UiText("Escolher versão")},onClick={OndaStore.retryWithVersionChoice(item.id);menu=false})
                if(item.state=="Pendente") {
                    DropdownMenuItem(text={UiText("Mover para cima")},onClick={OndaStore.move(item.id,-1);menu=false})
                    DropdownMenuItem(text={UiText("Mover para baixo")},onClick={OndaStore.move(item.id,1);menu=false})
                    DropdownMenuItem(text={UiText("Próximo")},onClick={OndaStore.move(item.id,0);menu=false})
                }
                DropdownMenuItem(text={UiText("Remover")},enabled=item.state !in listOf("Baixando","Aguardando escolha"),onClick={OndaStore.remove(setOf(item.id));menu=false})
                DropdownMenuItem(text={UiText("Ver detalhes")},onClick={vm.showNotice(item.title,item.message.ifBlank {activity.ifBlank {item.state}},error=item.state=="Erro");menu=false})
            }}
        }
    }
}
