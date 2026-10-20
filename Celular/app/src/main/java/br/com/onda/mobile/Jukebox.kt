package br.com.onda.mobile

import android.content.Context
import android.content.BroadcastReceiver
import android.content.Intent
import android.content.IntentFilter
import androidx.core.content.ContextCompat
import android.media.*
import android.util.Base64
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.input.pointer.pointerInput
import java.util.concurrent.atomic.AtomicInteger
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.*
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.flow.first
import org.json.JSONObject
import java.util.UUID
import kotlin.math.*

internal data class JukeboxState(val title:String="Escolha sua música.",val message:String="Abra um arquivo ou pesquise uma música para começar.",val model:JSONObject?=null,val records:List<JSONObject> = emptyList(),val busy:Boolean=false,val playing:Boolean=false,val paused:Boolean=false,val index:Int=0,val phase:Float=0f,val flow:List<Pair<Int,Int>> = emptyList(),val elapsed:Double=0.0,val jumps:Int=0)

internal class JukeboxController(private val context:Context,private val scope:CoroutineScope,var stopOtherAudio:()->Unit) {
    val state=MutableStateFlow(JukeboxState())
    @Volatile var variation=45f
    @Volatile var smooth=35f
    @Volatile var normal=false
    private val pendingSeek=AtomicInteger(-1)
    fun seek(index:Int) {
        val n=state.value.model?.optJSONArray("neighbors")?.length() ?: return
        if(index !in 0 until n || state.value.busy)return
        pendingSeek.set(index);state.update {it.copy(index=index,phase=0f,flow=emptyList())}
    }
    private var task:Job?=null
    private var identity=""
    @Volatile private var revision=0
    @Volatile private var track:AudioTrack?=null
    private val audio=context.getSystemService(AudioManager::class.java)
    private var noisyRegistered=false
    private val noisy=object:BroadcastReceiver(){override fun onReceive(context:Context,intent:Intent){if(intent.action==AudioManager.ACTION_AUDIO_BECOMING_NOISY)pause()}}
    private fun releaseNoisy(){if(noisyRegistered){runCatching {context.unregisterReceiver(noisy)};noisyRegistered=false}}
    private val focus=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN).setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build()).setOnAudioFocusChangeListener {change->if(change<0)pause()}.build()
    private suspend fun call(action:String,config:JSONObject,id:String):JSONObject=withContext(Dispatchers.IO) {
        MobileEngine.call(context,id,action,config,EventCallback {}).also {require(!it.has("error")){it.optString("error")}}
    }
    fun prepare(source:String="",record:JSONObject?=null,url:String="") {
        stop();val own=++revision;val id="jukebox-"+UUID.randomUUID();identity=id
        state.value=JukeboxState(title=record?.optString("title").orEmpty(),message="Analisando ritmo e trechos semelhantes…",busy=true)
        val direct=record?.optBoolean("_jukebox_direct")==true
        val config=OndaStore.config().put("source",source).put("url",if(direct)record!!.getString("source_url") else url)
        if(record!=null&&!direct)config.put("record",record)
        task=scope.launch {
            try {
                val model=call("jukebox_prepare",config,id)
                if(own==revision)state.value=JukeboxState(title=model.optString("media_title").ifBlank {model.optString("title")},model=model,message=if(model.optInt("links")>0)"Análise concluída." else "Sem saltos compatíveis: a faixa será repetida normalmente.")
            } catch(e:CancellationException){throw e} catch(e:Exception){if(own==revision)state.value=state.value.copy(busy=false,message=e.message ?: "Não foi possível analisar a música.")}
        }
    }
    fun search(query:String) {
        if(query.isBlank())return
        if(query.startsWith("http://") || query.startsWith("https://")) {stop();state.value=JukeboxState(records=listOf(JSONObject().put("title",query).put("source_url",query).put("_jukebox_direct",true)),message="Escolha uma música nos resultados.");return}
        stop();val own=++revision;val id="jukebox-search-"+UUID.randomUUID();identity=id
        state.value=JukeboxState(message="Pesquisando…",busy=true)
        task=scope.launch {
            try {
                val result=call("search",OndaStore.config().put("query",query).put("provider",OndaStore.settings.value.optString("provider","Deezer")).put("auto_metadata",true),id)
                val rows=result.optJSONArray("tracks");val records=if(rows==null)emptyList() else (0 until min(12,rows.length())).map {rows.getJSONObject(it)}
                if(own==revision)state.value=JukeboxState(records=records,message=if(records.isEmpty())"Nenhuma música encontrada." else "Escolha uma música nos resultados.")
            } catch(e:CancellationException){throw e} catch(e:Exception){if(own==revision)state.value=state.value.copy(busy=false,message=e.message ?: "Falha de pesquisa.")}
        }
    }
    fun pause() {if(state.value.playing){state.update {it.copy(paused=true)};runCatching {track?.pause()}}}
    fun playPause() {
        if(state.value.playing) {
            if(state.value.paused){if(audio.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED)return;runCatching {track?.play()};state.update {it.copy(paused=false)}} else pause()
            return
        }
        val model=state.value.model ?: return
        if(!java.io.File(model.optString("cache"),"analysis.json").isFile){state.value=state.value.copy(model=null,message="O cache foi limpo. Abra ou pesquise a música novamente.");return}
        val initial=state.value.index
        stopOtherAudio();stop();pendingSeek.set(initial);val own=++revision;val id="jukebox-play-"+UUID.randomUUID();identity=id
        state.value=state.value.copy(model=model,playing=true,paused=false,message="Reproduzindo…",elapsed=0.0,jumps=0,phase=0f,flow=emptyList())
        try {ContextCompat.startForegroundService(context,Intent(context,JukeboxService::class.java))}
        catch(e:Exception){state.update {it.copy(playing=false,message=e.message ?: "Não foi possível reproduzir.")};return}
        if(audio.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED){state.value=state.value.copy(playing=false,message="A saída de áudio está ocupada.");return}
        ContextCompat.registerReceiver(context,noisy,IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),ContextCompat.RECEIVER_NOT_EXPORTED);noisyRegistered=true
        task=scope.launch(Dispatchers.IO) {
            var output:AudioTrack?=null
            try {
                call("jukebox_open",JSONObject().put("session",id).put("cache",model.getString("cache")),id)
                val minimum=AudioTrack.getMinBufferSize(44100,AudioFormat.CHANNEL_OUT_STEREO,AudioFormat.ENCODING_PCM_16BIT)
                require(minimum>0){"Não foi possível abrir a saída de áudio."}
                output=AudioTrack.Builder().setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build()).setAudioFormat(AudioFormat.Builder().setSampleRate(44100).setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build()).setBufferSizeInBytes(max(minimum,44100*4/5)).setTransferMode(AudioTrack.MODE_STREAM).build()
                require(output.state==AudioTrack.STATE_INITIALIZED){"Não foi possível abrir a saída de áudio."}
                synchronized(this@JukeboxController) {
                    if(own!=revision || !isActive)throw CancellationException()
                    track=output;output.play()
                }
                val timeline=java.util.ArrayDeque<Pair<Long,JSONObject>>();var submitted=0L;var lastProgress=0L
                fun progress() {
                    val now=android.os.SystemClock.elapsedRealtime()
                    if(now-lastProgress<40 || own!=revision)return
                    lastProgress=now
                    val played=output.playbackHeadPosition.toLong() and 0xffffffffL
                    val heard=buildList {while(timeline.isNotEmpty() && timeline.first.first<=played)add(timeline.removeFirst().second)}
                    val part=timeline.peekFirst();val frames=part?.second?.optDouble("seconds")?.times(44100) ?: 1.0
                    val phase=if(part==null)0f else ((played-(part.first-frames))/frames).toFloat().coerceIn(0f,1f)
                    state.update {current->if(own==revision)current.copy(
                        index=part?.second?.optInt("index") ?: heard.lastOrNull()?.optInt("next") ?: current.index,phase=phase,
                        flow=if(heard.isEmpty())current.flow else (current.flow+heard.map {it.optInt("index") to it.optInt("next")}).takeLast(24),
                        jumps=heard.lastOrNull()?.optInt("jumps") ?: current.jumps,elapsed=played/44100.0) else current}
                }
                while(isActive && own==revision) {
                    if(state.value.paused)state.first {!it.paused}
                    ensureActive()
                    val config=JSONObject().put("equalizer",OndaStore.settings.value.optJSONObject("jukebox_equalizer")).put("session",id).put("variation",variation).put("smooth",smooth).put("volume",100).put("normal",normal)
                    val seek=pendingSeek.getAndSet(-1)
                    if(seek>=0){output.pause();output.flush();submitted=0L;timeline.clear();output.play();config.put("seek",seek)}
                    val part=call("jukebox_chunk",config,id)
                    val data=Base64.decode(part.getString("pcm"),Base64.NO_WRAP);part.remove("pcm");var offset=0
                    submitted+=data.size/4;timeline.addLast(submitted to part)
                    while(offset<data.size && isActive && own==revision) {
                        if(state.value.paused)state.first {!it.paused}
                        ensureActive()
                        val count=output.write(data,offset,min(4096,data.size-offset),AudioTrack.WRITE_NON_BLOCKING)
                        require(count>=0){"A saída de áudio foi interrompida."}
                        if(count==0)delay(5) else offset+=count
                        progress()
                    }
                    progress()
                }
            } catch(e:CancellationException){throw e} catch(e:Exception){if(own==revision)state.value=state.value.copy(message=e.message ?: "Não foi possível reproduzir.")}
            finally {
                runCatching {output?.pause();output?.flush();output?.release()}
                withContext(NonCancellable+Dispatchers.IO) {runCatching {call("jukebox_close",JSONObject().put("session",id),id+"-close")}}
                if(own==revision){track=null;state.update {it.copy(playing=false,paused=false)};releaseNoisy();audio.abandonAudioFocusRequest(focus)}
            }
        }
    }
    fun stop() {
        synchronized(this) {revision++;runCatching {track?.pause();track?.flush()};track=null}
        if(identity.isNotBlank())MobileEngine.cancel(identity)
        task?.cancel();task=null;runCatching {track?.pause();track?.flush()};track=null
        releaseNoisy();audio.abandonAudioFocusRequest(focus)
        state.value=state.value.copy(busy=false,playing=false,paused=false,index=0,phase=0f,flow=emptyList(),message=if(state.value.playing||state.value.busy)"Reprodução encerrada." else state.value.message)
    }
    fun close()=stop()
}

