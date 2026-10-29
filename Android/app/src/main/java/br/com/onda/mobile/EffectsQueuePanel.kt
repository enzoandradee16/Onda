package br.com.onda.mobile

import android.util.Base64
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.Dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import org.json.JSONObject
import kotlinx.coroutines.*
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.ImeAction

@Composable internal fun EffectsArtwork(info:JSONObject,modifier:Modifier=Modifier) {
    val encoded=info.optString("cover")
    val coverUrl=info.optJSONObject("record")?.optString("cover_url").orEmpty()
    val cover=remember(encoded,coverUrl){if(encoded.isBlank())coverUrl.takeIf {it.isNotBlank()} else runCatching {Base64.decode(encoded,Base64.DEFAULT)}.getOrNull()}
    Surface(modifier.clip(RoundedCornerShape(12.dp)),color=MaterialTheme.colorScheme.surfaceVariant,shape=RoundedCornerShape(12.dp)) {
        if(cover!=null)AsyncImage(cover,translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Fit)
        else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(32.dp))}
    }
}

@Composable internal fun EffectsTrackInformation(info:JSONObject,source:String,artworkSize:Dp=96.dp,action:@Composable ()->Unit={}) {
    val record=info.optJSONObject("record") ?: JSONObject()
    ToolCard(Modifier.testTag("effects-track-information")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
            EffectsArtwork(info,Modifier.size(artworkSize))
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
                Text(record.optString("title").ifBlank {importedAudioName(source)},style=MaterialTheme.typography.titleMedium,maxLines=2)
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodyMedium)
                AlbumDateLabel(record)
                Text(mediaClock(info.optDouble("duration").toLong()),style=MaterialTheme.typography.labelMedium)
                action()
            }
        }
    }
}


