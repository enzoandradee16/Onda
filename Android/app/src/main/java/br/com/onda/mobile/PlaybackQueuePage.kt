package br.com.onda.mobile

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.boundsInParent
import androidx.compose.ui.geometry.Rect
import androidx.compose.foundation.background
import androidx.compose.ui.draw.clip
import androidx.compose.animation.core.tween
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.foundation.Canvas
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.SaveableStateHolder
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import org.json.JSONObject

/** Playback queue is a page inside the shell: one header, player and navigation bar. */
@Composable internal fun PlaybackQueuePage(vm:OndaViewModel,onClose:()->Unit={vm.playbackQueueOpen.value=false}) {
    val controller=vm.jukebox
    val localQueue by controller.playbackQueue.collectAsStateWithLifecycle()
    val localCurrent by controller.currentQueueId.collectAsStateWithLifecycle()
    val remote by RemotePlaybackRuntime.state.collectAsStateWithLifecycle()
    val queue=remember(remote.connected,remote.queue,localQueue){if(remote.connected)remote.queue.map {it.queueRecord()} else localQueue}
    val current=if(remote.connected)remote.trackId else localCurrent
    val summaryFlow=remember(controller){controller.state.map {it.model to it.title}.distinctUntilChanged()}
    val summary by summaryFlow.collectAsStateWithLifecycle(initialValue=controller.state.value.let {it.model to it.title})
    var recent by rememberSaveable {mutableStateOf(false)}
    var searching by rememberSaveable {mutableStateOf(false)}
    var actions by remember {mutableStateOf(false)}
    val listState=rememberLazyListState()
    val recentListState=rememberLazyListState()
    val swipeThreshold=with(LocalDensity.current){64.dp.toPx()}
    var previousSize by remember {mutableIntStateOf(queue.size)}
    LaunchedEffect(queue.size) {
        if(queue.size>previousSize){recent=false;listState.scrollToItem(0)}
        previousSize=queue.size
    }
    BackHandler(searching){searching=false}
    val files=rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) {uris->
        vm.importConversionBatch(uris){paths->paths.forEach {path->controller.enqueue(JSONObject().put("title",importedAudioName(path).substringBeforeLast('.')).put("_local_source",path))}}
    }
    val active=if(remote.connected)queue.indexOfFirst {it.optString("_queue_id")==current} else (controller.nextQueueIndex-1).coerceIn(-1,queue.lastIndex.coerceAtLeast(-1))
    LaunchedEffect(remote.connected,remote.trackId,remote.queue.size) {
        if(remote.connected && remote.online && active<0 && remote.queue.size<remote.queueTotal)RemotePlaybackRuntime.loadMore()
    }
    val played=if(remote.connected)queue.filter {it.optInt("_recent_rank",-1)>=0 && it.optString("_queue_id")!=current}.sortedBy {it.optInt("_recent_rank")} else queue.take(active.coerceAtLeast(0)).asReversed()
    val upcoming=queue.drop((active+1).coerceAtLeast(0)).filter { !remote.connected || remote.repeat=="Todas" || it.optInt("_recent_rank",-1)<0 }
    val currentRow=queue.firstOrNull {it.optString("_queue_id")==current} ?: if(remote.connected) {
        if(remote.trackId.isNotBlank())RemoteQueueTrack(remote.trackId,remote.title,remote.artist,remote.duration).queueRecord() else null
    } else summary.first?.let {model->
        JSONObject().put("title",summary.second).put("artists",org.json.JSONArray(listOf(model.optString("media_artist"))))
            .put("cover_url",model.optString("cover_url")).put("_cover",model.optString("media_cover")).put("duration_ms",(model.optDouble("duration")*1000).toLong())
    }
    BoxWithConstraints(Modifier.fillMaxSize().testTag("playback-queue-page").pointerInput(searching,swipeThreshold) {
        if(!searching) {
            var distance=0f
            detectHorizontalDragGestures(
                onDragStart={distance=0f},
                onDragCancel={distance=0f},
                onDragEnd={
                    if(distance < -swipeThreshold)recent=true
                    else if(distance > swipeThreshold)recent=false
                    distance=0f
                },
                onHorizontalDrag={change,amount->change.consume();distance+=amount}
            )
        }
    }) {
        val searchHeight=(maxHeight*.45f).coerceAtMost(260.dp)
        Column(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                PlaybackQueueTabs(recent,Modifier.weight(1f)){recent=it}
                IconButton(onClick={searching=!searching},modifier=Modifier.testTag("queue-toggle-search")) {
                    OndaIcon(if(searching)"close" else "search",if(searching)"Fechar pesquisa" else "Pesquisar",Modifier.size(22.dp))
                }
                Box {
                    IconButton(onClick={actions=true},modifier=Modifier.testTag("queue-page-actions")){OndaIcon("more","Mais ações",Modifier.size(22.dp))}
                    DropdownMenu(actions,{actions=false}) {
                        if(!remote.connected)DropdownMenuItem(text={UiText("Adicionar arquivos")},onClick={actions=false;files.launch(arrayOf("audio/*"))})
                        DropdownMenuItem(text={UiText("Limpar fila")},enabled=queue.isNotEmpty() && (!remote.connected || remote.online),onClick={actions=false;if(remote.connected)RemotePlaybackRuntime.command("queue_clear") else controller.clearPlaybackQueue()})
                        DropdownMenuItem(text={UiText("Fechar fila")},onClick={actions=false;onClose()})
                    }
                }
            }
            if(searching)Box(Modifier.fillMaxWidth().heightIn(max=searchHeight).verticalScroll(rememberScrollState())) {
                Column {PlaybackQueueSearch(vm,true)}
            }
            AnimatedContent(targetState=recent,modifier=Modifier.weight(1f).fillMaxWidth().clipToBounds(),transitionSpec={
                val direction=if(targetState)1 else -1
                ((slideInHorizontally(tween(240,easing=FastOutSlowInEasing)){it*direction}+fadeIn(tween(180))) togetherWith
                    (slideOutHorizontally(tween(240,easing=FastOutSlowInEasing)){-it*direction}+fadeOut(tween(180)))).using(null)
            },label="queue-tab-content") {visibleRecent->
                val shown=if(visibleRecent)played else upcoming
                val tabListState=if(visibleRecent)recentListState else listState
                Column(Modifier.fillMaxSize(),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                if(!visibleRecent && currentRow!=null) {
                    UiText("Tocando agora",style=MaterialTheme.typography.titleSmall,fontWeight=FontWeight.SemiBold,modifier=Modifier.padding(top=8.dp,bottom=4.dp))
                    Surface(shape=RoundedCornerShape(14.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),modifier=Modifier.fillMaxWidth().testTag("queue-current-card")) {
                        PlaybackQueueTrack(currentRow,vm,true,false,{},Modifier.padding(horizontal=10.dp,vertical=4.dp))
                    }
                }
                if(!visibleRecent)UiText("Próximas na fila",style=MaterialTheme.typography.titleSmall,fontWeight=FontWeight.SemiBold,modifier=Modifier.padding(top=12.dp,bottom=4.dp))
                LazyColumn(Modifier.weight(1f).fillMaxWidth().testTag(if(visibleRecent)"queue-recent-list" else "queue-upcoming-list"),state=tabListState) {
                    if(shown.isEmpty())item {
                        UiText(if(visibleRecent)"Nenhuma música encontrada." else "Nenhuma música na fila.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant,modifier=Modifier.padding(vertical=16.dp))
                    }
                    items(shown.size,key={shown[it].optString("_queue_id")}) {index->
                        val record=shown[index]
                        fun move(from:Int,to:Int) {
                            if(remote.connected) {
                                val rows=remote.queue
                                val a=rows.indexOfFirst {it.id==shown[from].optString("_queue_id")}
                                val b=rows.indexOfFirst {it.id==shown[to].optString("_queue_id")}
                                if(a>=0 && b>=0 && a!=b)RemotePlaybackRuntime.moveQueue(rows[a].id,b-a)
                                return
                            }
                            val rows=controller.playbackQueue.value
                            val fromIndex=rows.indexOfFirst {it.optString("_queue_id")==shown[from].optString("_queue_id")}
                            val toIndex=rows.indexOfFirst {it.optString("_queue_id")==shown[to].optString("_queue_id")}
                            if(fromIndex>=0 && toIndex>=0)controller.moveQueued(fromIndex,toIndex-fromIndex)
                        }
                        DraggableQueueCard(tabListState,index,shown.size,enabled=!visibleRecent,move=::move) {
                            SwipeRemoveQueueTrack(record.optString("_queue_id"),onRemove={
                                if(remote.connected)RemotePlaybackRuntime.command("queue_remove",trackId=record.optString("_queue_id")) else {
                                val actual=controller.playbackQueue.value.indexOfFirst {it.optString("_queue_id")==record.optString("_queue_id")}
                                if(actual>=0)controller.removeQueued(actual)
                                }
                            }) {
                            PlaybackQueueTrack(record,vm,false,visibleRecent,{
                                if(remote.connected)RemotePlaybackRuntime.command("queue_play",trackId=record.optString("_queue_id")) else {
                                val actual=controller.playbackQueue.value.indexOfFirst {it.optString("_queue_id")==record.optString("_queue_id")}
                                if(actual>=0){if(record.optString("_analysis")=="Erro")controller.retryQueued(actual) else controller.playQueued(actual)}
                                }
                            },Modifier.testTag("queue-track-"+record.optString("_queue_id"))) {
                                QueueDragHandle(tabListState,index,shown.size,enabled=!visibleRecent,itemLabel=record.optString("title"),icon="drag-lines",move=::move)
                            }
                            }
                        }
                        HorizontalDivider(color=MaterialTheme.colorScheme.outlineVariant.copy(alpha=.45f))
                    }
                    if(remote.connected && remote.queue.size<remote.queueTotal)item {
                        TextButton(onClick=RemotePlaybackRuntime::loadMore,enabled=remote.online && !remote.queueLoading){UiText("Carregar mais")}
                    }
                }
                }
            }
        }
    }
}