@Composable internal fun PlaybackPage(vm:OndaViewModel) {
    var mode by rememberSaveable {mutableStateOf(if(vm.jukebox.state.value.model!=null)1 else 0)}
    val jukeboxState by vm.jukebox.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {if(jukeboxState.playing)mode=1}
    val incomingSource by vm.effectsSource.collectAsStateWithLifecycle()
    LaunchedEffect(jukeboxState.model) {jukeboxState.model?.optString("source")?.takeIf {it.isNotBlank()}?.let {vm.effectsSource.value=it}}
    LaunchedEffect(incomingSource) {if(incomingSource.isNotBlank() && incomingSource!=jukeboxState.model?.optString("source"))mode=0}
    val owner=LocalLifecycleOwner.current
    DisposableEffect(owner) {
        val observer=LifecycleEventObserver {_,event->if(event==Lifecycle.Event.ON_STOP && !OndaStore.settings.value.optBoolean("jukebox_background"))vm.jukebox.pause()}
        owner.lifecycle.addObserver(observer)
        onDispose {owner.lifecycle.removeObserver(observer);if(!OndaStore.settings.value.optBoolean("jukebox_background"))vm.jukebox.pause()}
    }
    Column(Modifier.fillMaxSize()) {
        UiText("Reprodução",modifier=Modifier.padding(horizontal=24.dp,vertical=8.dp),style=MaterialTheme.typography.headlineMedium,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth().padding(horizontal=24.dp,vertical=8.dp)) {
            listOf("Efeitos","Jukebox infinito").forEachIndexed {index,label->SegmentedButton(selected=index==mode,shape=RoundedCornerShape(12.dp),icon={},colors=SegmentedButtonDefaults.colors(activeContainerColor=MaterialTheme.colorScheme.primary,activeContentColor=MaterialTheme.colorScheme.onPrimary),onClick={vm.stopPreview(!OndaStore.settings.value.optBoolean("jukebox_background"));mode=index;if(index==1 && incomingSource.isNotBlank() && incomingSource!=jukeboxState.model?.optString("source"))vm.jukebox.prepare(incomingSource)}){UiText(label)}}
        }
        if(mode==0)EffectsPage(vm,heading=false) else JukeboxPage(vm)
    }
}

