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

internal data class JukeboxState(val title:String="Escolha sua música.",val message:String="Abra um arquivo ou pesquise uma música para começar.",val model:JSONObject?=null,val records:List<JSONObject> = emptyList(),val busy:Boolean=false,val playing:Boolean=false,val paused:Boolean=false,val index:Int=0,val phase:Float=0f,val flow:List<Pair<Int,Int>> = emptyList(),val used:Set<Pair<Int,Int>> = emptySet(),val elapsed:Double=0.0,val jumps:Int=0,val nextIndex:Int=-1,val jumpBlend:Float=0f)

internal class JukeboxController(private val context:Context,private val scope:CoroutineScope,var stopOtherAudio:()->Unit,private val callOverride:(suspend (String,JSONObject,String)->JSONObject)?=null) {
    val state=MutableStateFlow(JukeboxState())
    val playbackQueue=MutableStateFlow<List<JSONObject>>(emptyList())
    val timerMinutes=MutableStateFlow(0)
    val timerRemaining=MutableStateFlow(0)
    val switchMinutes=MutableStateFlow(0)
    val switchRemaining=MutableStateFlow(0)
    private var timerTask:Job?=null
    private var switchTask:Job?=null
    private var fadeTask:Job?=null
    private var stopGain=1f
    private var switchGain=1f
    private var startGain=1f
    private fun applyGain(){runCatching {track?.setVolume(minOf(stopGain,switchGain,startGain))}}
    private fun gradual()=OndaStore.settings.value.optBoolean("jukebox_gradual_transition",true)
    fun setTimer(minutes:Int,nextSong:Boolean=false) {
        val duration=minutes.coerceIn(0,180)
        if(nextSong){switchTask?.cancel();switchMinutes.value=duration;switchRemaining.value=duration*60;switchGain=1f}
        else {timerTask?.cancel();timerMinutes.value=duration;timerRemaining.value=duration*60;stopGain=1f}
        applyGain()
        if(duration<=0)return
        val progress=JukeboxTimerProgress(duration*60.0)
        val job=scope.launch {
            var last=android.os.SystemClock.elapsedRealtime()
            while(isActive) {
                delay(250)
                val now=android.os.SystemClock.elapsedRealtime();val current=state.value
                val remaining=progress.advance((now-last)/1000.0,current.playing,current.paused,if(nextSong)current.model else this@JukeboxController)
                last=now
                if(nextSong)switchRemaining.value=ceil(remaining).toInt() else timerRemaining.value=ceil(remaining).toInt()
                val head=playbackQueue.value.firstOrNull()
                val ready=head?.optString("_analysis")=="Pronta"
                switchGain=1f
                if(!nextSong)stopGain=if(gradual())(remaining/10).toFloat().coerceIn(0f,1f) else 1f
                applyGain()
                if(remaining<=0) {
                    if(!nextSong){stop();return@launch}
                    if(head==null || head.optString("_analysis")=="Erro") {
                        state.update {it.copy(message=if(head==null)"A fila da Jukebox está vazia. O timer de troca foi desligado." else "A próxima música não pôde ser preparada. Confira a fila da Jukebox.")}
                        setTimer(0,true);return@launch
                    }
                    // Keep the current song audible until preparation finishes.
                    if(ready){playQueued(0);progress.restart();last=android.os.SystemClock.elapsedRealtime()}
                }
            }
        }
        if(nextSong)switchTask=job else timerTask=job
    }
    private val preparedModels=mutableMapOf<String,JSONObject>()
    private var queueWorker:Job?=null
    private var queuePreparing=""
    private fun updateQueue(id:String,status:String,error:String="") {
        playbackQueue.update {rows->rows.map {if(it.optString("_queue_id")==id)JSONObject(it.toString()).put("_analysis",status).put("_error",error) else it}}
    }
    private fun prepareConfig(source:String,record:JSONObject?,url:String=""):JSONObject {
        val direct=record?.optBoolean("_jukebox_direct")==true
        return OndaStore.config().put("source",source).put("url",if(direct)record!!.getString("source_url") else url).apply {if(record!=null&&!direct)put("record",record)}
    }
    private fun startQueuePreparation() {
        if(queueWorker?.isActive==true)return
        queueWorker=scope.launch {
            while(isActive) {
                val row=playbackQueue.value.firstOrNull {it.optString("_analysis")=="Pendente"} ?: break
                val id=row.getString("_queue_id");queuePreparing=id;updateQueue(id,"Analisando")
                try {
                    val model=call("jukebox_prepare",prepareConfig(row.optString("_local_source"),row.takeUnless {it.has("_local_source")}),"jukebox-preload-$id")
                    if(playbackQueue.value.any {it.optString("_queue_id")==id}){preparedModels[id]=model;updateQueue(id,"Pronta")}
                } catch(e:CancellationException){throw e}
                catch(e:Exception){updateQueue(id,"Erro",e.message ?: "Não foi possível analisar.")}
                finally {queuePreparing=""}
            }
        }
    }
    fun enqueue(record:JSONObject) {
        playbackQueue.update {it+JSONObject(record.toString()).put("_queue_id",UUID.randomUUID().toString()).put("_analysis","Pendente")}
        startQueuePreparation()
    }
    fun retryQueued(index:Int){playbackQueue.value.getOrNull(index)?.optString("_queue_id")?.let {updateQueue(it,"Pendente");startQueuePreparation()}}
    fun removeQueued(index:Int) {
        val id=playbackQueue.value.getOrNull(index)?.optString("_queue_id") ?: return
        playbackQueue.update {rows->rows.filter {it.optString("_queue_id")!=id}}
        preparedModels.remove(id)
        if(queuePreparing==id)MobileEngine.cancel("jukebox-preload-$id")
    }
    private data class TrackSwitch(val row:JSONObject,val model:JSONObject,val seconds:Int)
    @Volatile private var switchRequest:TrackSwitch?=null
    @Volatile private var switchActive=false
    private val switchModels=java.util.concurrent.ConcurrentHashMap<String,TrackSwitch>()
    private fun transitionSeconds()=OndaStore.settings.value.optInt("jukebox_transition_seconds",2).coerceIn(1,10)
    fun playQueued(index:Int) {
        val row=playbackQueue.value.getOrNull(index) ?: return
        val model=preparedModels[row.optString("_queue_id")] ?: return
        if(!java.io.File(model.optString("cache"),"analysis.json").isFile()) {updateQueue(row.optString("_queue_id"),"Pendente");startQueuePreparation();return}
        if(state.value.playing && !state.value.paused) {
            if(switchActive)return
            switchActive=true
            val request=TrackSwitch(row,model,if(gradual())transitionSeconds() else 0)
            switchModels[model.getString("cache")]=request;switchRequest=request
            return
        }
        stop(clearTimer=false);removeQueued(index)
        state.value=JukeboxState(title=model.optString("media_title").ifBlank {model.optString("title")},model=model)
        playPause()
    }
    suspend fun searchQueue(query:String,id:String="jukebox-queue-"+UUID.randomUUID()):List<JSONObject> {
        if(query.startsWith("https://") || query.startsWith("http://"))return listOf(JSONObject().put("title",query).put("source_url",query).put("_jukebox_direct",true))
        val result=call("search",OndaStore.config().put("query",query).put("provider",OndaStore.settings.value.optString("provider","Deezer")),id)
        val rows=result.optJSONArray("tracks") ?: return emptyList()
        return (0 until min(12,rows.length())).map {rows.getJSONObject(it)}
    }
    @Volatile var variation=45f
    @Volatile var smooth=35f
    @Volatile var normal=false
    private val pendingSeek=AtomicInteger(-1)
    fun seek(index:Int) {
        val n=state.value.model?.optJSONArray("neighbors")?.length() ?: return
        if(index !in 0 until n || state.value.busy)return
        pendingSeek.set(index);state.update {it.copy(index=index,phase=0f,flow=emptyList(),used=emptySet(),nextIndex=-1,jumpBlend=0f)}
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
    private suspend fun call(action:String,config:JSONObject,id:String):JSONObject {
        callOverride?.let {return it(action,config,id)}
        return withContext(Dispatchers.IO) {
        MobileEngine.call(context,id,action,config,EventCallback {}).also {require(!it.has("error")){it.optString("error")}}
    }
    }
    fun prepare(source:String="",record:JSONObject?=null,url:String="",autoPlay:Boolean=false) {
        stop(clearTimer=false);val own=++revision;val id="jukebox-"+UUID.randomUUID();identity=id
        state.value=JukeboxState(title=record?.optString("title").orEmpty(),message="Analisando ritmo e trechos semelhantes…",busy=true)
        val config=prepareConfig(source,record,url)
        task=scope.launch {
            try {
                val model=call("jukebox_prepare",config,id)
                if(own==revision)state.value=JukeboxState(title=model.optString("media_title").ifBlank {model.optString("title")},model=model,message=if(model.optInt("links")>0)"Análise concluída." else "Sem saltos compatíveis: a faixa será repetida normalmente.")
                if(own==revision && autoPlay)playPause()
            } catch(e:CancellationException){throw e} catch(e:Exception){if(own==revision)state.value=state.value.copy(busy=false,message=e.message ?: "Não foi possível analisar a música.")}
        }
    }
    val searching=MutableStateFlow(false)
    private var searchTask:Job?=null
    private var searchIdentity=""
    fun cancelSearch() {
        val id=searchIdentity;searchIdentity=""
        searchTask?.cancel();searchTask=null;searching.value=false
        if(id.isNotBlank())MobileEngine.cancel(id)
    }
    fun search(query:String) {
        if(query.isBlank())return
        cancelSearch()
        val id="jukebox-search-"+UUID.randomUUID();searchIdentity=id
        searching.value=true
        state.update {it.copy(records=emptyList(),message="Pesquisando…")}
        searchTask=scope.launch {
            try {
                val records=searchQueue(query,id)
                if(searchIdentity==id)state.update {it.copy(records=records,message=if(records.isEmpty())"Nenhuma música encontrada." else "Escolha uma música nos resultados.")}
            } catch(e:CancellationException){throw e}
            catch(e:Exception){if(searchIdentity==id)state.update {it.copy(message=e.message ?: "Falha de pesquisa.")}}
            finally {if(searchIdentity==id){searchIdentity="";searching.value=false}}
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
        stopOtherAudio();stop(clearTimer=false);pendingSeek.set(initial);val own=++revision;val id="jukebox-play-"+UUID.randomUUID();identity=id
        state.value=state.value.copy(model=model,playing=true,paused=false,message="Reproduzindo…",elapsed=0.0,jumps=0,phase=0f,flow=emptyList(),used=emptySet(),nextIndex=-1,jumpBlend=0f)
        try {ContextCompat.startForegroundService(context,Intent(context,JukeboxService::class.java))}
        catch(e:Exception){state.update {it.copy(playing=false,message=e.message ?: "Não foi possível reproduzir.")};return}
        if(audio.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED){state.value=state.value.copy(playing=false,message="A saída de áudio está ocupada.");return}
        ContextCompat.registerReceiver(context,noisy,IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),ContextCompat.RECEIVER_NOT_EXPORTED);noisyRegistered=true
        fadeTask?.cancel()
        startGain=if(gradual())0f else 1f
        if(gradual())fadeTask=scope.launch {
            while(track==null && state.value.playing)delay(20)
            val steps=transitionSeconds()*20
            repeat(steps){while(state.value.paused)delay(50);startGain=(it+1)/steps.toFloat();applyGain();delay(50)}
        }
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
                    track=output;output.setVolume(minOf(stopGain,switchGain,startGain));output.play()
                }
                val timeline=java.util.ArrayDeque<Pair<Long,JSONObject>>();var submitted=0L;var lastProgress=0L;var trackBase=0L
                fun progress() {
                    val now=android.os.SystemClock.elapsedRealtime()
                    if(now-lastProgress<40 || own!=revision)return
                    lastProgress=now
                    val played=output.playbackHeadPosition.toLong() and 0xffffffffL
                    fun announce(end:Long,packet:JSONObject) {
                        val cache=packet.optString("track_changed")
                        if(cache.isBlank())return
                        packet.remove("track_changed")
                        trackBase=end-(packet.optDouble("seconds")*44100).roundToLong()
                        switchModels.remove(cache)?.let {request->scope.launch(Dispatchers.Main.immediate) {
                            val queued=playbackQueue.value.indexOfFirst {it.optString("_queue_id")==request.row.optString("_queue_id")}
                            if(queued>=0)removeQueued(queued)
                            state.update {it.copy(model=request.model,title=request.model.optString("media_title").ifBlank {request.model.optString("title")},flow=emptyList(),used=emptySet(),elapsed=0.0)}
                        }}
                    }
                    val heard=buildList {while(timeline.isNotEmpty() && timeline.first.first<=played){val entry=timeline.removeFirst();announce(entry.first,entry.second);add(entry.second)}}
                    val part=timeline.peekFirst()
                    if(part!=null)announce(part.first,part.second)
                    val frames=part?.second?.optDouble("seconds")?.times(44100) ?: 1.0
                    val local=if(part==null)0f else ((played-(part.first-frames))/frames).toFloat().coerceIn(0f,1f)
                    val startPhase=part?.second?.optDouble("phase_start",0.0) ?: 0.0
                    val endPhase=part?.second?.optDouble("phase_end",1.0) ?: 1.0
                    val phase=(startPhase+(endPhase-startPhase)*local).toFloat()
                    val outgoing=part?.second
                    val blend=if(outgoing?.optBoolean("jumped")==true)jukeboxJumpBlend(phase,outgoing.optDouble("beat_seconds",outgoing.optDouble("seconds")),outgoing.optDouble("transition_seconds")) else 0f
                    state.update {current->if(own==revision)current.copy(
                        index=part?.second?.optInt("index") ?: heard.lastOrNull()?.let {it.optInt(if(it.optBoolean("edge_completed",true))"next" else "index")} ?: current.index,phase=phase,
                        nextIndex=outgoing?.optInt("next",-1) ?: -1,jumpBlend=blend,
                        used=current.used+heard.filter {it.optBoolean("edge_completed",true)}.map {it.optInt("index") to it.optInt("next")},
                        flow=if(heard.isEmpty())current.flow else (current.flow+heard.filter {it.optBoolean("edge_completed",true)}.map {it.optInt("index") to it.optInt("next")}).takeLast(24),
                        jumps=heard.lastOrNull()?.optInt("jumps") ?: current.jumps,elapsed=(played-trackBase).coerceAtLeast(0)/44100.0) else current}
                }
                while(isActive && own==revision) {
                    if(state.value.paused)state.first {!it.paused}
                    ensureActive()
                    switchRequest?.let {request->
                        switchRequest=null
                        try {call("jukebox_switch",JSONObject().put("session",id).put("cache",request.model.getString("cache")).put("seconds",request.seconds),id)}
                        catch(e:CancellationException){throw e}
                        catch(e:Exception){switchActive=false;switchModels.remove(request.model.optString("cache"));state.update {it.copy(message=e.message ?: "Não foi possível trocar a música.")}}
                    }
                    val config=JSONObject().put("equalizer",OndaStore.settings.value.optJSONObject("jukebox_equalizer")).put("session",id).put("variation",variation).put("smooth",smooth).put("volume",100).put("normal",normal)
                    val seek=pendingSeek.getAndSet(-1)
                    if(seek>=0){output.pause();output.flush();submitted=0L;trackBase=0L;timeline.clear();output.play();config.put("seek",seek)}
                    val part=call("jukebox_chunk",config,id)
                    if(!part.optBoolean("crossfade_active",false))switchActive=false
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
    fun stop(clearTimer:Boolean=true) {
        switchRequest=null;switchActive=false;switchModels.clear()
        cancelSearch()
        if(clearTimer){timerTask?.cancel();switchTask?.cancel();timerTask=null;switchTask=null;timerMinutes.value=0;timerRemaining.value=0;switchMinutes.value=0;switchRemaining.value=0}
        fadeTask?.cancel();stopGain=1f;switchGain=1f;startGain=1f;applyGain()
        synchronized(this) {revision++;runCatching {track?.pause();track?.flush()};track=null}
        if(identity.isNotBlank())MobileEngine.cancel(identity)
        task?.cancel();task=null;runCatching {track?.pause();track?.flush()};track=null
        releaseNoisy();audio.abandonAudioFocusRequest(focus)
        state.value=state.value.copy(busy=false,playing=false,paused=false,index=0,phase=0f,flow=emptyList(),used=emptySet(),nextIndex=-1,jumpBlend=0f,message=if(state.value.playing||state.value.busy)"Reprodução encerrada." else state.value.message)
    }
    fun close(){stop();queueWorker?.cancel();if(queuePreparing.isNotBlank())MobileEngine.cancel("jukebox-preload-$queuePreparing");preparedModels.clear()}
}

@Composable internal fun PlaybackPage(vm:OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val modes=if(settings.optString("playback_tab_order")=="Jukebox infinito primeiro")listOf(1 to "Jukebox infinito",0 to "Efeitos") else listOf(0 to "Efeitos",1 to "Jukebox infinito")
    var mode by rememberSaveable(settings.optString("playback_tab_order")) {mutableStateOf(if(vm.jukebox.state.value.playing)1 else modes.first().first)}
    val jukeboxState by vm.jukebox.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {if(jukeboxState.playing)mode=1}
    val incomingSource by vm.effectsSource.collectAsStateWithLifecycle()
    LaunchedEffect(jukeboxState.model) {jukeboxState.model?.optString("source")?.takeIf {it.isNotBlank()}?.let {vm.effectsSource.value=it}}
    var observedSource by remember {mutableStateOf(vm.effectsSource.value)}
    LaunchedEffect(incomingSource) {
        if(incomingSource!=observedSource && incomingSource.isNotBlank() && incomingSource!=jukeboxState.model?.optString("source"))mode=0
        observedSource=incomingSource
    }
    val owner=LocalLifecycleOwner.current
    DisposableEffect(owner) {
        val observer=LifecycleEventObserver {_,event->if(event==Lifecycle.Event.ON_STOP && !OndaStore.settings.value.optBoolean("jukebox_background"))vm.jukebox.pause()}
        owner.lifecycle.addObserver(observer)
        onDispose {owner.lifecycle.removeObserver(observer);if(!OndaStore.settings.value.optBoolean("jukebox_background"))vm.jukebox.pause()}
    }
    Column(Modifier.fillMaxSize()) {
        UiText("Reprodução",modifier=Modifier.padding(horizontal=24.dp,vertical=8.dp),style=MaterialTheme.typography.headlineMedium,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth().padding(horizontal=24.dp,vertical=8.dp)) {
            modes.forEach {(index,label)->SegmentedButton(selected=index==mode,shape=RoundedCornerShape(12.dp),icon={},colors=SegmentedButtonDefaults.colors(activeContainerColor=MaterialTheme.colorScheme.primary,activeContentColor=MaterialTheme.colorScheme.onPrimary),onClick={vm.stopPreview(!OndaStore.settings.value.optBoolean("jukebox_background"));mode=index;if(index==1 && incomingSource.isNotBlank() && incomingSource!=jukeboxState.model?.optString("source"))vm.jukebox.prepare(incomingSource)}){UiText(label)}}
        }
        if(mode==0)EffectsPage(vm,heading=false) else JukeboxPage(vm)
    }
}

@Composable private fun JukeboxPage(vm:OndaViewModel) {
    val controller=vm.jukebox;val state by controller.state.collectAsStateWithLifecycle()
    val searching by controller.searching.collectAsStateWithLifecycle()
    val queuedTracks by controller.playbackQueue.collectAsStateWithLifecycle()
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
    var showTimer by rememberSaveable {mutableStateOf(false)}
    var showSwitchTimer by rememberSaveable {mutableStateOf(false)}
    var showQueue by rememberSaveable {mutableStateOf(false)}
    val timer by controller.timerMinutes.collectAsStateWithLifecycle()
    val switchTimer by controller.switchMinutes.collectAsStateWithLifecycle()
    if(showTimer)JukeboxTimerDialog(controller,showSwitchTimer){showTimer=false}
    if(showQueue)JukeboxQueueDialog(controller,vm){showQueue=false}
    BoxWithConstraints(Modifier.fillMaxSize()) {
    val graphHeight=(maxHeight*.36f).coerceIn(200.dp,260.dp)
    Column(Modifier.fillMaxSize().padding(horizontal=24.dp)) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(top=12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        if(state.model==null || chooseMusic || state.busy) {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                Button(onClick={chooser.launch(arrayOf("audio/*"))},enabled=!state.busy){UiText("Abrir arquivo")}
            }
            OutlinedTextField(query,{query=it},placeholder={UiText("Pesquise uma música ou cole um link")},singleLine=true,shape=RoundedCornerShape(14.dp),modifier=Modifier.fillMaxWidth())
            Button(onClick={if(searching)controller.cancelSearch() else if(state.busy)controller.stop() else controller.search(query)},enabled=searching || state.busy || query.isNotBlank()){UiText(if(searching || state.busy)"Cancelar" else "Pesquisar")}
            if(state.busy || searching)LinearProgressIndicator(Modifier.fillMaxWidth())
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
            }
        }
        if(state.model==null || state.busy || chooseMusic)UiText(state.message,style=MaterialTheme.typography.bodySmall)
        JukeboxGraph(state.model,state.index,state.phase,state.playing,state.flow,state.used,variation,smooth,normal,controller::seek,height=graphHeight,nextIndex=state.nextIndex,jumpBlend=state.jumpBlend)
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
            IconButton(onClick={showSwitchTimer=false;showTimer=true}){OndaIcon("timer","Timer",Modifier.size(23.dp),tint=if(timer>0 || switchTimer>0)MaterialTheme.colorScheme.primary else LocalContentColor.current)}
            IconButton(onClick={controller.seek((state.index-1).coerceAtLeast(0))},enabled=state.model!=null&&!state.busy){OndaIcon("previous","Trecho anterior",Modifier.size(25.dp))}
            FilledIconButton(onClick=controller::playPause,enabled=state.model!=null&&!state.busy,modifier=Modifier.size(64.dp),shape=RoundedCornerShape(50)){OndaIcon(if(state.playing&&!state.paused)"pause" else "play",if(state.playing&&!state.paused)"Pausar" else "Reproduzir",Modifier.size(28.dp))}
            if(queuedTracks.isNotEmpty())IconButton(onClick={controller.playQueued(0)},enabled=queuedTracks.first().optString("_analysis")=="Pronta"&&!state.busy,modifier=Modifier.testTag("jukebox-next-song")){OndaIcon("next","Próxima música",Modifier.size(25.dp))}
            Box {
                IconButton(onClick={playbackMenu=true}){OndaIcon("more","Controles da reprodução",Modifier.size(25.dp))}
                DropdownMenu(expanded=playbackMenu,onDismissRequest={playbackMenu=false}) {
                    DropdownMenuItem(text={UiText("Parar")},enabled=state.playing || state.busy,onClick={controller.stop();playbackMenu=false})
                    DropdownMenuItem(text={UiText("Trocar música")},onClick={chooseMusic=true;playbackMenu=false})
                    DropdownMenuItem(text={UiText("Timer para trocar música")},onClick={showSwitchTimer=true;showTimer=true;playbackMenu=false})
                    DropdownMenuItem(text={UiText("Timer para parar")},onClick={showSwitchTimer=false;showTimer=true;playbackMenu=false})
                    DropdownMenuItem(text={UiText("Reprodução normal")},leadingIcon={Checkbox(normal,null)},onClick={normal=!normal;controller.normal=normal;playbackMenu=false})
                    DropdownMenuItem(text={UiText("Fila da Jukebox")},onClick={showQueue=true;playbackMenu=false})
                    HorizontalDivider()
                    DropdownMenuItem(text={UiText(translateUi("Tempo ouvido: {time} · Saltos: {count}").replace("{time}",mediaClock(state.elapsed.toLong())).replace("{count}",state.jumps.toString()),style=MaterialTheme.typography.labelSmall)},enabled=false,onClick={})
                }
            }
        }

    }
    }
}