@Composable private fun PlaybackQueueTabs(recent:Boolean,modifier:Modifier=Modifier,select:(Boolean)->Unit) {
    var first by remember {mutableStateOf(Rect.Zero)}
    var second by remember {mutableStateOf(Rect.Zero)}
    val active=if(recent)second else first
    val density=LocalDensity.current
    val left by animateDpAsState(with(density){active.left.toDp()},tween(180,easing=FastOutSlowInEasing),label="queue-tab-indicator-position")
    val width by animateDpAsState(with(density){active.width.toDp()},tween(180,easing=FastOutSlowInEasing),label="queue-tab-indicator-width")
    Box(modifier.horizontalScroll(rememberScrollState())) {
        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            PlaybackQueueTab("Fila",!recent,"queue-tab-upcoming",Modifier.onGloballyPositioned {first=it.boundsInParent()}){select(false)}
            PlaybackQueueTab("Tocado recentemente",recent,"queue-tab-recent",Modifier.onGloballyPositioned {second=it.boundsInParent()}){select(true)}
        }
        Surface(Modifier.align(Alignment.BottomStart).offset(x=left).width(width).height(3.dp).testTag("queue-tab-indicator"),color=MaterialTheme.colorScheme.primary,shape=RoundedCornerShape(2.dp)){}
    }
}

