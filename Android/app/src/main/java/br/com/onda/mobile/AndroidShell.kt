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
import androidx.compose.ui.graphics.drawscope.rotate

/** Small vector icons keep the shell independent of downloadable fonts. */
@Composable internal fun OndaIcon(name:String,description:String?=null,modifier:Modifier=Modifier,tint:Color=LocalContentColor.current) {
    val label=description?.let {translateUi(it)}
    Canvas(modifier.semantics {if(label!=null)contentDescription=label}) {
        val u=size.width/24f;val v=size.height/24f;val stroke=1.7f*u
        fun line(x:Float,y:Float,a:Float,b:Float)=drawLine(tint,Offset(x*u,y*v),Offset(a*u,b*v),stroke,StrokeCap.Round)
        fun path(vararg points:Pair<Float,Float>,close:Boolean=false) {drawPath(Path().apply {points.forEachIndexed {i,p->if(i==0)moveTo(p.first*u,p.second*v) else lineTo(p.first*u,p.second*v)};if(close)close()},tint,style=Stroke(stroke,cap=StrokeCap.Round))}
        when(name) {
            "close"->{line(6f,6f,18f,18f);line(18f,6f,6f,18f)}
            "shuffle"->{path(3f to 6f,7f to 6f,17f to 18f,21f to 18f);path(3f to 18f,7f to 18f,17f to 6f,21f to 6f);path(18f to 3f,21f to 6f,18f to 9f);path(18f to 15f,21f to 18f,18f to 21f)}
            "share"->{line(6f,12f,18f,5f);line(6f,12f,18f,19f);listOf(6f to 12f,18f to 5f,18f to 19f).forEach {(x,y)->drawCircle(tint,3f*u,Offset(x*u,y*v),style=Stroke(stroke))}}
            "mini"->{path(3f to 4f,21f to 4f,21f to 20f,3f to 20f,close=true);path(12f to 12f,19f to 12f,19f to 18f,12f to 18f,close=true)}
            "queue"->{for(y in listOf(5f,12f,19f)){drawCircle(tint,1f*u,Offset(3*u,y*v));line(7f,y,21f,y)}}
            "expand"->{path(3f to 9f,3f to 3f,9f to 3f);path(15f to 3f,21f to 3f,21f to 9f);path(21f to 15f,21f to 21f,15f to 21f);path(9f to 21f,3f to 21f,3f to 15f)}
            "search"->{drawCircle(tint,7*u,Offset(10*u,10*v),style=Stroke(stroke));line(15f,15f,21f,21f)}
            "download"->{line(12f,3f,12f,16f);path(7f to 11f,12f to 16f,17f to 11f);path(4f to 18f,4f to 21f,20f to 21f,20f to 18f)}
            "play"->path(7f to 4f,20f to 12f,7f to 20f,close=true)
            "pause"->{line(8f,5f,8f,19f);line(16f,5f,16f,19f)}
            "microphone"->rotate(45f) {
                val micStroke=Stroke(1.4f*u,cap=StrokeCap.Round,join=androidx.compose.ui.graphics.StrokeJoin.Round)
                drawOval(tint,Offset(6.5f*u,2*v),androidx.compose.ui.geometry.Size(11*u,10*v),style=micStroke)
                drawLine(tint,Offset(7*u,7*v),Offset(17*u,7*v),1.4f*u,StrokeCap.Round)
                drawPath(Path().apply {moveTo(9*u,12*v);lineTo(10*u,21*v);lineTo(14*u,21*v);lineTo(15*u,12*v)},tint,style=micStroke)
            }
            "stop"->drawRect(tint,Offset(6*u,6*v),androidx.compose.ui.geometry.Size(12*u,12*v),style=Stroke(stroke))
            "more-vertical"->listOf(5f,12f,19f).forEach {drawCircle(tint,1.5f*u,Offset(12*u,it*v))}
            "more"->listOf(5f,12f,19f).forEach {drawCircle(tint,1.5f*u,Offset(it*u,12*v))}
            "add"->{line(12f,4f,12f,20f);line(4f,12f,20f,12f)}
            "next"->{path(6f to 5f,16f to 12f,6f to 19f,close=true);line(19f,5f,19f,19f)}
            "previous"->{path(18f to 5f,8f to 12f,18f to 19f,close=true);line(5f,5f,5f,19f)}
            "paste"->{path(8f to 5f,4f to 5f,4f to 22f,20f to 22f,20f to 5f,16f to 5f);path(8f to 2f,16f to 2f,16f to 7f,8f to 7f,close=true)}
            "back"->path(15f to 4f,7f to 12f,15f to 20f)
            "up"->path(5f to 15f,12f to 8f,19f to 15f)
            "down"->path(5f to 9f,12f to 16f,19f to 9f)
            "check"->path(5f to 12f,10f to 17f,20f to 6f)
            "chevron"->path(9f to 5f,16f to 12f,9f to 19f)
            "image"->{path(3f to 3f,21f to 3f,21f to 21f,3f to 21f,close=true);path(3f to 18f,10f to 11f,15f to 16f,18f to 13f,21f to 16f);drawCircle(tint,2*u,Offset(16*u,8*v),style=Stroke(stroke))}
            "convert"->{line(3f,7f,21f,7f);path(17f to 3f,21f to 7f,17f to 11f);line(21f,17f,3f,17f);path(7f to 13f,3f to 17f,7f to 21f)}
            "tag"->path(3f to 12f,12f to 3f,21f to 3f,21f to 12f,12f to 21f,3f to 12f)
            "timer"->{drawCircle(tint,8*u,Offset(12*u,14*v),style=Stroke(stroke));line(9f,2f,15f,2f);line(12f,2f,12f,6f);line(12f,14f,12f,9f);line(18f,7f,20f,5f)}
            "history"->{drawCircle(tint,9*u,center,style=Stroke(stroke));path(12f to 6f,12f to 12f,17f to 14f)}
            "album"->{path(4f to 6f,20f to 6f,20f to 22f,4f to 22f,close=true);line(7f,2f,17f,2f);drawCircle(tint,4*u,Offset(12*u,14*v),style=Stroke(stroke))}
            "equalizer"->{line(5f,3f,5f,21f);line(12f,3f,12f,21f);line(19f,3f,19f,21f);drawCircle(tint,2.5f*u,Offset(5*u,8*v));drawCircle(tint,2.5f*u,Offset(12*u,16*v));drawCircle(tint,2.5f*u,Offset(19*u,10*v))}
            "appearance"->{
                val palette=Path().apply {
                    moveTo(12*u,3*v)
                    cubicTo(6*u,3*v,2*u,7*v,2*u,12*v)
                    cubicTo(2*u,18*v,7*u,22*v,12*u,22*v)
                    cubicTo(15*u,22*v,16*u,20*v,14*u,18*v)
                    cubicTo(13*u,16*v,15*u,15*v,18*u,15*v)
                    cubicTo(24*u,15*v,23*u,3*v,12*u,3*v)
                    close()
                }
                drawPath(palette,tint,style=Stroke(stroke,join=androidx.compose.ui.graphics.StrokeJoin.Round))
                listOf(7f to 9f,12f to 7f,17f to 9f,7f to 14f).forEach {(x,y)->drawCircle(tint,1.3f*u,Offset(x*u,y*v))}
            }
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

@Composable internal fun OndaAppBar(onAppearance:()->Unit,onSettings:()->Unit) {
    val accent=MaterialTheme.colorScheme.primary
    Row(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal=24.dp,vertical=8.dp),verticalAlignment=Alignment.CenterVertically) {
        OndaBrandMark(Modifier.size(44.dp,36.dp),accent)
        Text("ONDA",Modifier.weight(1f).padding(start=10.dp),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold,color=accent)
        IconButton(onClick=onAppearance,modifier=Modifier.testTag("open-appearance")){OndaIcon("appearance","Aparência",Modifier.size(25.dp))}
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
    val updates=remember(vm){vm.jukebox.state.map {it.copy(index=0,phase=0f,flow=emptyList(),used=emptySet(),elapsed=0.0,jumps=0,nextIndex=-1,jumpBlend=0f)}.distinctUntilChanged()}
    val initialState=remember(vm){vm.jukebox.state.value}
    val state by updates.collectAsStateWithLifecycle(initialValue=initialState)
    val queuedTracks by vm.jukebox.playbackQueue.collectAsStateWithLifecycle()
    val currentQueueId by vm.jukebox.currentQueueId.collectAsStateWithLifecycle()
    val volume by vm.jukebox.volume.collectAsStateWithLifecycle()
    if(state.model==null || !state.playing)return
    var showEqualizer by rememberSaveable {mutableStateOf(false)}
    if(showEqualizer)JukeboxEqualizerDialog {showEqualizer=false}
    val model=state.model
    val embedded=model?.optString("media_cover").orEmpty()
    val cover=remember(embedded,model?.optString("cover_url")){if(embedded.isNotBlank())runCatching {android.util.Base64.decode(embedded,android.util.Base64.DEFAULT)}.getOrNull() else model?.optString("cover_url")}
    var controls by remember {mutableStateOf(false)}
    var timers by remember {mutableStateOf(false)}
    var showQueue by remember {mutableStateOf(false)}
    if(timers)JukeboxTimerDialog(vm.jukebox){timers=false}
    if(showQueue)JukeboxQueueDialog(vm.jukebox,vm){showQueue=false}
    Surface(Modifier.fillMaxWidth().padding(horizontal=LayoutSpacing.inset,vertical=LayoutSpacing.details).testTag("jukebox-miniplayer"),shape=RoundedCornerShape(16.dp),color=MaterialTheme.colorScheme.surfaceContainer) {
        Column {
        Row(Modifier.clickable(onClick=onOpen).padding(LayoutSpacing.controls),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
            AsyncImage(cover,translateUi("Capa do álbum"),Modifier.size(48.dp).clip(RoundedCornerShape(8.dp)),contentScale=ContentScale.Crop)
            Column(Modifier.weight(1f)) {Text(state.title,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.labelLarge);Text(model?.optString("media_artist").orEmpty(),maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
        }
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceEvenly) {
            JukeboxLyricsButton(vm)
            IconButton(onClick=vm.jukebox::previousTrack){OndaIcon("previous","Retroceder",Modifier.size(23.dp))}
            IconButton(onClick=vm.jukebox::playPause){OndaIcon(if(state.paused)"play" else "pause",if(state.paused)"Retomar" else "Pausar",Modifier.size(23.dp))}
            IconButton(onClick=vm.jukebox::nextTrack,enabled=vm.jukebox.nextQueueIndex<queuedTracks.size&&!state.busy,modifier=Modifier.testTag("miniplayer-next-song")){OndaIcon("next","Próxima música",Modifier.size(23.dp))}
            Box {
                IconButton(onClick={controls=true}){OndaIcon("more","Controles da reprodução",Modifier.size(23.dp))}
                DropdownMenu(controls,{controls=false}) {
                    DropdownMenuItem(text={UiText("Parar")},onClick={controls=false;vm.jukebox.stop()})
                    DropdownMenuItem(text={UiText("Equalizador")},onClick={controls=false;showEqualizer=true})
                    DropdownMenuItem(text={UiText("Timer")},onClick={controls=false;timers=true})
                    DropdownMenuItem(text={UiText("Fila de reprodução")},onClick={controls=false;showQueue=true})
                    Row(Modifier.width(220.dp).padding(horizontal=12.dp),verticalAlignment=Alignment.CenterVertically) {
                        UiText("Volume",style=MaterialTheme.typography.labelSmall)
                        RoundSlider(volume,vm.jukebox::setVolume,slim=true,modifier=Modifier.weight(1f).a11yLabel("Volume"))
                    }
                }
            }
        }
        }
    }
}

@Composable internal fun MorePage(tabs:JSONArray,onNavigate:(String)->Unit,onYouTube:()->Unit,onLicenses:()->Unit,onFailures:()->Unit) {
    val visible=remember(tabs.toString()){(0 until tabs.length()).map {tabs.optString(it)}}
    LazyColumn(Modifier.fillMaxSize().testTag("more-list").padding(horizontal=24.dp),verticalArrangement=Arrangement.spacedBy(12.dp),contentPadding=PaddingValues(bottom=24.dp)) {
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
