package br.com.onda.mobile

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.gestures.*
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.boundsInRoot
import androidx.compose.ui.layout.positionInRoot
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/** Small vector icons keep the shell independent of downloadable fonts. */
@Composable internal fun OndaIcon(name:String,description:String?=null,modifier:Modifier=Modifier,tint:Color=LocalContentColor.current) {
    val label=description?.let {translateUi(it)}
    Canvas(modifier.semantics {if(label!=null)contentDescription=label}) {
        val u=size.width/24f;val v=size.height/24f;val stroke=1.7f*u
        fun line(x:Float,y:Float,a:Float,b:Float)=drawLine(tint,Offset(x*u,y*v),Offset(a*u,b*v),stroke,StrokeCap.Round)
        fun path(vararg points:Pair<Float,Float>,close:Boolean=false) {drawPath(Path().apply {points.forEachIndexed {i,p->if(i==0)moveTo(p.first*u,p.second*v) else lineTo(p.first*u,p.second*v)};if(close)close()},tint,style=Stroke(stroke,cap=StrokeCap.Round))}
        when(name) {
            "search"->{drawCircle(tint,7*u,Offset(10*u,10*v),style=Stroke(stroke));line(15f,15f,21f,21f)}
            "download"->{line(12f,3f,12f,16f);path(7f to 11f,12f to 16f,17f to 11f);path(4f to 18f,4f to 21f,20f to 21f,20f to 18f)}
            "play"->path(7f to 4f,20f to 12f,7f to 20f,close=true)
            "pause"->{line(8f,5f,8f,19f);line(16f,5f,16f,19f)}
            "stop"->drawRect(tint,Offset(6*u,6*v),androidx.compose.ui.geometry.Size(12*u,12*v))
            "more-vertical"->listOf(5f,12f,19f).forEach {drawCircle(tint,1.5f*u,Offset(12*u,it*v))}
            "more"->listOf(5f,12f,19f).forEach {drawCircle(tint,1.5f*u,Offset(it*u,12*v))}
            "add"->{line(12f,4f,12f,20f);line(4f,12f,20f,12f)}
            "next"->{path(6f to 5f,16f to 12f,6f to 19f,close=true);line(19f,5f,19f,19f)}
            "previous"->{path(18f to 5f,8f to 12f,18f to 19f,close=true);line(5f,5f,5f,19f)}
            "check"->path(5f to 12f,10f to 17f,20f to 6f)
            "chevron"->path(9f to 5f,16f to 12f,9f to 19f)
            "image"->{path(3f to 3f,21f to 3f,21f to 21f,3f to 21f,close=true);path(3f to 18f,10f to 11f,15f to 16f,18f to 13f,21f to 16f);drawCircle(tint,2*u,Offset(16*u,8*v),style=Stroke(stroke))}
            "convert"->{line(3f,7f,21f,7f);path(17f to 3f,21f to 7f,17f to 11f);line(21f,17f,3f,17f);path(7f to 13f,3f to 17f,7f to 21f)}
            "tag"->path(3f to 12f,12f to 3f,21f to 3f,21f to 12f,12f to 21f,3f to 12f)
            "timer"->{drawCircle(tint,8*u,Offset(12*u,14*v),style=Stroke(stroke));line(9f,2f,15f,2f);line(12f,2f,12f,6f);line(12f,14f,12f,9f);line(18f,7f,20f,5f)}
            "history"->{drawCircle(tint,9*u,center,style=Stroke(stroke));path(12f to 6f,12f to 12f,17f to 14f)}
            "album"->{path(4f to 6f,20f to 6f,20f to 22f,4f to 22f,close=true);line(7f,2f,17f,2f);drawCircle(tint,4*u,Offset(12*u,14*v),style=Stroke(stroke))}
            "equalizer"->{line(5f,3f,5f,21f);line(12f,3f,12f,21f);line(19f,3f,19f,21f);drawCircle(tint,2.5f*u,Offset(5*u,8*v));drawCircle(tint,2.5f*u,Offset(12*u,16*v));drawCircle(tint,2.5f*u,Offset(19*u,10*v))}
            "settings"->{
                val gear=Path().apply {
                    for(tooth in 0 until 8) {
                        val angles=listOf(-22.5,-14.0,-10.0,10.0,14.0)
                        val radii=listOf(7.5,7.5,10.0,10.0,7.5)
                        angles.forEachIndexed {point,angle->
                            val radians=Math.toRadians(tooth*45.0+angle)
                            val x=(12+radii[point]*kotlin.math.cos(radians)).toFloat()*u
                            val y=(12+radii[point]*kotlin.math.sin(radians)).toFloat()*v
                            if(tooth==0 && point==0)moveTo(x,y) else lineTo(x,y)
                        }
                    }
                    close()
                }
                drawPath(gear,tint,style=Stroke(stroke,join=androidx.compose.ui.graphics.StrokeJoin.Round))
                drawCircle(tint,3*u,center,style=Stroke(stroke))
            }
            else->{line(5f,6f,19f,6f);line(5f,12f,19f,12f);line(5f,18f,19f,18f)}
        }
    }
}