@Composable internal fun PlaybackQueueRow(record:JSONObject,cover:String,duration:Long,current:Boolean,editing:Boolean,play:()->Unit,up:()->Unit,down:()->Unit,remove:()->Unit,canUp:Boolean,canDown:Boolean,preparation:String="",failed:Boolean=false,drag:@Composable ()->Unit={}) {
    var actions by remember {mutableStateOf(false)}
    Box(Modifier.fillMaxWidth()) {
    Column(Modifier.fillMaxWidth().onSecondaryClick(record.optString("source_url")){actions=true}) {
        Row(Modifier.fillMaxWidth().clickable(onClick=play).padding(vertical=10.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            EffectsArtwork(JSONObject().put("record",record).put("cover",cover),Modifier.size(48.dp))
            Column(Modifier.weight(1f)) {
                Text(record.optString("title"),maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis,color=if(current)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                AlbumDateLabel(record)
                if(preparation.isNotBlank())UiText(workflowLabel(preparation,true),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite},style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if(duration>0)Text(mediaClock(duration),style=MaterialTheme.typography.labelSmall)
            IconButton(onClick=play){OndaIcon("play",if(failed)"Tentar novamente" else if(current)"Reproduzir novamente" else "Reproduzir",Modifier.size(22.dp))}
            Box {
                IconButton(onClick={actions=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(20.dp))}
                DropdownMenu(actions,{actions=false}) {
                    DropdownMenuItem(text={UiText(if(failed)"Tentar novamente" else "Reproduzir")},onClick={actions=false;play()})
                    DropdownMenuItem(text={UiText("Mover para cima")},enabled=canUp,onClick={actions=false;up()})
                    DropdownMenuItem(text={UiText("Mover para baixo")},enabled=canDown,onClick={actions=false;down()})
                    DropdownMenuItem(text={UiText("Remover da fila")},onClick={actions=false;remove()})
                    DropdownMenuItem(text={UiText("Copiar link")},enabled=record.cleanString("source_url").isNotBlank(),onClick={actions=false;copyRecordLink(record)})
                }
            }
        }
        if(editing)Row {
            IconButton(onClick=up,enabled=canUp){OndaIcon("up","Mover para cima",Modifier.size(22.dp))}
            IconButton(onClick=down,enabled=canDown){OndaIcon("down","Mover para baixo",Modifier.size(22.dp))}
            IconButton(onClick=remove){OndaIcon("close","Remover da fila",Modifier.size(22.dp))}
        }
    }
        Box(Modifier.align(Alignment.BottomEnd).padding(end=12.dp,bottom=2.dp)){drag()}
    }
}
@Composable internal fun EffectsQueuePanel(vm:OndaViewModel,source:String,onPlay:(Int)->Unit) {
    val queue by vm.effectsPlaylist.collectAsStateWithLifecycle()
    val infos by vm.effectsInfo.collectAsStateWithLifecycle()
    val preparations by vm.effectsPreparation.collectAsStateWithLifecycle()
    val preparationErrors by vm.effectsPreparationErrors.collectAsStateWithLifecycle()
    val preparing by vm.effectsPreparing.collectAsStateWithLifecycle()
    val playing by vm.previewActive.collectAsStateWithLifecycle()
    val listState=rememberLazyListState()
    var editing by remember {mutableStateOf(false)}
    Column(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset).testTag("effects-queue-panel")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText("Fila",Modifier.weight(1f),style=MaterialTheme.typography.titleLarge);TextButton(onClick={editing=!editing}){UiText(if(editing)"Pronto" else "Editar")}}
        if(editing)TextButton(onClick=vm::clearEffectsQueue){UiText("Limpar fila")}
        PlaybackQueueSearch(vm,false)
        val active=queue.indexOf(source)
        LazyColumn(Modifier.weight(1f),state=listState) {
            if(queue.isEmpty())item {UiText("Adicione arquivos, músicas, álbuns ou playlists à fila.")}
            itemsIndexed(queue,key={_,path->path}) {index,path->
                if(index==0&&active>0)UiText("Já tocadas",style=MaterialTheme.typography.labelLarge)
                if(index==active)UiText("Tocando agora",style=MaterialTheme.typography.labelLarge)
                if(index==active+1)UiText("A seguir",style=MaterialTheme.typography.labelLarge)
                val info=infos[path] ?: JSONObject()
                val record=info.optJSONObject("record") ?: JSONObject().put("title",importedAudioName(path))
                val failure=preparationErrors[path] ?: info.optString("error")
                DraggableQueueCard(listState,index,queue.size,move={from,to->vm.moveEffectsTrack(from,to-from)}) {
                PlaybackQueueRow(record,info.optString("cover"),info.optDouble("duration",0.0).toLong(),path==source,editing,{if(failure.isNotBlank())vm.retryEffectsPreparation(path) else onPlay(index)},{vm.moveEffectsTrack(index,-1)},{vm.moveEffectsTrack(index,1)},{vm.removeEffectsTrack(index)},index>0,index+1<queue.size,preparation=if(path==source&&preparing)"Preparando efeitos…" else if(path==source&&playing)"Reproduzindo" else preparations[path] ?: if(info.has("error"))"Erro na preparação" else "Aguardando preparação",failed=failure.isNotBlank(),drag={QueueDragHandle(listState,index,queue.size,itemLabel=record.optString("title")){from,to->vm.moveEffectsTrack(from,to-from)}})
                }
                if(failure.isNotBlank()) {
                    UiText(failureAdvice(failure).first,style=MaterialTheme.typography.bodySmall)
                    UiErrorText(failure,style=MaterialTheme.typography.labelSmall)
                    TextButton(onClick={vm.retryEffectsPreparation(path)}){UiText("Tentar novamente")}
                }
            }
        }
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun EffectsQueueDrawer(vm:OndaViewModel) {
    val open by vm.effectsQueueOpen.collectAsStateWithLifecycle()
    val source by vm.effectsSource.collectAsStateWithLifecycle()
    if(open)ModalBottomSheet(onDismissRequest={vm.effectsQueueOpen.value=false},sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true)) {
        Box(Modifier.fillMaxWidth().fillMaxHeight(.85f)){EffectsQueuePanel(vm,source,vm::playEffectsQueueTrack)}
    }
}

@Composable internal fun SearchTrackInformation(original:JSONObject,vm:OndaViewModel?=null) {
    val record=rememberCardMetadata(original,vm)
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        EffectsArtwork(JSONObject().put("record",record),Modifier.size(56.dp))
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
            Text(record.optString("title"),maxLines=2,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)

            AlbumDateLabel(record)
        }
    }
}