@Composable private fun SwipeRemoveQueueTrack(identity:String,onRemove:()->Unit,content:@Composable ()->Unit) {
    val dismiss=rememberSwipeToDismissBoxState(positionalThreshold={it*.4f})
    val remove by rememberUpdatedState(onRemove)
    LaunchedEffect(dismiss.currentValue) {if(dismiss.currentValue==SwipeToDismissBoxValue.EndToStart)remove()}
    SwipeToDismissBox(state=dismiss,enableDismissFromStartToEnd=false,enableDismissFromEndToStart=true,
        modifier=Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).testTag("queue-swipe-"+identity),
        backgroundContent={
            if(dismiss.dismissDirection==SwipeToDismissBoxValue.EndToStart)Row(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.errorContainer).padding(horizontal=16.dp),horizontalArrangement=Arrangement.End,verticalAlignment=Alignment.CenterVertically) {
                OndaIcon("close","Remover",Modifier.size(22.dp),tint=MaterialTheme.colorScheme.onErrorContainer)
                Spacer(Modifier.width(8.dp));UiText("Remover",color=MaterialTheme.colorScheme.onErrorContainer)
            }
        }) {Surface(color=MaterialTheme.colorScheme.background){content()}}
}

@Composable private fun PlaybackQueueTab(title:String,selected:Boolean,tag:String,modifier:Modifier=Modifier,click:()->Unit) {
    val ink by animateColorAsState(if(selected)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,tween(160),label="queue-tab-color")
    Column(modifier.width(IntrinsicSize.Max).selectable(selected,role=Role.Tab,onClick=click).testTag(tag).padding(horizontal=4.dp)) {
        UiText(title,style=MaterialTheme.typography.labelLarge,fontWeight=FontWeight.SemiBold,color=ink,maxLines=1,modifier=Modifier.heightIn(min=44.dp).wrapContentHeight())
        Spacer(Modifier.height(3.dp))
    }
}

