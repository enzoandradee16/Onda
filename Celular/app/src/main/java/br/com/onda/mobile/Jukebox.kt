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
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.unit.dp
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.*
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import org.json.JSONObject
import java.util.UUID
import kotlin.math.*

internal data class JukeboxState(val title:String="Escolha sua música.",val message:String="Abra um arquivo ou pesquise uma música para começar.",val model:JSONObject?=null,val records:List<JSONObject> = emptyList(),val busy:Boolean=false,val playing:Boolean=false,val paused:Boolean=false,val index:Int=0,val elapsed:Double=0.0,val jumps:Int=0)

internal class JukeboxController(private val context:Context,private val scope:CoroutineScope,var stopOtherAudio:()->Unit) {
    val state=MutableStateFlow(JukeboxState())
    @Volatile var variation=45f
    @Volatile var smooth=35f
    @Volatile var normal=false
    private val pendingSeek=AtomicInteger(-1)
    fun seek(index:Int) {
        val n=state.value.model?.optJSONArray("neighbors")?.length() ?: return
        if(index !in 0 until n || state.value.busy)return
        pendingSeek.set(index);state.update {it.copy(index=index)}
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
        state.value=state.value.copy(model=model,playing=true,paused=false,message="Reproduzindo…",elapsed=0.0,jumps=0)
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
                while(isActive && own==revision) {
                    while(state.value.paused && isActive)delay(20)
                    ensureActive()
                    val config=JSONObject().put("session",id).put("variation",variation).put("smooth",smooth).put("volume",100).put("normal",normal)
                    val seek=pendingSeek.getAndSet(-1)
                    if(seek>=0){output.pause();output.flush();output.play();config.put("seek",seek)}
                    val part=call("jukebox_chunk",config,id)
                    val data=Base64.decode(part.getString("pcm"),Base64.NO_WRAP);var offset=0
                    while(offset<data.size && isActive && own==revision) {
                        while(state.value.paused && isActive)delay(20)
                        ensureActive()
                        val count=output.write(data,offset,min(4096,data.size-offset),AudioTrack.WRITE_NON_BLOCKING)
                        require(count>=0){"A saída de áudio foi interrompida."}
                        if(count==0)delay(5) else offset+=count
                    }
                    if(own==revision)state.update {current->if(own==revision)current.copy(index=part.optInt("index"),jumps=part.optInt("jumps"),elapsed=(output.playbackHeadPosition.toLong() and 0xffffffffL)/44100.0) else current}
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
        state.value=state.value.copy(busy=false,playing=false,paused=false,index=0,message=if(state.value.playing||state.value.busy)"Reprodução encerrada." else state.value.message)
    }
    fun close()=stop()
}

@Composable internal fun PlaybackPage(vm:OndaViewModel) {
    var mode by rememberSaveable {mutableStateOf(0)}
    val jukeboxState by vm.jukebox.state.collectAsStateWithLifecycle()
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
        PageTitle("Reprodução e efeitos","Sua música, de um novo jeito.")
        TabRow(selectedTabIndex=mode) {
            listOf("Efeitos","Jukebox infinito").forEachIndexed {index,label->Tab(selected=index==mode,onClick={vm.stopPreview(!OndaStore.settings.value.optBoolean("jukebox_background"));mode=index;if(index==1 && incomingSource.isNotBlank() && incomingSource!=jukeboxState.model?.optString("source"))vm.jukebox.prepare(incomingSource)},text={UiText(label)})}
        }
        if(mode==0)EffectsPage(vm,heading=false) else JukeboxPage(vm)
    }
}