@Composable private fun JukeboxPage(vm:OndaViewModel) {
    val controller=vm.jukebox;val state by controller.state.collectAsStateWithLifecycle()
    var showEqualizer by rememberSaveable {mutableStateOf(false)}
    if(showEqualizer)JukeboxEqualizerDialog {showEqualizer=false}
    var query by rememberSaveable {mutableStateOf("")}
    var variation by rememberSaveable {mutableFloatStateOf(controller.variation)}
    var smooth by rememberSaveable {mutableFloatStateOf(controller.smooth)}
    var normal by rememberSaveable {mutableStateOf(controller.normal)}
    LaunchedEffect(variation,smooth,normal) {controller.variation=variation;controller.smooth=smooth;controller.normal=normal}
    val chooser=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"audio") {file->controller.prepare(file.absolutePath)}}
    var chooseMusic by rememberSaveable {mutableStateOf(false)}
    var playbackMenu by remember {mutableStateOf(false)}
    BoxWithConstraints(Modifier.fillMaxSize()) {
    val graphHeight=(maxHeight*.36f).coerceIn(200.dp,260.dp)
    Column(Modifier.fillMaxSize().padding(horizontal=24.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(top=12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        if(state.model==null || chooseMusic || state.busy) {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                Button(onClick={chooser.launch(arrayOf("audio/*"))},enabled=!state.busy){UiText("Abrir arquivo")}
                TextButton(onClick={showEqualizer=true}){UiText("Equalizador")}
            }
            OutlinedTextField(query,{query=it},placeholder={UiText("Pesquise uma música ou cole um link")},singleLine=true,shape=RoundedCornerShape(14.dp),modifier=Modifier.fillMaxWidth())
            Button(onClick={if(state.busy)controller.stop() else controller.search(query)},enabled=state.busy || query.isNotBlank()){UiText(if(state.busy)"Cancelar" else "Pesquisar")}
            if(state.busy)LinearProgressIndicator(Modifier.fillMaxWidth())
            state.records.forEach {record->
                val artists=record.optJSONArray("artists")?.let {a->(0 until a.length()).joinToString(", "){a.getString(it)}}.orEmpty()
                OutlinedButton(onClick={chooseMusic=false;controller.prepare(record=record)},modifier=Modifier.fillMaxWidth()) {UiText(listOf(record.optString("title"),artists).filter {it.isNotBlank()}.joinToString(" · "))}
            }
        }
        val embeddedCover=state.model?.optString("media_cover").orEmpty()
        val cover=remember(embeddedCover,state.model?.optString("cover_url")) {
            if(embeddedCover.isNotBlank())runCatching {Base64.decode(embeddedCover,Base64.DEFAULT)}.getOrNull()
            else state.model?.optString("cover_url")?.takeIf {it.isNotBlank()}
        }
        if(state.model!=null)Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(16.dp)) {
            Box(Modifier.size(128.dp).clip(RoundedCornerShape(12.dp)),contentAlignment=androidx.compose.ui.Alignment.Center) {
                if(cover!=null)coil.compose.AsyncImage(model=cover,contentDescription=translateUi("Capa do álbum"),contentScale=ContentScale.Crop,modifier=Modifier.fillMaxSize())
                else OndaIcon("album",modifier=Modifier.size(44.dp))
            }
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                UiText(state.title,style=MaterialTheme.typography.titleMedium,maxLines=2)
                state.model?.optString("media_artist")?.takeIf {it.isNotBlank()}?.let {UiText(it,style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)}
                state.model?.optString("album")?.takeIf {it.isNotBlank()}?.let {UiText(it,style=MaterialTheme.typography.bodySmall,maxLines=1,color=MaterialTheme.colorScheme.onSurfaceVariant)}
                OutlinedButton(onClick={showEqualizer=true},shape=RoundedCornerShape(10.dp),contentPadding=PaddingValues(horizontal=10.dp,vertical=4.dp)) {
                    OndaIcon("equalizer",modifier=Modifier.size(17.dp));Spacer(Modifier.width(8.dp));UiText("Equalizador",style=MaterialTheme.typography.labelMedium)
                }
            }
        }
        if(state.model==null || state.busy)UiText(state.message,style=MaterialTheme.typography.bodySmall)
        JukeboxGraph(state.model,state.index,state.phase,state.playing,state.flow,variation,smooth,normal,controller::seek,height=graphHeight)
        UiText("Variação",style=MaterialTheme.typography.labelLarge)
        Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            UiText("Mais fiel",style=MaterialTheme.typography.labelSmall)
            RoundSlider(variation,{variation=it;controller.variation=it},modifier=Modifier.weight(1f).testTag("jukebox-variation"),valueRange=0f..100f,slim=true)
            UiText("Mais saltos",style=MaterialTheme.typography.labelSmall)
        }
        UiText("Transição suave",style=MaterialTheme.typography.labelLarge)
        RoundSlider(smooth,{smooth=it;controller.smooth=it},modifier=Modifier.fillMaxWidth().testTag("jukebox-transition"),valueRange=0f..100f,slim=true)
        Spacer(Modifier.height(4.dp))
        }
        Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceEvenly) {
            IconButton(onClick={showEqualizer=true}){OndaIcon("equalizer","Equalizador",Modifier.size(23.dp))}
            IconButton(onClick={controller.seek((state.index-1).coerceAtLeast(0))},enabled=state.model!=null&&!state.busy){OndaIcon("previous","Trecho anterior",Modifier.size(25.dp))}
            FilledIconButton(onClick=controller::playPause,enabled=state.model!=null&&!state.busy,modifier=Modifier.size(64.dp),shape=RoundedCornerShape(50)){OndaIcon(if(state.playing&&!state.paused)"pause" else "play",if(state.playing&&!state.paused)"Pausar" else "Reproduzir",Modifier.size(28.dp))}
            IconButton(onClick={val n=state.model?.optJSONArray("neighbors")?.length() ?: 1;controller.seek((state.index+1)%n)},enabled=state.model!=null&&!state.busy){OndaIcon("next","Próximo trecho",Modifier.size(25.dp))}
            Box {
                IconButton(onClick={playbackMenu=true}){OndaIcon("more","Controles da reprodução",Modifier.size(25.dp))}
                DropdownMenu(expanded=playbackMenu,onDismissRequest={playbackMenu=false}) {
                    DropdownMenuItem(text={UiText("Trocar música")},onClick={chooseMusic=true;playbackMenu=false})
                    DropdownMenuItem(text={UiText("Reprodução normal")},leadingIcon={Checkbox(normal,null)},onClick={normal=!normal;controller.normal=normal;playbackMenu=false})
                    DropdownMenuItem(text={UiText("Parar")},enabled=state.playing || state.busy,onClick={controller.stop();playbackMenu=false})
                    HorizontalDivider()
                    DropdownMenuItem(text={UiText(translateUi("Tempo ouvido: {time} · Saltos: {count}").replace("{time}",mediaClock(state.elapsed.toLong())).replace("{count}",state.jumps.toString()),style=MaterialTheme.typography.labelSmall)},enabled=false,onClick={})
                }
            }
        }

    }
    }
}