@Composable internal fun JukeboxTimerDialog(controller:JukeboxController,initialNext:Boolean=false,close:()->Unit) {
    val stopMinutes by controller.timerMinutes.collectAsStateWithLifecycle()
    val stopRemaining by controller.timerRemaining.collectAsStateWithLifecycle()
    val switchMinutes by controller.switchMinutes.collectAsStateWithLifecycle()
    val switchRemaining by controller.switchRemaining.collectAsStateWithLifecycle()
    val queue by controller.playbackQueue.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var nextSong by rememberSaveable {mutableStateOf(initialNext)}
    var stopDuration by rememberSaveable {mutableStateOf(if(stopMinutes>0)stopMinutes.toString() else "30")}
    var switchDuration by rememberSaveable {mutableStateOf(if(switchMinutes>0)switchMinutes.toString() else "5")}
    val value=(if(nextSong)switchDuration else stopDuration).toIntOrNull()
    AlertDialog(onDismissRequest=close,title={UiText("Timer")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        Row {TextButton(onClick={nextSong=true}){UiText("Trocar música")};TextButton(onClick={nextSong=false}){UiText("Parar música")}}
        UiText(if(nextSong)"Timer para trocar música" else "Timer para parar",style=MaterialTheme.typography.titleSmall)
        OutlinedTextField(if(nextSong)switchDuration else stopDuration,{val text=it.filter(Char::isDigit).take(3);if(nextSong)switchDuration=text else stopDuration=text},label={UiText("Tempo em minutos")},singleLine=true,isError=value==null || value !in 1..180,keyboardOptions=androidx.compose.foundation.text.KeyboardOptions(keyboardType=androidx.compose.ui.text.input.KeyboardType.Number),modifier=Modifier.fillMaxWidth())
        UiText(if(nextSong)"Avança pela fila a cada intervalo. Aguarda a próxima faixa ficar pronta sem interromper a atual." else "Encerra a reprodução após o tempo escolhido, mesmo com o timer de troca ativo.",style=MaterialTheme.typography.bodySmall)
        UiText("Os dois timers são independentes e pausam junto com a música.",style=MaterialTheme.typography.bodySmall)
        Toggle("Transição gradual",settings.optBoolean("jukebox_gradual_transition",true)){OndaStore.saveSettings(JSONObject(settings.toString()).put("jukebox_gradual_transition",it))}
        UiText("Sobrepõe a música atual e a próxima. Ajuste os segundos em Configurações → Áudio. Ao parar, reduz nos últimos 10 segundos.",style=MaterialTheme.typography.bodySmall)
        if(nextSong && queue.isEmpty())UiText("Adicione músicas em Fila da Jukebox para ativar a troca automática.",color=MaterialTheme.colorScheme.error,style=MaterialTheme.typography.bodySmall)
        if(switchMinutes>0)UiText(translateUi("Próxima música em")+": "+mediaClock(switchRemaining.toLong()))
        if(stopMinutes>0)UiText(translateUi("Parar em")+": "+mediaClock(stopRemaining.toLong()))
    }},confirmButton={TextButton(enabled=value!=null && value in 1..180 && (!nextSong || queue.isNotEmpty()),onClick={controller.setTimer(value!!,nextSong);close()}){UiText("Ativar")}},dismissButton={TextButton(onClick={controller.setTimer(0,nextSong);close()}){UiText("Desligar este timer")}})
}