@Composable internal fun OndaAppBar(onSettings:()->Unit) {
    val accent=MaterialTheme.colorScheme.primary
    Row(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal=24.dp,vertical=8.dp),verticalAlignment=Alignment.CenterVertically) {
        Canvas(Modifier.size(44.dp,36.dp)) {
            val path=Path();val points=80
            for(i in 0..points){val x=i.toFloat()/points;val envelope=kotlin.math.sin(x*Math.PI).toFloat();val y=.5f+kotlin.math.sin(x*8*Math.PI).toFloat()*envelope*.46f;if(i==0)path.moveTo(x*size.width,y*size.height) else path.lineTo(x*size.width,y*size.height)}
            drawPath(path,accent,style=Stroke(2.7.dp.toPx(),cap=StrokeCap.Round))
        }
        Text("ONDA",Modifier.weight(1f).padding(start=10.dp),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold,color=accent)
        IconButton(onClick=onSettings,modifier=Modifier.testTag("open-settings")){OndaIcon("settings","Configurações",Modifier.size(25.dp))}
    }
}

internal fun mainDestinations(tabs:JSONArray,order:List<String> = bottomBarDefaults)=bottomBarDestinations(order,(0 until tabs.length()).any {tabs.optString(it)=="Efeitos"})

private val LocalPageSwipeExclusions=staticCompositionLocalOf<MutableMap<Any,LayoutCoordinates>?> {null}

@Composable internal fun Modifier.pageSwipeExclusion():Modifier {
    val registry=LocalPageSwipeExclusions.current
    val identity=remember {Any()}
    DisposableEffect(registry) {onDispose {registry?.remove(identity)}}
    return if(registry==null)this else onGloballyPositioned {registry[identity]=it}
}

/** Native sliders keep the complete gesture when a touch starts inside them. */
@Composable internal fun SwipePageHost(current:String,pages:List<String>,onNavigate:(String)->Unit,modifier:Modifier=Modifier,content:@Composable ()->Unit) {
    val scope=rememberCoroutineScope()
    val incoming=remember {Animatable(0f)}
    val exclusions=remember {mutableMapOf<Any,LayoutCoordinates>()}
    var origin by remember {mutableStateOf(Offset.Zero)}
    var dragging by remember {mutableStateOf(false)}
    var distance by remember {mutableFloatStateOf(0f)}
    val latestCurrent by rememberUpdatedState(current)
    val latestNavigate by rememberUpdatedState(onNavigate)
    val threshold=with(LocalDensity.current){64.dp.toPx()}
    val touchMargin=with(LocalDensity.current){24.dp.toPx()}
    Box(modifier.clipToBounds().testTag("page-swipe").onGloballyPositioned {origin=it.positionInRoot()}.pointerInput(pages,threshold,touchMargin) {
        awaitEachGesture {
            val down=awaitFirstDown(requireUnconsumed=false)
            val rootTouch=down.position+origin
            if(exclusions.values.any {it.isAttached && it.boundsInRoot().inflate(touchMargin).contains(rootTouch)})return@awaitEachGesture
            val startIndex=pages.indexOf(if(latestCurrent=="Links e fila")"Fila" else latestCurrent).let {if(it<0)pages.lastIndex else it}
            distance=0f
            val slop=awaitHorizontalTouchSlopOrCancellation(down.id) {change,over->change.consume();distance=over}
            if(slop!=null) {
                dragging=true
                val released=horizontalDrag(slop.id) {change->distance+=change.positionChange().x;change.consume()}
                val delta=if(released && distance < -threshold)1 else if(released && distance > threshold)-1 else 0
                val next=(startIndex+delta).coerceIn(0,pages.lastIndex)
                val width=size.width.toFloat()
                scope.launch {
                    if(next!=startIndex){incoming.snapTo(if(delta>0)width else -width);latestNavigate(pages[next])}
                    else incoming.snapTo(distance.coerceIn(-width*.4f,width*.4f))
                    dragging=false;distance=0f
                    incoming.animateTo(0f,tween(200))
                }
            }
        }
    }) {
        CompositionLocalProvider(LocalPageSwipeExclusions provides exclusions) {
            Box(Modifier.fillMaxSize().graphicsLayer {translationX=if(dragging)distance.coerceIn(-size.width*.4f,size.width*.4f) else incoming.value}) {content()}
        }
    }
}