@Composable private fun JukeboxGraph(model:JSONObject?,current:Int,phase:Float,playing:Boolean,flow:List<Pair<Int,Int>>,variation:Float,smooth:Float,normal:Boolean,onSeek:(Int)->Unit,height:Dp=230.dp) {
    val colors=MaterialTheme.colorScheme;val rows=model?.optJSONArray("neighbors");val n=max(1,rows?.length() ?: 64)
    val graphColors=jukeboxGraphColors(colors)
    val visible=remember(model,variation,normal){jukeboxVisibleLinks(model,variation,normal)}
    Box(Modifier.fillMaxWidth().height(height),contentAlignment=androidx.compose.ui.Alignment.Center) {
        Canvas(Modifier.fillMaxSize().pointerInput(n,model) {
            detectTapGestures {position->
                if(model!=null) {
                    val dx=position.x-size.width/2f;val dy=position.y-size.height/2f
                    val radius=min(size.width,size.height)*.42f
                    if(abs(hypot(dx,dy)-radius)<=24.dp.toPx()) {
                        val angle=(atan2(dy.toDouble(),dx.toDouble())+PI/2+2*PI)%(2*PI)
                        onSeek((angle/(2*PI)*n).roundToInt()%n)
                    }
                }
            }
        }) {
            val radius=min(size.width,size.height)*.42f
            fun point(index:Double):Offset {val angle=index/n*2*PI-PI/2;return center+Offset((cos(angle)*radius).toFloat(),(sin(angle)*radius).toFloat())}
            val strength=if(normal)0f else (variation/100).coerceIn(0f,1f)
            for((i,j) in visible) {
                val a=point(i.toDouble());val b=point(j.toDouble())
                drawPath(Path().apply {moveTo(a.x,a.y);quadraticTo(center.x,center.y,b.x,b.y)},graphColors.second.copy(alpha=.35f+.15f*strength),style=androidx.compose.ui.graphics.drawscope.Stroke((.65f+.35f*smooth/100).dp.toPx()))
            }
            for((k,edge) in flow.withIndex()) {
                val (i,j)=edge;val ink=colors.primary.copy(alpha=.75f+.25f*(k+1)/flow.size)
                if(j==(i+1)%n) {
                    drawArc(ink,i.toFloat()/n*360-90,360f/n,false,topLeft=center-Offset(radius,radius),size=androidx.compose.ui.geometry.Size(radius*2,radius*2),style=androidx.compose.ui.graphics.drawscope.Stroke(4.dp.toPx()))
                } else {
                    val a=point(i.toDouble());val b=point(j.toDouble())
                    drawPath(Path().apply {moveTo(a.x,a.y);quadraticTo(center.x,center.y,b.x,b.y)},ink,style=androidx.compose.ui.graphics.drawscope.Stroke(3.dp.toPx()))
                    val delta=b-center;val length=hypot(delta.x,delta.y);val unit=delta/length
                    val back=b-unit*12.dp.toPx();val side=Offset(-unit.y,unit.x)*5.dp.toPx()
                    drawLine(ink,back+side,b,3.dp.toPx());drawLine(ink,back-side,b,3.dp.toPx())
                }
            }
            for(i in 0 until n step max(1,n/150))drawCircle(if(i==current)colors.primary else graphColors.first,3.dp.toPx(),point(i.toDouble()))
            drawCircle(colors.primary,(if(playing)6+2*(1-phase).pow(3) else 6f).dp.toPx(),point(current.coerceIn(0,n-1)+phase.toDouble()))
        }

    }
}

internal fun jukeboxVisibleLinks(model:JSONObject?,variation:Float,normal:Boolean):List<Pair<Int,Int>> {
    val rows=model?.optJSONArray("neighbors") ?: return emptyList()
    val limit=if(normal)0 else ceil(90*(.15f+.85f*(variation/100).coerceIn(0f,1f))).toInt()
    if(limit==0)return emptyList()
    val links=buildList {for(i in 0 until rows.length()){val row=rows.optJSONArray(i) ?: continue;for(k in 0 until row.length())add(i to row.getInt(k))}}
    return links.filterIndexed {index,_->index % max(1,links.size/limit)==0}.take(limit)
}

// Graph geometry must remain visible when pure-black mode hides UI separators.
internal fun jukeboxGraphColors(colors:ColorScheme):Pair<Color,Color> {
    val dark=colors.surface.luminance()<.25f
    val ring=lerp(colors.surface,colors.onSurface,if(dark).68f else .55f)
    val accent=lerp(colors.primary,colors.onSurface,if(dark).15f else 0f)
    val links=lerp(colors.surface,accent,if(dark).7f else .4f)
    return ring to links
}