@Composable private fun JukeboxPage(vm:OndaViewModel) {
    val controller=vm.jukebox;val state by controller.state.collectAsStateWithLifecycle()
    var query by rememberSaveable {mutableStateOf("")}
    var variation by rememberSaveable {mutableFloatStateOf(controller.variation)}
    var smooth by rememberSaveable {mutableFloatStateOf(controller.smooth)}
    var normal by rememberSaveable {mutableStateOf(controller.normal)}
    LaunchedEffect(variation,smooth,normal) {controller.variation=variation;controller.smooth=smooth;controller.normal=normal}
    val chooser=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"audio") {file->controller.prepare(file.absolutePath)}}
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        OutlinedButton(onClick={chooser.launch(arrayOf("audio/*"))},enabled=!state.busy){UiText("Abrir arquivo")}
        OutlinedTextField(query,{query=it},label={UiText("Pesquise uma música ou cole um link")},singleLine=true,modifier=Modifier.fillMaxWidth())
        Button(onClick={controller.search(query)},enabled=query.isNotBlank()&&!state.busy){UiText("Pesquisar")}
        if(state.busy){LinearProgressIndicator(Modifier.fillMaxWidth());TextButton(onClick=controller::stop){UiText("Cancelar")}}
        state.records.forEach {record->
            val artists=record.optJSONArray("artists")?.let {a->(0 until a.length()).joinToString(", "){a.getString(it)}}.orEmpty()
            OutlinedButton(onClick={controller.prepare(record=record)},modifier=Modifier.fillMaxWidth()) {UiText(listOf(record.optString("title"),artists).filter {it.isNotBlank()}.joinToString(" · "))}
        }
        val embeddedCover=state.model?.optString("media_cover").orEmpty()
        val cover=remember(embeddedCover,state.model?.optString("cover_url")) {
            if(embeddedCover.isNotBlank())runCatching {Base64.decode(embeddedCover,Base64.DEFAULT)}.getOrNull()
            else state.model?.optString("cover_url")?.takeIf {it.isNotBlank()}
        }
        Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            Box(Modifier.size(88.dp).clip(RoundedCornerShape(8.dp)),contentAlignment=androidx.compose.ui.Alignment.Center) {
                if(cover!=null)coil.compose.AsyncImage(model=cover,contentDescription=null,contentScale=ContentScale.Crop,modifier=Modifier.fillMaxSize())
                else UiText("♪",style=MaterialTheme.typography.headlineLarge)
            }
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                if(state.title.isNotBlank())UiText(state.title,style=MaterialTheme.typography.titleMedium)
                state.model?.optString("media_artist")?.takeIf {it.isNotBlank()}?.let {UiText(it,style=MaterialTheme.typography.bodyMedium)}
                state.model?.optString("album")?.takeIf {it.isNotBlank()}?.let {UiText(it,style=MaterialTheme.typography.bodySmall)}
            }
        }
        UiText(if(state.paused)"Pausado." else state.message,style=MaterialTheme.typography.bodySmall)
        JukeboxGraph(state.model,state.index,variation,smooth,normal,controller::seek)
        UiText("Como a música se transforma",style=MaterialTheme.typography.titleMedium)
        UiText("Variação")
        RoundSlider(variation,{variation=it;controller.variation=it},valueRange=0f..100f)
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){UiText("Mais fiel");UiText("Mais saltos")}
        UiText("Transição suave")
        RoundSlider(smooth,{smooth=it;controller.smooth=it},valueRange=0f..100f)
        UiText("A análise fica salva para os próximos usos.",style=MaterialTheme.typography.bodySmall)
        UiText("Os saltos dependem de trechos compatíveis. A detecção de batidas é uma estimativa.",style=MaterialTheme.typography.bodySmall)
        Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            Button(onClick=controller::playPause,enabled=state.model!=null&&!state.busy){UiText(if(state.playing)if(state.paused)"Retomar" else "Pausar" else "Reproduzir")}
            OutlinedButton(onClick=controller::stop){UiText("Parar")}
        }
        Toggle("Reprodução normal",normal){normal=it;controller.normal=it}
        UiText(translateUi("Tempo ouvido: {time} · Saltos: {count}").replace("{time}",mediaClock(state.elapsed.toLong())).replace("{count}",state.jumps.toString()))
    }
}

@Composable private fun JukeboxGraph(model:JSONObject?,current:Int,variation:Float,smooth:Float,normal:Boolean,onSeek:(Int)->Unit) {
    val colors=MaterialTheme.colorScheme;val rows=model?.optJSONArray("neighbors");val n=max(1,rows?.length() ?: 64)
    val visible=remember(model,variation,normal){jukeboxVisibleLinks(model,variation,normal)}
    Box(Modifier.fillMaxWidth().height(300.dp),contentAlignment=androidx.compose.ui.Alignment.Center) {
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
            fun point(index:Int):Offset {val angle=index.toDouble()/n*2*PI-PI/2;return center+Offset((cos(angle)*radius).toFloat(),(sin(angle)*radius).toFloat())}
            val strength=if(normal)0f else (variation/100).coerceIn(0f,1f)
            for((i,j) in visible) {
                val a=point(i);val b=point(j)
                drawPath(Path().apply {moveTo(a.x,a.y);quadraticTo(center.x,center.y,b.x,b.y)},colors.primary.copy(alpha=.15f+.55f*strength),style=androidx.compose.ui.graphics.drawscope.Stroke(1f+smooth/100))
            }
            val hot=visible.filter {it.first==current}.map {it.second}.toSet()
            for(i in 0 until n step max(1,n/150))drawCircle(if(i in hot)colors.primary else colors.outline,3.dp.toPx(),point(i))
            drawCircle(colors.primary,6.dp.toPx(),point(current.coerceIn(0,n-1)))
        }
        Column(horizontalAlignment=androidx.compose.ui.Alignment.CenterHorizontally){UiText("Jukebox infinito",style=MaterialTheme.typography.titleMedium);Text("∞",style=MaterialTheme.typography.headlineLarge,color=colors.primary)}
    }
}

internal fun jukeboxVisibleLinks(model:JSONObject?,variation:Float,normal:Boolean):List<Pair<Int,Int>> {
    val rows=model?.optJSONArray("neighbors") ?: return emptyList()
    val limit=if(normal)0 else ceil(90*(variation/100).coerceIn(0f,1f)).toInt()
    if(limit==0)return emptyList()
    val links=buildList {for(i in 0 until rows.length()){val row=rows.optJSONArray(i) ?: continue;for(k in 0 until row.length())add(i to row.getInt(k))}}
    return links.filterIndexed {index,_->index % max(1,links.size/limit)==0}.take(limit)
}