@Composable internal fun PlaybackQueueSearch(vm:OndaViewModel,jukeboxTarget:Boolean) {
    val scope=rememberCoroutineScope()
    var query by rememberSaveable {mutableStateOf("")}
    var results by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    var searching by remember {mutableStateOf(false)}
    var message by remember {mutableStateOf("")}
    var job by remember {mutableStateOf<Job?>(null)}
    val id=remember {"queue-input-"+java.util.UUID.randomUUID()}
    val loading by vm.loadingPlaybackCollection.collectAsStateWithLifecycle()
    DisposableEffect(id){onDispose {job?.cancel();MobileEngine.cancel(id)}}
    fun search() {
        if(searching){job?.cancel();MobileEngine.cancel(id);return}
        if(loading&&!jukeboxTarget){vm.cancelPlaybackCollection();return}
        if(query.isBlank())return
        job=scope.launch {
            searching=true;message=""
            try {
                val resolved=vm.jukebox.resolveQueueInput(query,id)
                val rows=resolved.optJSONArray("tracks")?.objects().orEmpty()
                if(resolved.optBoolean("is_collection")){vm.addPlaybackCollection(rows,jukeboxTarget);results=emptyList();message=resolved.optString("coverage_summary").ifBlank {"${rows.size} músicas adicionadas à fila."}}
                else {results=rows;if(rows.isEmpty())message="Nenhuma música encontrada."}
            } catch(e:CancellationException){throw e} catch(e:Exception){message=uiExceptionMessage(e,"Falha de pesquisa.")} finally {searching=false;MobileEngine.cancel(id)}
        }
    }
    OutlinedTextField(query,{query=it},label={UiText(PLAYBACK_INPUT_HINT)},singleLine=true,keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={search()}),trailingIcon={if(query.isNotEmpty()||results.isNotEmpty()||searching)IconButton(onClick={job?.cancel();MobileEngine.cancel(id);results=emptyList();query="";message="";searching=false},modifier=Modifier.testTag("close-playback-queue-search")){OndaIcon("close","Fechar pesquisa",Modifier.size(22.dp))}},modifier=Modifier.fillMaxWidth().testTag("playback-queue-search"))
    TextButton(onClick=::search,enabled=searching||(!jukeboxTarget&&loading)||query.isNotBlank()){UiText(if(searching||(!jukeboxTarget&&loading))"Cancelar" else "Pesquisar")}
    if(message.isNotBlank())UiText(message,style=MaterialTheme.typography.bodySmall)
    if(results.isNotEmpty())LazyColumn(Modifier.fillMaxWidth().heightIn(max=230.dp),verticalArrangement=Arrangement.spacedBy(10.dp),contentPadding=PaddingValues(vertical=6.dp)) {
        itemsIndexed(results) {_,record->
            OutlinedButton(onClick={vm.addPlaybackCollection(listOf(record),jukeboxTarget);results=results.filter {it!==record}},enabled=jukeboxTarget||!loading,modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(12.dp),contentPadding=PaddingValues(12.dp),border=androidx.compose.foundation.BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),colors=ButtonDefaults.outlinedButtonColors(containerColor=MaterialTheme.colorScheme.surfaceContainerLow)) {
                Column(Modifier.weight(1f)){SearchTrackInformation(record,vm)}
                OndaIcon("add","Adicionar à fila",Modifier.size(22.dp))
            }
        }
    }
}

@Composable internal fun PlaybackSearchResult(record:JSONObject,vm:OndaViewModel,enabled:Boolean,play:()->Unit,add:()->Unit) {
    var actions by remember {mutableStateOf(false)}
    Column(Modifier.fillMaxWidth().onSecondaryClick(record.optString("source_url")){actions=true}) {
        SearchTrackInformation(record,vm)
        Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            TextButton(enabled=enabled,onClick=play){UiText("Reproduzir")}
            TextButton(enabled=enabled,onClick=add){UiText("Adicionar à fila")}
            Box {
                IconButton(onClick={actions=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                DropdownMenu(actions,{actions=false}) {
                    DropdownMenuItem(text={UiText("Reproduzir")},enabled=enabled,onClick={actions=false;play()})
                    DropdownMenuItem(text={UiText("Adicionar à fila")},enabled=enabled,onClick={actions=false;add()})
                    DropdownMenuItem(text={UiText("Ver no catálogo")},onClick={actions=false;openRecordLink(record)})
                    DropdownMenuItem(text={UiText("Copiar link")},onClick={actions=false;copyRecordLink(record)})
                }
            }
        }
    }
}