@Composable internal fun OndaBottomNavigation(tab:String,tabs:JSONArray,onNavigate:(String)->Unit) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val destinations=mainDestinations(tabs,bottomBarOrder(settings))
    val selected=when(tab){"Pesquisar"->"Pesquisar";"Fila","Links e fila"->"Fila";"Efeitos"->"Efeitos";else->"Mais"}
    NavigationBar(containerColor=MaterialTheme.colorScheme.background,tonalElevation=0.dp) {
        destinations.forEach {key->
            val (label,icon)=when(key){"Pesquisar"->"Pesquisar" to "search";"Fila"->"Downloads" to "download";"Efeitos"->"Reprodução" to "play";else->"Mais" to "more"}
            NavigationBarItem(selected=selected==key,onClick={onNavigate(key)},modifier=Modifier.testTag("nav-$key"),icon={OndaIcon(icon,modifier=Modifier.size(23.dp))},label={UiText(label,style=MaterialTheme.typography.labelSmall,maxLines=1)},colors=NavigationBarItemDefaults.colors(indicatorColor=MaterialTheme.colorScheme.primary,selectedIconColor=MaterialTheme.colorScheme.onPrimary,selectedTextColor=MaterialTheme.colorScheme.primary))
        }
    }
}

@Composable internal fun OndaMiniPlayer(vm:OndaViewModel,onOpen:()->Unit) {
    val updates=remember(vm){vm.jukebox.state.map {it.copy(index=0,phase=0f,flow=emptyList(),elapsed=0.0,jumps=0,nextIndex=-1,jumpBlend=0f)}.distinctUntilChanged()}
    val state by updates.collectAsStateWithLifecycle(initialValue=vm.jukebox.state.value)
    if(state.model==null || !state.playing)return
    var showEqualizer by rememberSaveable {mutableStateOf(false)}
    if(showEqualizer)JukeboxEqualizerDialog {showEqualizer=false}
    val model=state.model
    val embedded=model?.optString("media_cover").orEmpty()
    val cover=remember(embedded,model?.optString("cover_url")){if(embedded.isNotBlank())runCatching {android.util.Base64.decode(embedded,android.util.Base64.DEFAULT)}.getOrNull() else model?.optString("cover_url")}
    Surface(Modifier.fillMaxWidth().padding(horizontal=12.dp,vertical=4.dp).testTag("jukebox-miniplayer"),shape=RoundedCornerShape(16.dp),color=MaterialTheme.colorScheme.surfaceContainer) {
        Row(Modifier.clickable(onClick=onOpen).padding(10.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(4.dp)) {
            AsyncImage(cover,translateUi("Capa do álbum"),Modifier.size(48.dp).clip(RoundedCornerShape(8.dp)),contentScale=ContentScale.Crop)
            Column(Modifier.weight(1f)) {Text(state.title,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.labelLarge);Text(model?.optString("media_artist").orEmpty(),maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
            IconButton(onClick={showEqualizer=true}){OndaIcon("equalizer","Equalizador",Modifier.size(23.dp))}
            IconButton(onClick=vm.jukebox::playPause){OndaIcon(if(state.paused)"play" else "pause",if(state.paused)"Retomar" else "Pausar",Modifier.size(23.dp))}
            IconButton(onClick={val current=vm.jukebox.state.value;val count=current.model?.optJSONArray("neighbors")?.length() ?: 1;vm.jukebox.seek((current.index+1)%count)}){OndaIcon("next","Próximo trecho",Modifier.size(23.dp))}
        }
    }
}

@Composable internal fun MorePage(tabs:JSONArray,onNavigate:(String)->Unit,onYouTube:()->Unit,onLicenses:()->Unit,onFailures:()->Unit) {
    val visible=remember(tabs.toString()){(0 until tabs.length()).map {tabs.optString(it)}}
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=24.dp),verticalArrangement=Arrangement.spacedBy(12.dp),contentPadding=PaddingValues(bottom=24.dp)) {
        item {PageTitle("Mais","Todas as ferramentas do ONDA")}
        for((heading,keys) in listOf("Ferramentas" to listOf("Imagens","Conversor de vídeos","Metadados"),"Biblioteca" to listOf("Playlists / Álbuns","Histórico"))) {
            val shown=visible.filter {it in keys}
            if(shown.isNotEmpty())item {UiText(heading.uppercase(),style=MaterialTheme.typography.labelLarge,color=MaterialTheme.colorScheme.onSurfaceVariant,modifier=Modifier.padding(top=12.dp,bottom=4.dp))}
            items(shown,key={it}) {name->
                val (icon,detail)=when(name){"Imagens"->"image" to "Baixe e converta imagens";"Conversor de vídeos"->"convert" to "Converta áudio e vídeo";"Metadados"->"tag" to "Edite informações, capa e letras";"Playlists / Álbuns"->"album" to "Importe e organize suas coleções";else->"history" to "Consulte seus downloads anteriores"}
                MoreRow(tabLabel(name),detail,icon){onNavigate(name)}
            }
        }
        item {UiText("Aplicativo",style=MaterialTheme.typography.labelLarge,color=MaterialTheme.colorScheme.onSurfaceVariant,modifier=Modifier.padding(top=12.dp))}
        item {MoreRow("Sessão do YouTube","","play",onYouTube)}
        item {MoreRow("Falhas da fila","","download",onFailures)}
        item {MoreRow("Licenças e fontes","","more",onLicenses)}
        item {UiText("ONDA Android ${BuildConfig.VERSION_NAME}",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
    }
}
@Composable private fun MoreRow(title:String,detail:String,icon:String,onClick:()->Unit) {
    Surface(onClick=onClick,shape=RoundedCornerShape(18.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,modifier=Modifier.fillMaxWidth().testTag("more-$title")) {
        Row(Modifier.padding(18.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(16.dp)) {
            Surface(shape=RoundedCornerShape(12.dp),color=MaterialTheme.colorScheme.surfaceContainerHigh){Box(Modifier.size(48.dp),contentAlignment=Alignment.Center){OndaIcon(icon,modifier=Modifier.size(27.dp))}}
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)){UiText(title,style=MaterialTheme.typography.titleMedium);if(detail.isNotBlank())UiText(detail,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
            OndaIcon("chevron",modifier=Modifier.size(18.dp))
        }
    }
}

@Composable internal fun DownloadsHome(vm:OndaViewModel) {
    var completed by rememberSaveable {mutableStateOf(false)}
    var advanced by rememberSaveable {mutableStateOf(false)}
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val queue by OndaStore.items.collectAsStateWithLifecycle()
    val running by OndaStore.running.collectAsStateWithLifecycle()
    var menu by remember {mutableStateOf(false)}
    Column(Modifier.fillMaxSize().padding(horizontal=24.dp)) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
            UiText("Downloads",Modifier.weight(1f),style=MaterialTheme.typography.headlineMedium,fontWeight=FontWeight.Bold)
            DownloadCardSizeControl(settings,compact=true)
            Box {IconButton(onClick={menu=true}){OndaIcon("more","Mais ações",Modifier.size(24.dp))};DropdownMenu(menu,{menu=false}) {
                DropdownMenuItem(text={UiText(if(advanced)"Visualização simples" else "Gerenciar fila")},onClick={advanced=!advanced;menu=false})
                DropdownMenuItem(text={UiText("Baixar fila")},enabled=queue.any {it.state=="Pendente"},onClick={DownloadService.start(OndaStore.context);menu=false})
                DropdownMenuItem(text={UiText(if(DownloadRuntime.paused)"Retomar fila" else "Pausar fila")},enabled=running,onClick={DownloadService.control(OndaStore.context,if(DownloadRuntime.paused)"resume" else "pause");menu=false})
                DropdownMenuItem(text={UiText("Cancelar fila")},enabled=running,onClick={DownloadService.stop(OndaStore.context);menu=false})
            }}
        }
        if(advanced){QueuePage(vm);return@Column}
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth().padding(vertical=16.dp)) {
            listOf("Em andamento","Concluídos").forEachIndexed {i,label->SegmentedButton(selected=completed==(i==1),onClick={completed=i==1},shape=RoundedCornerShape(12.dp),icon={},colors=SegmentedButtonDefaults.colors(activeContainerColor=MaterialTheme.colorScheme.primary,activeContentColor=MaterialTheme.colorScheme.onPrimary)){UiText(label)}}
        }
        val finished=queue.filter {it.state=="Concluído"}
        val shown=if(completed)finished else queue.filter {it.state!="Concluído"}
        LazyColumn(verticalArrangement=Arrangement.spacedBy(12.dp),contentPadding=PaddingValues(bottom=96.dp)) {
            if(shown.isEmpty() && (completed || finished.isEmpty()))item {UiText(if(completed)"Nenhum download concluído" else "Nenhum download na fila",style=MaterialTheme.typography.titleMedium,modifier=Modifier.padding(top=24.dp));UiText("Use + para adicionar links ou encontre músicas na pesquisa.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
            items(shown,key={it.id}) {item->DownloadSummaryCard(item,vm,settings)}
            if(!completed && finished.isNotEmpty()) {
                item {UiText("Concluídos",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=12.dp,bottom=4.dp))}
                items(finished.takeLast(3),key={it.id}) {item->DownloadSummaryCard(item,vm,settings)}
            }
        }
    }
}
@Composable private fun DownloadSummaryCard(item:DownloadItem,vm:OndaViewModel,settings:JSONObject) {
    var menu by remember {mutableStateOf(false)}
    val complete=settings.optString("queue_view","Completa")=="Completa"
    val cardSize=settings.optString("queue_card_size","Grande")
    val coverSide=when(cardSize){"Pequeno"->56.dp;"Médio"->80.dp;else->100.dp}
    val cardPadding=when(cardSize){"Pequeno"->10.dp;"Médio"->12.dp;else->16.dp}
    LaunchedEffect(item.id,complete){if(complete && item.config.optJSONObject("queue_info")==null)vm.loadQueueInformation(item)}
    val info=item.config.optJSONObject("queue_info") ?: item.config.optJSONObject("catalog_record")
    val artists=info?.optJSONArray("artists")?.let {a->(0 until a.length()).joinToString(", "){a.optString(it)}}.orEmpty()
    Surface(shape=RoundedCornerShape(18.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,modifier=Modifier.fillMaxWidth().testTag("download-summary-${item.id}")) {
        Row(Modifier.padding(cardPadding).heightIn(min=if(complete)coverSide else 40.dp),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalAlignment=Alignment.CenterVertically) {
            if(complete)Box(Modifier.size(coverSide).clip(RoundedCornerShape(10.dp)),contentAlignment=Alignment.Center){if(info?.cleanString("cover_url").isNullOrBlank())OndaIcon("album",modifier=Modifier.size(32.dp)) else AsyncImage(info?.cleanString("cover_url"),translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Crop)}
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                Text(songCardTitle(info?.cleanString("title")?.ifBlank {item.title} ?: item.title,artists),fontWeight=FontWeight.Medium,maxLines=if(cardSize=="Pequeno")1 else 2,overflow=TextOverflow.Ellipsis,style=if(cardSize=="Pequeno")MaterialTheme.typography.bodyMedium else if(cardSize=="Médio")MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleSmall)
                if(complete && artists.isNotBlank())Text(artists,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                if(item.state in listOf("Baixando","Aguardando escolha"))Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    LinearProgressIndicator(progress={item.progress/100},modifier=Modifier.weight(1f).height(4.dp),strokeCap=StrokeCap.Round,drawStopIndicator={})
                    Text("${item.progress.toInt()}%",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if(item.state !in listOf("Baixando","Aguardando escolha"))UiText(item.state,style=MaterialTheme.typography.labelSmall,color=if(item.state=="Erro")MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if(item.state=="Concluído")Surface(shape=RoundedCornerShape(50),color=MaterialTheme.colorScheme.primary) {Box(Modifier.size(28.dp),contentAlignment=Alignment.Center){OndaIcon("check","Concluído",Modifier.size(17.dp),tint=MaterialTheme.colorScheme.onPrimary)}}
            Box {IconButton(onClick={menu=true}){OndaIcon("more","Mais ações",Modifier.size(21.dp))};DropdownMenu(menu,{menu=false}) {
                DropdownMenuItem(text={UiText("Baixar agora")},enabled=item.state=="Pendente",onClick={DownloadService.start(OndaStore.context,item.id);menu=false})
                DropdownMenuItem(text={UiText("Tentar novamente")},enabled=item.state in listOf("Erro","Cancelado"),onClick={OndaStore.retry(setOf(item.id));menu=false})
                DropdownMenuItem(text={UiText("Remover")},enabled=item.state !in listOf("Baixando","Aguardando escolha"),onClick={OndaStore.remove(setOf(item.id));menu=false})
                DropdownMenuItem(text={UiText("Ver detalhes")},onClick={vm.showNotice(item.title,item.message.ifBlank {item.state});menu=false})
            }}
        }
    }
}
