package br.com.onda.mobile

import android.util.Base64
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage

/** One compact player across navigation; expanding never transfers audio between tabs. */
@Composable internal fun AndroidPlaybackSurface(vm:OndaViewModel,queueIsVisible:Boolean=false) {
    val remote by RemotePlaybackRuntime.state.collectAsStateWithLifecycle()
    if(remote.connected){RemotePlaybackSurface(remote,vm,queueIsVisible);return}
    val mode by vm.playbackMode.collectAsStateWithLifecycle()
    val fxSource by vm.effectsSource.collectAsStateWithLifecycle()
    val infos by vm.effectsInfo.collectAsStateWithLifecycle()
    val fxMedia by EffectsPlaybackRuntime.state.collectAsStateWithLifecycle()
    val fxPosition by vm.effectsPosition.collectAsStateWithLifecycle()
    val fxPreparing by vm.effectsPreparing.collectAsStateWithLifecycle()
    val fxEnabled by vm.effectsPreviewEnabled.collectAsStateWithLifecycle()
    val fxQueue by vm.effectsPlaylist.collectAsStateWithLifecycle()
    val juke by vm.jukebox.state.collectAsStateWithLifecycle()
    val jukeQueue by vm.jukebox.playbackQueue.collectAsStateWithLifecycle()
    var expanded by rememberSaveable {mutableStateOf(false)}
    var expandedQueue by rememberSaveable {mutableStateOf(false)}
    var devices by remember {mutableStateOf(false)}
    LaunchedEffect(expanded){if(!expanded)expandedQueue=false}
    var expandedJukebox by rememberSaveable {mutableStateOf(false)}
    var lastJukebox by rememberSaveable(mode,fxSource,juke.model?.optString("source")) {mutableStateOf(mode==1&&juke.model!=null)}
    LaunchedEffect(juke.playing,juke.paused,fxMedia?.playing,fxPreparing) {
        if(juke.playing&&!juke.paused)lastJukebox=true
        else if(fxMedia?.playing==true||fxPreparing)lastJukebox=false
    }
    val useJukebox=true
    val model=juke.model
    val source=if(useJukebox)model?.optString("source").orEmpty() else fxSource
    SideEffect {vm.compactPlaybackMode.value=if(source.isBlank())null else if(useJukebox)1 else 0}
    DisposableEffect(vm){onDispose {vm.compactPlaybackMode.value=null}}
    if(source.isBlank())return
    val localExpandedRequested by RemotePlaybackRuntime.localExpandedRequested.collectAsStateWithLifecycle()
    LaunchedEffect(localExpandedRequested) {
        if(localExpandedRequested){expanded=true;RemotePlaybackRuntime.localExpandedRequested.value=false}
    }
    val info=infos[fxSource]
    val record=info?.optJSONObject("record")
    val title=if(useJukebox)juke.title else record?.optString("title")?.ifBlank {importedAudioName(source)} ?: importedAudioName(source)
    val artist=if(useJukebox)model?.optString("media_artist").orEmpty() else record?.stringList("artists").orEmpty()
    val encoded=if(useJukebox)model?.optString("media_cover").orEmpty() else info?.optString("cover").orEmpty()
    val coverUrl=if(useJukebox)model?.optString("cover_url") else info?.optJSONObject("record")?.optString("cover_url")
    val artwork=remember(encoded,coverUrl,useJukebox) {
        if(encoded.isNotBlank())runCatching {Base64.decode(encoded,Base64.DEFAULT)}.getOrNull()
        else coverUrl?.takeIf {it.isNotBlank()}
    }
    val beats=model?.optJSONArray("beats")
    val beatStart=beats?.optDouble(juke.index,0.0) ?: 0.0
    val beatEnd=beats?.optDouble(juke.index+1,beatStart) ?: beatStart
    val position=if(useJukebox)beatStart+(beatEnd-beatStart)*juke.phase else fxPosition
    val duration=(if(useJukebox)model?.optDouble("duration",0.0) ?: 0.0 else info?.optDouble("duration",0.0) ?: fxMedia?.duration ?: 0.0).coerceAtLeast(0.0)
    val preparing=if(useJukebox)juke.busy else fxPreparing
    val playing=if(useJukebox)juke.playing&&!juke.paused else fxEnabled
    val fxRepeat by vm.effectsRepeat.collectAsStateWithLifecycle()
    val fxShuffle by vm.effectsShuffle.collectAsStateWithLifecycle()
    val jukeRepeat by vm.jukebox.queueRepeat.collectAsStateWithLifecycle()
    val jukeShuffle by vm.jukebox.queueShuffle.collectAsStateWithLifecycle()
    val hasNext=if(useJukebox)(vm.jukebox.nextQueueIndex<jukeQueue.size || jukeRepeat=="Todas" && jukeQueue.isNotEmpty()) else (vm.effectsQueueIndex(source)+1<fxQueue.size || fxRepeat=="Todas" && fxQueue.isNotEmpty())
    var menu by remember {mutableStateOf(false)}
    var timer by remember {mutableStateOf(false)}
    var equalizer by remember {mutableStateOf(false)}
    var dragged by remember(source) {mutableStateOf<Float?>(null)}
    fun toggle(){if(useJukebox)vm.jukebox.playPause() else vm.mediaToggleEffects()}
    fun previous(){if(useJukebox)vm.jukebox.previousTrack() else vm.mediaPreviousEffects()}
    fun next(){if(useJukebox)vm.jukebox.nextTrack() else vm.mediaNextEffects()}
    fun seek(seconds:Double){
        if(useJukebox){if(beats!=null)vm.jukebox.seek((0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=seconds} ?: 0)}
        else vm.mediaSeekEffects(seconds)
    }
    fun openQueue(){
        if(useJukebox) {
            if(expanded)expandedQueue=!expandedQueue
            else if(queueIsVisible)vm.playbackQueueOpen.value=false
            else vm.openPlaybackQueue()
        } else vm.effectsQueueOpen.value=true
    }
    @Composable fun cover(modifier:Modifier){
        Surface(modifier.clip(RoundedCornerShape(12.dp)),color=MaterialTheme.colorScheme.surfaceContainerHighest) {
            if(artwork!=null)AsyncImage(artwork,translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Fit)
            else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(48.dp))}
        }
    }
    AlbumGlass(artwork,Modifier.fillMaxWidth().padding(horizontal=8.dp,vertical=4.dp).testTag("android-compact-player")) {glass->
        Column {
            Row(Modifier.fillMaxWidth().clickable {expandedJukebox=useJukebox;expanded=true}.testTag("compact-player-expand").padding(6.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                cover(Modifier.size(48.dp))
                Column(Modifier.weight(1f)) {
                    Text(title,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.labelLarge)
                    Text(artist,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,color=glass.secondary)
                }
                LyricsButton(vm,source,{position},duration,::seek,::toggle,isPlaying={playing},title=title,artist=artist)
                IconButton(onClick=::openQueue,modifier=Modifier.testTag("compact-player-queue"),colors=IconButtonDefaults.iconButtonColors(contentColor=if(queueIsVisible)MaterialTheme.colorScheme.primary else glass.ink)){OndaIcon("queue",if(queueIsVisible)"Fechar fila" else "Fila",Modifier.size(24.dp))}
                OutlinedIconButton(onClick=::toggle,enabled=duration>0,modifier=Modifier.testTag("compact-player-toggle"),border=BorderStroke(1.dp,MaterialTheme.colorScheme.primary),colors=IconButtonDefaults.outlinedIconButtonColors(contentColor=glass.ink,disabledContentColor=glass.ink.copy(alpha=if(glass.highContrast)1f else .38f))) {
                    if(preparing)CircularProgressIndicator(Modifier.size(23.dp),strokeWidth=2.dp,color=glass.ink)
                    else OndaIcon(if(playing)"pause" else "play",if(playing)"Pausar" else "Reproduzir",Modifier.size(26.dp))
                }
            }
            Row(Modifier.fillMaxWidth().padding(horizontal=10.dp,vertical=3.dp).testTag("compact-player-times"),horizontalArrangement=Arrangement.SpaceBetween) {
                Text(mediaClock(position.toLong()),style=MaterialTheme.typography.labelSmall,color=glass.secondary)
                Text(mediaClock(duration.toLong()),style=MaterialTheme.typography.labelSmall,color=glass.secondary)
            }
            LinearProgressIndicator(progress={if(duration>0)(position/duration).toFloat().coerceIn(0f,1f) else 0f},modifier=Modifier.fillMaxWidth().height(if(glass.highContrast)3.dp else 2.dp).testTag("compact-player-progress"),color=MaterialTheme.colorScheme.primary,trackColor=glass.ink.copy(alpha=if(glass.highContrast).4f else .18f))
        }
    }
    if(expanded)Dialog(onDismissRequest={expanded=false},properties=DialogProperties(usePlatformDefaultWidth=false)) {
        Surface(Modifier.fillMaxSize().testTag("android-expanded-player"),color=MaterialTheme.colorScheme.surface) {
            BoxWithConstraints(Modifier.fillMaxSize()) {
                val artworkSize=minOf(maxWidth-48.dp,maxHeight*.46f).coerceAtLeast(100.dp)
                Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                        IconButton(onClick={expanded=false}){OndaIcon("down","Recolher reprodução",Modifier.size(26.dp))}
                        Spacer(Modifier.weight(1f))
                        ShufflePlaybackButton(if(useJukebox)jukeShuffle else fxShuffle,{if(useJukebox)vm.jukebox.queueShuffle.value=it else vm.effectsShuffle.value=it})
                        RepeatPlaybackButton(jukeRepeat,{vm.jukebox.queueRepeat.value=it})
                        Box {
                            IconButton(onClick={menu=true}){OndaIcon("more-vertical","Mais",Modifier.size(24.dp))}
                            DropdownMenu(menu,{menu=false}) {
                                DropdownMenuItem(text={UiText("Parar")},onClick={menu=false;if(useJukebox)vm.jukebox.stop() else vm.stopEffectsPlayback()})
                                DropdownMenuItem(text={UiText("Ajustes de reprodução")},onClick={menu=false;expanded=false;vm.playbackMode.value=if(useJukebox)1 else 0;vm.effectsNavigation.value=true})
                                if(useJukebox){
                                    DropdownMenuItem(text={UiText("Reprodução normal")},leadingIcon={Checkbox(vm.jukebox.normal,null)},onClick={vm.jukebox.normal=!vm.jukebox.normal;menu=false})
                                    DropdownMenuItem(text={UiText("Timer")},onClick={menu=false;timer=true})
                                    DropdownMenuItem(text={UiText("Equalizador")},onClick={menu=false;equalizer=true})
                                }
                            }
                        }
                    }
                    cover(Modifier.size(artworkSize).align(Alignment.CenterHorizontally).testTag("expanded-album-cover"))
                    Column {Text(title,style=MaterialTheme.typography.headlineSmall);Text(artist,style=MaterialTheme.typography.bodyLarge,color=MaterialTheme.colorScheme.onSurfaceVariant)}
                    Column {
                        RoundSlider(dragged ?: position.toFloat().coerceIn(0f,duration.toFloat().coerceAtLeast(1f)),{dragged=it},valueRange=0f..duration.toFloat().coerceAtLeast(1f),enabled=duration>0,onValueChangeFinished={dragged?.let {seek(it.toDouble())};dragged=null},modifier=Modifier.fillMaxWidth().testTag("expanded-player-timeline").a11yLabel("Posição na música"),slim=true)
                        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){UiText(mediaClock((dragged?.toDouble() ?: position).toLong()),style=MaterialTheme.typography.labelSmall);UiText(mediaClock(duration.toLong()),style=MaterialTheme.typography.labelSmall)}
                    }
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceEvenly) {
                        LyricsButton(vm,source,{position},duration,::seek,::toggle,isPlaying={playing},title=title,artist=artist)
                        IconButton(onClick=::previous){OndaIcon("previous","Retroceder",Modifier.size(32.dp))}
                        FilledIconButton(onClick=::toggle,enabled=duration>0,modifier=Modifier.size(72.dp).testTag("expanded-player-toggle")) {
                            if(preparing)CircularProgressIndicator(Modifier.size(30.dp),strokeWidth=3.dp,color=MaterialTheme.colorScheme.onPrimary)
                            else OndaIcon(if(playing)"pause" else "play",if(playing)"Pausar" else "Reproduzir",Modifier.size(36.dp))
                        }
                        IconButton(onClick=::next,enabled=hasNext,modifier=Modifier.testTag("expanded-player-next")){OndaIcon("next","Avançar",Modifier.size(32.dp))}
                        IconButton(onClick=::openQueue,modifier=Modifier.testTag("expanded-player-queue")){OndaIcon("queue","Fila",Modifier.size(26.dp))}
                    }
                    PlaybackDeviceButton(onClick={devices=true})
                    LyricsPreviewCard(vm,source,title,artist,position,duration,playing,::seek,::toggle)
                }
            }
        }
        // The sheet belongs to this dialog so it stays above the expanded player.
        if(useJukebox && expandedQueue)PlaybackQueueSheet(vm){expandedQueue=false}
        if(devices)PlaybackDevicesSheet {devices=false}
        if(!useJukebox)EffectsQueueDrawer(vm)
    }
    if(!expanded || useJukebox)EffectsQueueDrawer(vm)
    if(timer)JukeboxTimerDialog(vm.jukebox){timer=false}
    if(equalizer)JukeboxEqualizerDialog {equalizer=false}
}