@Composable private fun PlaybackQueueTrack(record:JSONObject,vm:OndaViewModel,current:Boolean,recent:Boolean,play:()->Unit,modifier:Modifier=Modifier,drag:@Composable ()->Unit={}) {
    val controller=vm.jukebox
    val remote by RemotePlaybackRuntime.state.collectAsStateWithLifecycle()
    var actions by remember {mutableStateOf(false)}
    fun index()=if(remote.connected)remote.queue.indexOfFirst {it.id==record.optString("_queue_id")} else controller.playbackQueue.value.indexOfFirst {it.optString("_queue_id")==record.optString("_queue_id")}
    fun move(delta:Int){if(remote.connected)RemotePlaybackRuntime.moveQueue(record.optString("_queue_id"),delta) else controller.moveQueued(index(),delta)}
    val state=if(current && !remote.connected)controller.state.collectAsStateWithLifecycle().value else JukeboxState()
    val model=if(current && !remote.connected)state.model else null
    val artist=record.stringList("artists").ifBlank {model?.optString("media_artist").orEmpty()}
    val cover=record.optString("_cover").ifBlank {model?.optString("media_cover").orEmpty()}
    val duration=if(current && remote.connected)remote.duration.toLong() else record.optLong("duration_ms").takeIf {it>0}?.div(1000) ?: model?.optDouble("duration")?.toLong() ?: 0L
    val colors=MaterialTheme.colorScheme
    Row(modifier.fillMaxWidth().clickable(enabled=!current,onClick=play).padding(vertical=8.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        Column(Modifier.width(56.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
            if(current && remote.connected)RemoteCover(remote,Modifier.size(56.dp)) else EffectsArtwork(JSONObject().put("record",record).put("cover",cover),Modifier.size(56.dp))
            if(current && (model!=null || remote.connected)) {
                val remotePosition=if(remote.connected)remotePosition(remote) else 0.0
                val beats=model?.optJSONArray("beats");val a=beats?.optDouble(state.index,0.0) ?: 0.0;val b=beats?.optDouble(state.index+1,a) ?: a
                val progress=if(duration>0)((if(remote.connected)remotePosition else a+(b-a)*state.phase)/duration).toFloat().coerceIn(0f,1f) else 0f
                Canvas(Modifier.fillMaxWidth().padding(horizontal=3.dp).height(3.dp).testTag("queue-current-cover-progress")) {
                    val start=Offset(0f,center.y);val end=Offset(size.width,center.y)
                    drawLine(colors.primary.copy(alpha=.2f),start,end,size.height,StrokeCap.Round)
                    if(progress>0f)drawLine(colors.primary,start,Offset(size.width*progress,center.y),size.height,StrokeCap.Round)
                }
            } else if(record.optString("_analysis") in listOf("Preparando","Analisando")) {
                LinearProgressIndicator(Modifier.fillMaxWidth().padding(horizontal=3.dp).height(3.dp).testTag("queue-cover-preparation"))
            }
        }
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
            Text(record.optString("title"),style=MaterialTheme.typography.titleSmall,fontWeight=FontWeight.SemiBold,color=if(current)colors.primary else colors.onSurface,maxLines=1,overflow=TextOverflow.Ellipsis)
            Text(artist,style=MaterialTheme.typography.bodySmall,color=colors.onSurfaceVariant,maxLines=1,overflow=TextOverflow.Ellipsis)
        }
        if(duration>0)Text(mediaClock(duration),style=MaterialTheme.typography.labelSmall,color=colors.onSurfaceVariant)
        Box {
            IconButton(onClick={actions=true},modifier=Modifier.size(32.dp).testTag("queue-track-actions-"+record.optString("_queue_id"))) {
                if(current||recent)OndaIcon("drag-lines",modifier=Modifier.size(20.dp),tint=colors.onSurfaceVariant) else drag()
            }
            DropdownMenu(actions,{actions=false}) {
                if(!current)DropdownMenuItem(text={UiText(if(record.optString("_analysis")=="Erro")"Tentar novamente" else "Reproduzir")},onClick={actions=false;play()})
                if(!recent && !current) {
                    DropdownMenuItem(text={UiText("Mover para cima")},enabled=if(remote.connected)index()>remote.queue.indexOfFirst {it.id==remote.trackId}+1 else index()>controller.nextQueueIndex,onClick={actions=false;move(-1)})
                    DropdownMenuItem(text={UiText("Mover para baixo")},enabled=index()>=0 && index()<(if(remote.connected)remote.queueTotal-1 else controller.playbackQueue.value.lastIndex),onClick={actions=false;move(1)})
                }
                if(record.optString("_error").isNotBlank())DropdownMenuItem(text={UiText(translateError(record.optString("_error")))},onClick={actions=false;vm.showNotice("Erro",failureAdvice(record.optString("_error")).first,true)})
                DropdownMenuItem(text={UiText("Remover")},enabled=index()>=0,onClick={actions=false;if(remote.connected)RemotePlaybackRuntime.command("queue_remove",trackId=record.optString("_queue_id")) else controller.removeQueued(index())})
            }
        }
    }
}


/** The expanded player keeps its own queue overlay; dismissing it preserves the player. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun PlaybackQueueSheet(vm:OndaViewModel,close:()->Unit) {
    ModalBottomSheet(onDismissRequest=close,sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true),containerColor=MaterialTheme.colorScheme.surface) {
        Box(Modifier.fillMaxWidth().fillMaxHeight(.85f).navigationBarsPadding().testTag("expanded-player-queue-sheet")) {
            PlaybackQueuePage(vm,onClose=close)
        }
    }
}

/** Keep each page's saved query and scroll state while both participate in the transition. */
@Composable internal fun PlaybackQueueTransition(vm:OndaViewModel,pages:SaveableStateHolder,queueOpen:Boolean,motion:Boolean,content:@Composable ()->Unit) {
    var presented by remember {mutableStateOf(false)}
    LaunchedEffect(queueOpen){presented=queueOpen}
    AnimatedContent(targetState=presented,modifier=Modifier.fillMaxSize().clipToBounds(),transitionSpec={
        if(!motion)(EnterTransition.None togetherWith ExitTransition.None).using(null)
        else {
            if(targetState) {
                ((slideInVertically(tween(320,easing=FastOutSlowInEasing)){it}+fadeIn(tween(180))) togetherWith fadeOut(tween(140))).using(null)
            } else {
                (fadeIn(tween(200)) togetherWith (slideOutVertically(tween(280,easing=FastOutSlowInEasing)){it}+fadeOut(tween(220)))).using(null)
            }
        }
    },label="playback-queue-transition") {visibleQueue->
        if(visibleQueue)pages.SaveableStateProvider("playback-queue") {PlaybackQueuePage(vm)}
        else content()
    }
}