@Composable private fun JukeboxQueueDialog(controller:JukeboxController,vm:OndaViewModel,close:()->Unit) {
    val queue by controller.playbackQueue.collectAsStateWithLifecycle()
    val scope=rememberCoroutineScope()
    var query by rememberSaveable {mutableStateOf("")}
    var results by remember {mutableStateOf<List<JSONObject>>(emptyList())}
    var busy by remember {mutableStateOf(false)}
    var message by remember {mutableStateOf("")}
    val files=rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) {uris->uris.forEach {uri->vm.importLocal(uri,"audio") {file->controller.enqueue(JSONObject().put("title",file.nameWithoutExtension).put("_local_source",file.absolutePath))}}}
    AlertDialog(onDismissRequest=close,title={UiText("Fila da Jukebox")},text={Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        UiText("Cada música continua em loop. Use o timer para avançar automaticamente pela fila ou toque em Reproduzir para trocar agora.",style=MaterialTheme.typography.bodySmall)
        OutlinedButton(onClick={files.launch(arrayOf("audio/*"))}){UiText("Adicionar arquivos")}
        OutlinedTextField(query,{query=it},label={UiText("Música, artista ou link")},singleLine=true,modifier=Modifier.fillMaxWidth())
        TextButton(enabled=!busy && query.isNotBlank(),onClick={scope.launch {busy=true;message="";try{results=controller.searchQueue(query);if(results.isEmpty())message="Nenhuma música encontrada."}catch(e:CancellationException){throw e}catch(e:Exception){message=e.message ?: "Falha de pesquisa."}finally{busy=false}}}){UiText(if(busy)"Pesquisando…" else "Pesquisar")}
        if(message.isNotBlank())Text(message)
        results.forEach {record->TextButton(onClick={controller.enqueue(record);results=results.filter {it!==record}}){Text("+ "+record.optString("title"),maxLines=2)}}
        HorizontalDivider()
        if(queue.isEmpty())UiText("Nenhuma música na fila.")
        queue.forEachIndexed {index,record->
            UiText(record.optString("title"),style=MaterialTheme.typography.titleSmall,maxLines=2)
            UiText(when(record.optString("_analysis")){"Pronta"->"Pronta para reproduzir";"Erro"->record.optString("_error");"Analisando"->"Analisando ritmo e trechos…";else->"Aguardando análise"},style=MaterialTheme.typography.bodySmall)
            Row {
                TextButton(enabled=record.optString("_analysis")=="Pronta",onClick={controller.playQueued(index);close()}){UiText("Reproduzir")}
                if(record.optString("_analysis")=="Erro")TextButton(onClick={controller.retryQueued(index)}){UiText("Tentar novamente")}
                TextButton(onClick={controller.removeQueued(index)}){UiText("Remover")}
            }
        }
    }},confirmButton={TextButton(onClick=close){UiText("Pronto")}})
}

@Composable private fun JukeboxGraph(model:JSONObject?,current:Int,phase:Float,playing:Boolean,flow:List<Pair<Int,Int>>,used:Set<Pair<Int,Int>>,variation:Float,smooth:Float,normal:Boolean,onSeek:(Int)->Unit,height:Dp=230.dp,nextIndex:Int=-1,jumpBlend:Float=0f) {
    val colors=MaterialTheme.colorScheme;val rows=model?.optJSONArray("neighbors");val n=max(1,rows?.length() ?: 64)
    val graphColors=jukeboxGraphColors(colors)
    val visible=remember(model,normal,variation){jukeboxVisibleLinks(model,normal,variation)}
    val allowed=remember(visible){visible.toSet()}
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
            for((i,j) in visible) {
                val a=point(i.toDouble());val b=point(j.toDouble())
                drawPath(Path().apply {moveTo(a.x,a.y);quadraticTo(center.x,center.y,b.x,b.y)},colors.primary.copy(alpha=.28f),style=androidx.compose.ui.graphics.drawscope.Stroke(1.dp.toPx()))
            }
            for((i,j) in used) {
                if((i to j) in allowed && j!=(i+1)%n) {
                    val a=point(i.toDouble());val b=point(j.toDouble())
                    drawPath(Path().apply {moveTo(a.x,a.y);quadraticTo(center.x,center.y,b.x,b.y)},colors.primary.copy(alpha=.7f),style=androidx.compose.ui.graphics.drawscope.Stroke(1.8.dp.toPx()))
                }
            }
            for((k,edge) in flow.withIndex()) {
                val (i,j)=edge
                if(j!=(i+1)%n && edge !in allowed)continue
                val ink=colors.primary.copy(alpha=.75f+.25f*(k+1)/flow.size)
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
            val origin=point(current.coerceIn(0,n-1).toDouble())
            val jumped=nextIndex in 0 until n && nextIndex!=(current+1)%n
            val cursor=if(jumped) {
                val destination=point(nextIndex.toDouble());val t=jumpBlend.coerceIn(0f,1f)
                if(t>0f)drawPath(Path().apply {moveTo(origin.x,origin.y);quadraticTo(center.x,center.y,destination.x,destination.y)},colors.primary,style=androidx.compose.ui.graphics.drawscope.Stroke(3.dp.toPx()))
                origin*((1-t)*(1-t))+center*(2*(1-t)*t)+destination*(t*t)
            } else point(current.coerceIn(0,n-1)+phase.toDouble())
            drawCircle(colors.primary,(if(playing)6+2*(1-phase).pow(3) else 6f).dp.toPx(),cursor)
        }

    }
}

internal fun jukeboxVisibleLinks(model:JSONObject?,normal:Boolean,variation:Float=100f):List<Pair<Int,Int>> {
    if(normal)return emptyList()
    val rows=model?.optJSONArray("neighbors") ?: return emptyList()
    return buildList {
        for(i in 0 until rows.length()) {
            val row=rows.optJSONArray(i) ?: continue
            val count=kotlin.math.ceil(row.length()*(.2+.8*variation.coerceIn(0f,100f)/100)).toInt().coerceAtLeast(1).coerceAtMost(row.length())
            for(j in 0 until count)add(i to row.getInt(j))
        }
    }
}

// Graph geometry must remain visible when pure-black mode hides UI separators.
internal fun jukeboxGraphColors(colors:ColorScheme):Pair<Color,Color> {
    val dark=colors.surface.luminance()<.25f
    val ring=lerp(colors.surface,colors.onSurface,if(dark).68f else .55f)
    val accent=lerp(colors.primary,colors.onSurface,if(dark).15f else 0f)
    val links=lerp(colors.surface,accent,if(dark).7f else .4f)
    return ring to links
}
