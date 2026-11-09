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
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.input.pointer.pointerInput
import java.util.concurrent.atomic.AtomicInteger
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.graphics.graphicsLayer
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
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import org.json.JSONObject
import java.util.UUID
import kotlin.math.*

internal data class JukeboxState(val title:String="Escolha suas músicas.",val message:String="Abra arquivos, pesquise músicas ou adicione álbuns e playlists à fila.",val model:JSONObject?=null,val records:List<JSONObject> = emptyList(),val busy:Boolean=false,val playing:Boolean=false,val paused:Boolean=false,val index:Int=0,val phase:Float=0f,val flow:List<Pair<Int,Int>> = emptyList(),val used:Set<Pair<Int,Int>> = emptySet(),val elapsed:Double=0.0,val jumps:Int=0,val nextIndex:Int=-1,val jumpBlend:Float=0f,val effectsPending:Boolean=false,val effectsError:String="",val restoredSeconds:Double=0.0,val playbackError:String="")

internal class JukeboxController(private val context:Context,private val scope:CoroutineScope,var stopOtherAudio:()->Unit,private val callOverride:(suspend (String,JSONObject,String)->JSONObject)?=null) {
    val state=MutableStateFlow(JukeboxState())
    val presentationState=state.map {it.copy(index=0,phase=0f,flow=emptyList(),used=emptySet(),elapsed=0.0,jumps=0,nextIndex=-1,jumpBlend=0f)}
        .distinctUntilChanged().stateIn(scope,kotlinx.coroutines.flow.SharingStarted.WhileSubscribed(5000),state.value)
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
    private var normalEndGain=1f
    internal val audioReady=MutableStateFlow(false)
    val streamBuffer=MutableStateFlow(0.0 to 0.0)
    val volume=MutableStateFlow(1f)
    fun setVolume(value:Float){volume.value=value.coerceIn(0f,1f);applyGain()}
    private var streaming:AndroidStreamPlayback?=null
    private var outgoingStream:AndroidStreamPlayback?=null
    private class PcmTail(val output:AudioTrack,val job:Job?,val identity:String) {
        fun volume(value:Float){runCatching {output.setVolume(value)}}
        fun close(){if(identity.isNotBlank())MobileEngine.cancel(identity);job?.cancel()}
    }
    @Volatile private var outgoingPcm:PcmTail?=null
    private var streamFade:Job?=null
    private var streamGain=1f
    private fun finishStreamOverlap() {
        val old=outgoingStream;val pcm=outgoingPcm
        outgoingStream=null;outgoingPcm=null
        val fade=streamFade;streamFade=null
        fade?.cancel();old?.close();pcm?.close();streamGain=1f;applyGain()
    }
    private var shuffleOrder=emptyList<String>()
    fun setQueueShuffle(enabled:Boolean) {
        if(queueShuffle.value==enabled)return
        val rows=playbackQueue.value
        val start=nextQueueIndex.coerceIn(0,rows.size)
        playbackQueue.value=if(enabled) {
            shuffleOrder=rows.map {it.optString("_queue_id")}
            rows.take(start)+rows.drop(start).shuffled()
        } else {
            val order=shuffleOrder.withIndex().associate {it.value to it.index}
            rows.take(start)+rows.drop(start).sortedBy {order[it.optString("_queue_id")] ?: Int.MAX_VALUE}
        }
        queueShuffle.value=enabled
        reprioritizeQueue()
        checkpointPosition()
    }
    private fun reprioritizeQueue() {
        val next=autoplayQueueId.ifBlank {priorityQueueId}.ifBlank {normalNextIndex()?.let {playbackQueue.value.getOrNull(it)?.optString("_queue_id")}.orEmpty()}
        if(next.isNotBlank() && !preparedModels.containsKey(next) && queuePreparing.isNotBlank() && queuePreparing!=next) {
            cancelQueuePreparation()
        }
        startQueuePreparation()
    }
    private var sourceChange:Job?=null
    private var sourceChangeId=""
    private var checkpoint:Job?=null
    private val seekEpoch=AtomicInteger(0)
    private fun canStream():Boolean {
        val fx=effects.value
        val changesAudio=fx.optBoolean("enabled") && (fx.optInt("speed",85)!=100 || fx.optInt("reverb",25)!=0)
        return normal && !changesAudio && !OndaStore.settings.value.optJSONObject("jukebox_equalizer").let {it?.optBoolean("enabled")==true}
    }
    private fun checkpointPosition(){checkpoint?.cancel();checkpoint=scope.launch {delay(250);savePlaybackSession()}}
    private val appliedGain=AppliedAudioGain()
    private fun applyGain(){
        streaming?.volume(volume.value*minOf(stopGain,switchGain,startGain)*streamGain)
        val output=track ?: return
        val value=volume.value*minOf(stopGain,switchGain,startGain,if(normal&&gradual())normalEndGain else 1f)
        runCatching {appliedGain.apply(output,value){output.setVolume(it)}}
    }
    private fun normalRemaining():Double {
        val current=state.value;val model=current.model ?: return Double.POSITIVE_INFINITY
        val beats=model.optJSONArray("beats") ?: return Double.POSITIVE_INFINITY
        val a=beats.optDouble(current.index,0.0);val b=beats.optDouble(current.index+1,a)
        val speed=if(effects.value.optBoolean("enabled")&&!current.effectsPending)effects.value.optInt("speed",100)/100.0 else 1.0
        return ((model.optDouble("duration")-a-(b-a)*current.phase)/speed.coerceAtLeast(.5)).coerceAtLeast(0.0)
    }
    private fun normalNextIndex():Int? {
        val current=nextQueueIndex-1
        if(queueRepeat.value=="Uma"&&current in playbackQueue.value.indices)return current
        val next=if(nextQueueIndex>=playbackQueue.value.size&&queueRepeat.value=="Todas")0 else nextQueueIndex
        return next.takeIf {it in playbackQueue.value.indices}
    }
    private fun normalTransition() {
        if(outgoingStream!=null || outgoingPcm!=null || streamFade!=null)return
        if(!normal||!gradual()||!state.value.playing||state.value.paused)return
        val target=normalNextIndex()
        val ready=target!=null&&preparedModels.containsKey(playbackQueue.value[target].optString("_queue_id"))
        normalEndGain=if(!ready)(normalRemaining()/transitionSeconds()).toFloat().coerceIn(0f,1f) else 1f
        applyGain()
        if(switchMinutes.value>0||target==null||normalRemaining()>transitionSeconds()+.5||switchRequest.get()!=null||switchModels.isNotEmpty()||autoplayQueueId.isNotBlank())return
        if(!preparedModels.containsKey(playbackQueue.value[target].optString("_queue_id")))return
        if(queueRepeat.value=="Uma")playQueued(target) else nextTrack()
    }
    val queueRepeat=MutableStateFlow("Desativada")
    val queueShuffle=MutableStateFlow(false)
    val currentQueueId=MutableStateFlow("")
    private var queueCursor=-1
    private val queueIndex=PlaybackQueueIndex()
    val nextQueueIndex:Int get()=(queueIndex.index(playbackQueue.value,currentQueueId.value).takeIf {it>=0} ?: queueCursor)+1
    val pendingPlaybackId=MutableStateFlow("")
    private var autoplayQueueId:String
        get()=pendingPlaybackId.value
        set(value){pendingPlaybackId.value=value}
    fun previousTrack(){val current=state.value;if(sessionSeconds(current.model,current.index,current.phase.toDouble())>=3.0){seek(0);return};val index=nextQueueIndex-1;if(index>0)playQueued(index-1) else seek(0)}
    fun nextTrack(){
        if(autoplayQueueId.isNotBlank() || switchRequest.get()!=null)return
        val rows=playbackQueue.value.toMutableList()
        val target=nextPlaybackIndex(rows.size,nextQueueIndex-1,queueRepeat.value)
        if(target in rows.indices){
            playQueued(target)
        } else {setTimer(0,true);state.update {it.copy(message="Fim da fila de reprodução. A música atual continua.")}}}
    fun moveQueued(index:Int,direction:Int){val rows=playbackQueue.value;val current=nextQueueIndex-1;val target=if(index>current && current>=0)(index+direction).coerceAtLeast(current+1) else index+direction;if(index !in rows.indices||target !in rows.indices)return;queueCursor=playbackCursorAfterMove(current,index,target);playbackQueue.value=movePlaybackEntry(rows,index,target-index);reprioritizeQueue()}
    fun clearPlaybackQueue(){cancelQueuePreparation();queueUndoJob?.cancel();removedQueueEntry=null;canUndoQueueRemoval.value=false;autoplayQueueId="";priorityQueueId="";switchRequest.set(null);if(queuePreparationId.isNotBlank())MobileEngine.cancel(queuePreparationId);playbackQueue.value=emptyList();preparedModels.clear();currentQueueId.value="";queueCursor=-1}
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
                val head=playbackQueue.value.getOrNull(if(nextQueueIndex>=playbackQueue.value.size&&queueRepeat.value=="Todas")0 else nextQueueIndex)
                switchGain=1f
                if(!nextSong)stopGain=if(gradual())(remaining/10).toFloat().coerceIn(0f,1f) else 1f
                applyGain()
                if(remaining<=0) {
                    if(!nextSong){stop();return@launch}
                    if(queueRepeat.value!="Uma" && (head==null || head.optString("_analysis")=="Erro")) {
                        state.update {it.copy(message=if(head==null)"A fila de reprodução está vazia. O timer de troca foi desligado." else "A próxima música não pôde ser preparada. Confira a fila de reprodução.")}
                        setTimer(0,true);return@launch
                    }
                    // Keep the current song audible until preparation finishes.
                    if(queueRepeat.value!="Uma")nextTrack()
                    progress.restart();last=android.os.SystemClock.elapsedRealtime()
                }
            }
        }
        if(nextSong)switchTask=job else timerTask=job
    }
    private val preparedModels=mutableMapOf<String,JSONObject>()
    private var queueWorker:Job?=null
    private var queuePreparing=""
    private var queuePreparationId=""
    private var queueEffectsId = ""
    private var queuePreparationEpoch=0
    private fun cancelQueuePreparation() {
        val obsolete=queuePreparing
        queuePreparationEpoch++
        if(queuePreparationId.isNotBlank())MobileEngine.cancel(queuePreparationId)
        cancelQueueEffects()
        queueWorker?.cancel();queueWorker=null;queuePreparing="";queuePreparationId=""
        if(obsolete.isNotBlank() && !preparedModels.containsKey(obsolete))updateQueue(obsolete,"Pendente")
    }
    private fun cancelQueueEffects() {
        if (queueEffectsId.isNotBlank()) MobileEngine.cancel(queueEffectsId)
    }
    private var priorityQueueId=""
    private fun preparationWindow():Set<String> {
        val rows=playbackQueue.value
        val current=nextQueueIndex-1
        return buildSet {
            for(index in maxOf(0,current-1)..minOf(rows.lastIndex,current+preparationAhead(OndaStore.settings.value)))add(rows[index].optString("_queue_id"))
            normalNextIndex()?.let {rows.getOrNull(it)?.optString("_queue_id")?.let {id->add(id)}}
            if(autoplayQueueId.isNotBlank())add(autoplayQueueId)
            if(priorityQueueId.isNotBlank())add(priorityQueueId)
            switchRequest.get()?.let {add(it.row.optString("_queue_id"))}
            switchModels.values.forEach {add(it.row.optString("_queue_id"))}
        }
    }
    private fun trimPreparedModels(wanted:Set<String>) {
        val removed=preparedModels.keys.filter {it !in wanted}
        removed.forEach {preparedModels.remove(it);updateQueue(it,"Pendente")}
    }
    private fun updateQueue(id:String,status:String,error:String="") {
        playbackQueue.update {rows->rows.map {if(it.optString("_queue_id")==id && (it.optString("_analysis")!=status || it.optString("_error")!=error))copyJsonObject(it).put("_analysis",status).put("_error",error) else it}}
    }
    private fun prepareConfig(source:String,record:JSONObject?,url:String=""):JSONObject {
        val direct=record?.optBoolean("_jukebox_direct")==true
        return OndaStore.config().put("stream",canStream()).put("source",source).put("url",if(direct)record!!.getString("source_url") else url).apply {if(record!=null&&!direct)put("record",record)}
    }
    private fun startQueuePreparation() {
        if(queueWorker?.isActive==true)return
        playbackQueue.update {rows->rows.map {row->
            val id=row.optString("_queue_id")
            when {
                preparedModels.containsKey(id)->if(row.optString("_analysis")=="Pronta" && row.optString("_error").isBlank())row else copyJsonObject(row).put("_analysis","Pronta").put("_error","")
                row.optString("_analysis") in listOf("Analisando","Preparando","Pronta")->copyJsonObject(row).put("_analysis","Pendente")
                else->row
            }
        }}
        val owner=++queuePreparationEpoch
        queueWorker=scope.launch {
            while(isActive && owner==queuePreparationEpoch) {
                val wanted=preparationWindow()
                trimPreparedModels(wanted)
                val pending=playbackQueue.value.filter {it.optString("_analysis")=="Pendente" && it.optString("_queue_id") in wanted}
                val row=pending.firstOrNull {it.optString("_queue_id")==autoplayQueueId}
                    ?: pending.firstOrNull {it.optString("_queue_id")==priorityQueueId}
                    ?: pending.firstOrNull {it.optString("_queue_id")==playbackQueue.value.getOrNull(normalNextIndex() ?: -1)?.optString("_queue_id")}
                    ?: pending.firstOrNull() ?: break
                val id=row.getString("_queue_id");val operationId="jukebox-preload-$id-$owner";queuePreparing=id;queuePreparationId=operationId;updateQueue(id,"Analisando")
                try {
                    var model=withContext(Dispatchers.IO) {restoreQueueModel(row)} ?: call("jukebox_prepare",prepareConfig(row.optString("_local_source"),row.takeUnless {it.cleanString("_local_source").isNotBlank() && !it.optBoolean("_catalog_source")}),operationId)
                    if(model.has("_stream") && state.value.playing && id!=autoplayQueueId) {
                        try {withTimeoutOrNull(6000){StreamAudioCache.prefetch(context,model)}}
                        catch(cancelled:CancellationException){throw cancelled}
                        catch(error:Exception){android.util.Log.w("ONDA-preload","Optional streaming preload failed: ${error.javaClass.simpleName}")}
                    }
                    if (model.has("_stream") && !canStream()) {
                        model = call("jukebox_transfer_prepare", OndaStore.config().put("model", model), operationId)
                    }
                    if(!model.has("_stream")) {
                        while(isActive) {
                            val currentEffects = effects.value
                            val snapshot = copyJsonObject(currentEffects)
                            if(snapshot.optBoolean("enabled")) {
                                val effectsId = "jukebox-queue-effects-${UUID.randomUUID()}"
                                queueEffectsId = effectsId
                                try {
                                    val prepared = call("jukebox_effects", JSONObject().put("cache", model.getString("cache")).put("effects", snapshot), effectsId)
                                    if (currentEffects === effects.value) {
                                        check(prepared.optString("error_detail").isBlank()) { prepared.optString("error_detail") }
                                    }
                                } catch (error: Exception) {
                                    ensureActive()
                                    if (currentEffects === effects.value) throw error
                                } finally {
                                    if (queueEffectsId == effectsId) queueEffectsId = ""
                                }
                            }
                            if (currentEffects === effects.value) break
                        }
                    }
                    if(isActive && owner==queuePreparationEpoch && playbackQueue.value.any {it.optString("_queue_id")==id}) {
                        preparedModels[id]=model
                        playbackQueue.update {rows->rows.map {entry->
                            if(entry.optString("_queue_id")!=id)entry else copyJsonObject(entry).apply {
                                put("_cover",model.optString("media_cover"))
                                put("_prepared_cache",preparedQueueReference(model))
                                put("duration_ms",model.optDouble("duration",0.0)*1000)
                                if(has("_local_source") && model.cleanString("media_title").isNotBlank())put("title",model.getString("media_title"))
                                if(model.cleanString("cover_url").isNotBlank())put("cover_url",model.getString("cover_url"))
                                if(stringList("artists").isBlank())put("artists",org.json.JSONArray(listOf(model.cleanString("media_artist")).filter {it.isNotBlank()}))
                                if(cleanString("album").isBlank())put("album",model.cleanString("album"))
                            }
                        }}
                        updateQueue(id,"Pronta")
                        if(priorityQueueId==id)priorityQueueId=""
                        if(autoplayQueueId==id){autoplayQueueId="";playQueued(playbackQueue.value.indexOfFirst {it.optString("_queue_id")==id})}
                    }
                } catch(e:CancellationException){if(owner==queuePreparationEpoch)updateQueue(id,"Pendente");throw e}
                catch(e:Exception){
                    if(owner!=queuePreparationEpoch)throw CancellationException()
                    val message=uiExceptionMessage(e,"Não foi possível analisar.")
                    updateQueue(id,"Erro",message)
                    if(autoplayQueueId==id){autoplayQueueId="";state.update {it.copy(message=message,playbackError=message)}}
                    if(priorityQueueId==id)priorityQueueId=""
                }
                finally {if(owner==queuePreparationEpoch && queuePreparing==id){queuePreparing="";queuePreparationId=""}}
            }
        }
    }
    fun enqueue(record:JSONObject) {
        enqueueAll(listOf(record),manual=true)
    }
    fun playRecord(record:JSONObject) {
        enqueueAll(listOf(record),manual=true,playNow=true)
    }
    internal fun enqueueAll(records:List<JSONObject>,manual:Boolean=false,playNow:Boolean=false):Int {
        val accepted=records.take((5000-playbackQueue.value.size).coerceAtLeast(0)).map {record->copyJsonObject(record).put("_queue_id",UUID.randomUUID().toString()).put("_analysis","Pendente").put("_queue_manual",manual)}
        if(accepted.isNotEmpty()){
            playbackQueue.update {rows->
                var insertion=if(manual||playNow)nextQueueIndex.coerceIn(0,rows.size) else rows.size
                if(manual&&!playNow)while(insertion<rows.size && rows[insertion].optBoolean("_queue_manual"))insertion++
                rows.toMutableList().apply {addAll(insertion,accepted)}
            }
            if(playNow)playQueued(nextQueueIndex) else reprioritizeQueue()
        }
        if(accepted.size<records.size)state.update {it.copy(message="Limite de 5.000 músicas na fila de reprodução. Remova músicas antes de adicionar outras.")}
        return accepted.size
    }
    fun retryQueued(index:Int,autoplay:Boolean=false){if(!autoplay)autoplayQueueId="";playbackQueue.value.getOrNull(index)?.optString("_queue_id")?.let {priorityQueueId=it;preparedModels.remove(it);updateQueue(it,"Pendente");startQueuePreparation()}}
    val canUndoQueueRemoval=MutableStateFlow(false)
    private var removedQueueEntry:Pair<Int,JSONObject>?=null
    private var queueUndoJob:Job?=null
    fun undoQueueRemoval() {
        val (index,record)=removedQueueEntry ?: return
        if(playbackQueue.value.size>=5000)return
        queueUndoJob?.cancel();removedQueueEntry=null;canUndoQueueRemoval.value=false
        val restored=copyJsonObject(record).put("_queue_id",UUID.randomUUID().toString()).put("_analysis","Pendente")
        val position=index.coerceAtMost(playbackQueue.value.size)
        if(position<=queueCursor)queueCursor++
        playbackQueue.update {it.toMutableList().apply {add(position,restored)}}
        startQueuePreparation()
    }
    fun removeQueued(index:Int) {
        val id=playbackQueue.value.getOrNull(index)?.optString("_queue_id") ?: return
        removedQueueEntry=index to copyJsonObject(playbackQueue.value[index])
        canUndoQueueRemoval.value=true
        queueUndoJob?.cancel()
        queueUndoJob=scope.launch {delay(8000);removedQueueEntry=null;canUndoQueueRemoval.value=false}
        queueCursor=nextQueueIndex-1;if(index<=queueCursor)queueCursor--
        playbackQueue.update {rows->rows.filter {it.optString("_queue_id")!=id}}
        preparedModels.remove(id)
        switchRequest.get()?.takeIf {it.row.optString("_queue_id")==id}?.let {switchRequest.compareAndSet(it,null)}
        if(autoplayQueueId==id)autoplayQueueId=""
        if(priorityQueueId==id)priorityQueueId=""
        if (queuePreparing == id) cancelQueuePreparation()
        startQueuePreparation()
    }
    private data class TrackSwitch(val row:JSONObject,val model:JSONObject,val seconds:Int)
    private val switchRequest=java.util.concurrent.atomic.AtomicReference<TrackSwitch?>(null)
    private val switchModels=java.util.concurrent.ConcurrentHashMap<String,TrackSwitch>()
    private fun transitionSeconds()=OndaStore.settings.value.optInt("jukebox_transition_seconds",2).coerceIn(1,10)
    fun playQueued(index:Int) {
        val row=playbackQueue.value.getOrNull(index) ?: return
        state.update {it.copy(playbackError="")}
        val model=preparedModels[row.optString("_queue_id")] ?: run {autoplayQueueId=row.optString("_queue_id");if(row.optString("_analysis")=="Erro")retryQueued(index,autoplay=true) else reprioritizeQueue();return}
        if(model.has("_stream") && !canStream()) {
            val id=row.optString("_queue_id");autoplayQueueId=id;preparedModels.remove(id);updateQueue(id,"Pendente");startQueuePreparation();return
        }
        if(!model.has("_stream") && !java.io.File(model.optString("cache"),"analysis.json").isFile()) {
            val id=row.optString("_queue_id")
            autoplayQueueId=id
            preparedModels.remove(id)
            updateQueue(id,"Pendente");startQueuePreparation();return
        }
        autoplayQueueId=""
        if(outgoingStream!=null || outgoingPcm!=null || streamFade!=null)finishStreamOverlap()
        if(state.value.playing && !state.value.paused && task?.isActive==true && track!=null && audioReady.value && !model.has("_stream") && state.value.model?.has("_stream")!=true) {
            val request=TrackSwitch(row,model,if(gradual())transitionSeconds() else 0)
            // Keep the most recent navigation request while a crossfade finishes.
            switchRequest.set(request)
            return
        }
        val overlap=state.value.playing && !state.value.paused && gradual()
        val previous=streaming.takeIf {overlap}
        if(previous!=null)streaming=null
        if(overlap && model.has("_stream") && track!=null && task?.isActive==true) {
            outgoingPcm=PcmTail(track!!,task,identity);track=null;task=null;identity=""
        }
        outgoingStream=previous
        val keep=previous!=null || outgoingPcm!=null
        stop(clearTimer=false,keepAudioFocus=keep,keepOverlap=keep)
        currentQueueId.value=row.optString("_queue_id");queueCursor=index
        val beats=model.optJSONArray("beats")
        val restored=row.optDouble("_restore_seconds",0.0)
        val restoredIndex=if(beats==null)0 else (0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=restored} ?: 0
        row.remove("_restore_seconds")
        val begin=beats?.optDouble(restoredIndex,0.0) ?: 0.0
        val end=beats?.optDouble(restoredIndex+1,begin) ?: begin
        val restoredPhase=if(end>begin)((restored-begin)/(end-begin)).coerceIn(0.0,.999999).toFloat() else 0f
        state.value=JukeboxState(title=model.optString("media_title").ifBlank {model.optString("title")},model=model,index=restoredIndex,phase=restoredPhase)
        startQueuePreparation()
        playPause()
    }
    suspend fun searchQueue(query:String,id:String="jukebox-queue-"+UUID.randomUUID()):List<JSONObject> {
        return resolveQueueInput(query,id).optJSONArray("tracks")?.objects().orEmpty()
    }
    suspend fun resolveQueueInput(query:String,id:String="jukebox-input-"+UUID.randomUUID()):JSONObject {
        return call("playback_input",OndaStore.config().put("query",query).put("provider",OndaStore.settings.value.optString("provider","Deezer")),id)
    }
    @Volatile var variation=45f
    @Volatile var smooth=35f
    val normalPlayback=MutableStateFlow(true)
    val effects=MutableStateFlow(JSONObject().put("enabled",false).put("speed",85).put("reverb",25).put("keep_pitch",false))
    private var effectPreparation:Job?=null
    private var effectPreparationId=""
    fun setEffects(key: String, value: Any) {
        if (effects.value.opt(key) == value) return
        effects.value = JSONObject(effects.value.toString()).put(key, value)
        prewarmEffects()
        val obsolete = preparedModels.keys.filter { it != currentQueueId.value }
        obsolete.forEach {
            preparedModels.remove(it)
            updateQueue(it, "Pendente")
        }
        cancelQueueEffects()
        startQueuePreparation()
    }
    private fun restartPreparationMode() {
        if(state.value.model==null && queueWorker?.isActive!=true)return
        cancelQueuePreparation()
        if(!canStream())preparedModels.keys.toList().filter {it!=currentQueueId.value && preparedModels[it]?.has("_stream")==true}.forEach {preparedModels.remove(it);updateQueue(it,"Pendente")}
        startQueuePreparation()
    }
    private fun reconcileSource() {
        sourceChange?.cancel();sourceChange=null
        if(sourceChangeId.isNotBlank())MobileEngine.cancel(sourceChangeId)
        sourceChangeId=""
        val current=state.value
        val original=current.model ?: return
        val row=playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value} ?: return
        val remoteSource=row.cleanString("source_url").let {it.startsWith("https://") || it.startsWith("http://")} && (row.cleanString("_local_source").isBlank() || row.optBoolean("_catalog_source"))
        val wantStream=canStream() && remoteSource
        if(original.has("_stream")==wantStream){state.update {it.copy(effectsPending=false)};return}
        val own=revision
        val queueId=currentQueueId.value
        state.update {it.copy(effectsPending=true,effectsError="")}
        sourceChange=scope.launch {
            delay(350)
            val id="playback-source-"+UUID.randomUUID();sourceChangeId=id
            try {
                val model=if(wantStream)call("jukebox_stream_resolve",OndaStore.config().put("record",row),id)
                    else call("jukebox_transfer_prepare",OndaStore.config().put("model",original),id)
                if(!wantStream && effects.value.optBoolean("enabled")) {
                    val prepared=call("jukebox_effects",OndaStore.config().put("cache",model.getString("cache")).put("effects",copyJsonObject(effects.value)),id)
                    check(prepared.optString("error_detail").isBlank()){prepared.optString("error_detail")}
                }
                ensureActive()
                if(own!=revision || currentQueueId.value!=queueId || state.value.model!==original)return@launch
                val latest=state.value
                val seconds=sessionSeconds(latest.model,latest.index,latest.phase.toDouble())
                val continuePlaying=latest.playing && !latest.paused
                sourceChange=null;sourceChangeId=""
                stop(clearTimer=false)
                preparedModels[queueId]=model
                playbackQueue.update {rows->rows.map {if(it.optString("_queue_id")==queueId)copyJsonObject(it).put("_prepared_cache",preparedQueueReference(model)).put("_analysis","Pronta") else it}}
                val beats=model.optJSONArray("beats")
                val index=if(beats==null)0 else (0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=seconds} ?: 0
                val a=beats?.optDouble(index,0.0) ?: 0.0;val b=beats?.optDouble(index+1,a) ?: a
                state.value=JukeboxState(title=model.optString("media_title").ifBlank {latest.title},model=model,index=index,phase=if(b>a)((seconds-a)/(b-a)).coerceIn(0.0,.999999).toFloat() else 0f)
                if(continuePlaying)playPauseInternal(false)
                checkpointPosition()
            } catch(cancelled:CancellationException){throw cancelled}
            catch(error:Exception){if(own==revision)state.update {it.copy(effectsPending=false,effectsError=uiExceptionMessage(error,"Não foi possível preparar os efeitos desta música."))}}
            finally {if(sourceChangeId==id)sourceChangeId=""}
        }
    }

    private fun startStreaming(model:JSONObject) {
        val before=state.value
        val seconds=sessionSeconds(model,before.index,before.phase.toDouble())
        val previous=outgoingStream ?: streaming.takeIf {before.playing && !before.paused && gradual()}
        if(previous!=null)streaming=null
        outgoingStream=previous
        val keep=previous!=null || outgoingPcm!=null
        stopOtherAudio();stop(clearTimer=false,keepAudioFocus=keep,keepOverlap=keep)
        streamGain=if(keep)0f else 1f
        val own=++revision
        state.value=before.copy(model=model,playing=true,paused=false,index=0,phase=if(model.optDouble("duration")>0)(seconds/model.optDouble("duration")).toFloat().coerceIn(0f,.999999f) else 0f,message="Reproduzindo…")
        try {
            ContextCompat.startForegroundService(context,Intent(context,JukeboxService::class.java))
            if(!keep && audio.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED){finishStreamOverlap();state.update {it.copy(playing=false,message="A saída de áudio está ocupada.",playbackError="A saída de áudio está ocupada.")};return}
            if(!noisyRegistered){ContextCompat.registerReceiver(context,noisy,IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),ContextCompat.RECEIVER_NOT_EXPORTED);noisyRegistered=true}
            streaming=AndroidStreamPlayback(context,scope,model,seconds,
                prefetchAllowed={nextQueueIndex>=playbackQueue.value.size || queueRepeat.value=="Uma"},
                onClock={position,ready,bufferStart,bufferEnd->if(own==revision){
                    streamBuffer.value=bufferStart to bufferEnd
                    audioReady.value=ready
                    if(ready && (outgoingStream!=null || outgoingPcm!=null) && streamFade==null) {
                        val old=outgoingStream;val pcm=outgoingPcm
                        streamFade=scope.launch {
                            try {
                                val steps=transitionSeconds()*20
                                for(step in 1..steps){while(state.value.paused)delay(50);streamGain=step.toFloat()/steps;applyGain();old?.volume(volume.value*(1f-streamGain));pcm?.volume(volume.value*(1f-streamGain));delay(50)}
                            } finally {old?.close();pcm?.close();if(outgoingStream===old && outgoingPcm===pcm){outgoingStream=null;outgoingPcm=null;streamGain=1f;applyGain();streamFade=null}}
                        }
                    }
                    val duration=model.optDouble("duration",0.0)
                    state.update {it.copy(index=0,phase=if(duration>0)(position/duration).toFloat().coerceIn(0f,.999999f) else 0f,elapsed=position)}
                    normalTransition()
                }},
                onEnded={if(own==revision){
                    if(queueRepeat.value=="Uma"){seekSeconds(0.0);streaming?.resume()}
                    else if(nextQueueIndex<playbackQueue.value.size || queueRepeat.value=="Todas")nextTrack()
                    else stopPreservingPosition()
                }},
                refresh={
                    val row=playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value} ?: JSONObject()
                    val id="playback-stream-refresh-"+UUID.randomUUID()
                    val fresh=call("jukebox_stream_resolve",OndaStore.config().put("record",row).put("stream_source",model.getJSONObject("_stream").optString("source_url")),id)
                    if(own!=revision)throw CancellationException()
                    model.put("_stream",fresh.getJSONObject("_stream"));fresh
                },
                onFailure={error->if(own==revision){finishStreamOverlap();streaming?.close();streaming=null;audioReady.value=false;streamBuffer.value=0.0 to 0.0;releaseNoisy();audio.abandonAudioFocusRequest(focus);state.update {it.copy(playing=false,paused=false,message="Não foi possível reproduzir o áudio online. Tente abrir a música novamente.",playbackError="Não foi possível reproduzir o áudio online. Tente abrir a música novamente.")}}})
            applyGain()
        } catch(error:Exception){finishStreamOverlap();streaming?.close();streaming=null;releaseNoisy();audio.abandonAudioFocusRequest(focus);state.update {it.copy(playing=false,message=uiExceptionMessage(error,"Não foi possível reproduzir."),playbackError=uiExceptionMessage(error,"Não foi possível reproduzir."))}}
    }

    private fun prewarmEffects() {
        effectPreparation?.cancel();if(effectPreparationId.isNotBlank())MobileEngine.cancel(effectPreparationId)
        reconcileSource()
        if(state.value.model?.has("_stream")==true)return
        val preparationRevision=revision
        effectPreparation=scope.launch {
            delay(400)
            if(!effects.value.optBoolean("enabled"))return@launch
            val settings=JSONObject(effects.value.toString())
            val models=listOfNotNull(state.value.model).filter {!it.has("_stream")}
            for(model in models) {
                if(preparationRevision!=revision || settings.toString()!=effects.value.toString())break
                val id="playback-effects-"+UUID.randomUUID();effectPreparationId=id
                try {call("jukebox_effects",JSONObject().put("cache",model.getString("cache")).put("effects",settings),id)}
                catch(e:CancellationException){throw e}
                catch(e:Exception){if(preparationRevision==revision && settings.toString()==effects.value.toString())state.update {it.copy(effectsError=uiExceptionMessage(e,"Não foi possível preparar os efeitos desta música."))}}
            }
            effectPreparationId=""
        }
    }
    var normal:Boolean
        get()=normalPlayback.value
        set(value){if(normalPlayback.value==value)return;normalPlayback.value=value;normalEndGain=1f;applyGain();restartPreparationMode();reconcileSource()}
    private data class SeekRequest(val index:Int,val phase:Float,val epoch:Int)
    private val pendingSeek=java.util.concurrent.atomic.AtomicReference<SeekRequest?>(null)
    fun seek(index:Int) {
        val model=state.value.model ?: return
        val beats=model.optJSONArray("beats") ?: return
        if(index in 0 until beats.length()-1)seekSeconds(beats.optDouble(index))
    }
    fun seekSeconds(seconds:Double) {
        if(!seconds.isFinite())return
        val current=state.value
        val row=playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}
        val duration=current.model?.optDouble("duration",0.0) ?: ((row?.optDouble("duration_ms",0.0) ?: 0.0)/1000)
        val target=seconds.coerceIn(0.0,duration.coerceAtLeast(0.0))
        finishStreamOverlap()
        if(current.model==null){row?.put("_restore_seconds",target);state.update {it.copy(restoredSeconds=target)};checkpointPosition();return}
        val beats=current.model.optJSONArray("beats") ?: return
        val index=(0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=target} ?: 0
        val a=beats.optDouble(index);val b=beats.optDouble(index+1,a)
        val phase=if(b>a)((target-a)/(b-a)).coerceIn(0.0,.999999).toFloat() else 0f
        pendingSeek.set(SeekRequest(index,phase,seekEpoch.incrementAndGet()))
        state.update {it.copy(index=index,phase=phase,flow=emptyList(),used=emptySet(),nextIndex=-1,jumpBlend=0f)}
        streaming?.seek(target)
        checkpointPosition()
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
        return coroutineScope {
            val worker=async(Dispatchers.IO) {
                ensureActive()
                MobileEngine.call(context,id,action,config,EventCallback {}).also {ensureActive();require(!it.has("error")){it.optString("error")}}
            }
            try {worker.await()}
            catch(cancelled:CancellationException){MobileEngine.cancel(id);throw cancelled}
        }
    }
    private suspend fun handoffPreparation(action:String,config:JSONObject):JSONObject = coroutineScope {
        val id="jukebox-handoff-"+UUID.randomUUID()
        val worker=async(Dispatchers.IO) {call(action,config,id)}
        try {worker.await()}
        catch(error:CancellationException) {MobileEngine.cancel(id);throw error}
    }

    internal suspend fun awaitHandoffAudio() {
        withTimeout(10000) {
            kotlinx.coroutines.flow.combine(audioReady,state) {ready,current->ready to current.playing}.first {it.first || !it.second}.let {
                check(it.first && it.second) {state.value.message.ifBlank {"Não foi possível iniciar o áudio neste telefone."}}
            }
        }
    }

    internal suspend fun prepareHandoff(record:JSONObject):JSONObject =
        handoffPreparation("jukebox_prepare",prepareConfig("",record)).also {
            require(it.has("_stream") || java.io.File(it.optString("cache"),"analysis.json").isFile()) {"Não foi possível preparar a música neste telefone."}
        }

    internal suspend fun prepareResolvedHandoff(model:JSONObject):JSONObject {
        if(canStream() && model.has("_stream"))return copyJsonObject(model).put("source",model.getJSONObject("_stream").optString("source_url"))
        return handoffPreparation("jukebox_transfer_prepare",OndaStore.config().put("model",model)).also {
            require(java.io.File(it.optString("cache"),"analysis.json").isFile()) {"Não foi possível preparar o áudio recebido do computador."}
        }
    }

    internal fun startHandoff(record:JSONObject,model:JSONObject,seconds:Double,playing:Boolean,deferRemoteDisconnect:Boolean=false) {
        stop(clearTimer=false)
        val row=copyJsonObject(record).put("_queue_id",UUID.randomUUID().toString())
            .put("_analysis","Pronta").put("_restore_seconds",seconds)
            .put("_prepared_cache",preparedQueueReference(model))
        val id=row.getString("_queue_id")
        preparedModels[id]=model
        playbackQueue.value=playbackQueue.value+row
        currentQueueId.value=id;queueCursor=playbackQueue.value.lastIndex
        val beats=model.optJSONArray("beats")
        val index=if(beats==null)0 else (0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=seconds} ?: 0
        val a=beats?.optDouble(index,0.0) ?: 0.0
        val b=beats?.optDouble(index+1,a) ?: a
        val phase=if(b>a)((seconds-a)/(b-a)).coerceIn(0.0,.999999).toFloat() else 0f
        row.remove("_restore_seconds")
        state.value=JukeboxState(title=model.optString("media_title").ifBlank {record.optString("title")},model=model,index=index,phase=phase)
        if(playing)playPauseInternal(!deferRemoteDisconnect)
    }

    fun prepare(source:String="",record:JSONObject?=null,url:String="",autoPlay:Boolean=false) {
        autoplayQueueId="";priorityQueueId=""
        val insertion=nextQueueIndex.coerceIn(0,playbackQueue.value.size)
        currentQueueId.value="";queueCursor=-1
        stop(clearTimer=false);val own=++revision;val id="jukebox-"+UUID.randomUUID();identity=id
        state.value=JukeboxState(title=record?.optString("title").orEmpty(),message="Analisando ritmo e trechos semelhantes…",busy=true)
        val config=prepareConfig(source,record,url)
        task=scope.launch {
            try {
                val model=call("jukebox_prepare",config,id)
                if(own==revision) {
                    val row=JSONObject(record?.toString() ?: "{}").put("title",model.optString("media_title").ifBlank {model.optString("title")})
                        .put("artists",org.json.JSONArray(listOf(model.optString("media_artist")).filter {it.isNotBlank()}))
                        .put("cover_url",model.optString("cover_url")).put("_cover",model.optString("media_cover"))
                        .put("duration_ms",model.optDouble("duration",0.0)*1000).apply {if(!model.has("_stream"))put("_local_source",model.optString("source")) else if(optString("source_url").isBlank())put("source_url",model.optString("source"))}
                        .put("_queue_id",UUID.randomUUID().toString()).put("_analysis","Pronta")
                        .put("_catalog_source",record!=null && !record.optBoolean("_jukebox_direct"))
                        .put("_prepared_cache",preparedQueueReference(model))
                    preparedModels[row.getString("_queue_id")]=model
                    playbackQueue.value=playbackQueue.value.toMutableList().apply {add(insertion.coerceAtMost(size),row)}
                    currentQueueId.value=row.getString("_queue_id");queueCursor=insertion
                    startQueuePreparation()
                }
                if(own==revision)state.value=JukeboxState(title=model.optString("media_title").ifBlank {model.optString("title")},model=model,message=if(model.optInt("links")>0)"Análise concluída." else "Sem saltos compatíveis: a faixa será repetida normalmente.")
                if(own==revision && autoPlay)playPause()
            } catch(e:CancellationException){throw e} catch(e:Exception){if(own==revision)state.value=state.value.copy(busy=false,message=uiExceptionMessage(e,"Não foi possível analisar a música."))}
        }
    }
    val searching=MutableStateFlow(false)
    private var searchTask:Job?=null
    private var searchIdentity=""
    internal fun sessionSeconds(model:JSONObject?,index:Int,phase:Double):Double {
        if(model==null)return playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}?.optDouble("_restore_seconds",0.0)?.takeIf {it.isFinite()}?.coerceAtLeast(0.0) ?: 0.0
        val beats=model.optJSONArray("beats") ?: return 0.0
        if(beats.length()<2)return 0.0
        val i=index.coerceIn(0,beats.length()-2)
        return (beats.optDouble(i)+(beats.optDouble(i+1)-beats.optDouble(i))*phase.coerceIn(0.0,1.0)).takeIf {it.isFinite()}?.coerceAtLeast(0.0) ?: 0.0
    }
    private var savedQueueSource:List<JSONObject>?=null
    private var savedQueueSnapshot:org.json.JSONArray?=null
    internal fun savePlaybackSession(synchronous:Boolean=false) {
        val current=state.value
        val seconds=if(current.model!=null)sessionSeconds(current.model,current.index,current.phase.toDouble()) else playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}?.optDouble("_restore_seconds",0.0) ?: 0.0
        val queue=playbackQueue.value
        if(savedQueueSource!==queue) {
            savedQueueSource=queue
            savedQueueSnapshot=org.json.JSONArray(queue.map {copyJsonObject(it)})
        }
        PlaybackSessions.save(context,"jukebox",JSONObject().put("queue",savedQueueSnapshot).put("current",currentQueueId.value)
            .put("model",current.model?.let(::preparedQueueReference)).put("seconds",seconds).put("index",current.index).put("phase",current.phase.takeIf {it.isFinite()} ?: 0f).put("normal",normal).put("variation",variation.takeIf {it.isFinite()} ?: 45f).put("smooth",smooth.takeIf {it.isFinite()} ?: 35f).put("repeat",queueRepeat.value).put("shuffle",queueShuffle.value).put("effects",effects.value).put("unified",unifiedMigrated),synchronous)
    }
    private var unifiedMigrated=false
    fun migrateEffectsSession(data:JSONObject?) {
        if(unifiedMigrated)return
        if(data!=null) {
            val files=data.optJSONArray("queue")?.let {a->(0 until a.length()).map {a.optString(it)}}.orEmpty().toMutableList()
            val source=data.optString("source")
            if(source.isNotBlank()&&source !in files)files.add(0,source)
            val infos=data.optJSONObject("info")
            val migrated=files.mapNotNull {path->
                val info=infos?.optJSONObject(path)
                val row=JSONObject(info?.optJSONObject("record")?.toString() ?: "{}")
                if(java.io.File(path).isFile)row.put("_local_source",path)
                else if(path.startsWith("https://")||path.startsWith("http://")){if(row.optString("source_url").isBlank())row.put("source_url",path)}
                else return@mapNotNull null
                row.put("title",row.optString("title").ifBlank {importedAudioName(path)})
                    .put("_queue_id",UUID.randomUUID().toString()).put("_analysis",if(info?.optString("error").isNullOrBlank())"Pendente" else "Erro").put("_error",info?.optString("error").orEmpty())
            }
            playbackQueue.value=playbackQueue.value+migrated
            if(state.value.model==null&&migrated.isNotEmpty()) {
                currentQueueId.value=migrated.firstOrNull {it.optString("_local_source")==source}?.optString("_queue_id") ?: migrated.first().optString("_queue_id")
                queueCursor=playbackQueue.value.indexOfFirst {it.optString("_queue_id")==currentQueueId.value}
                normal=true
                effects.value=JSONObject().put("enabled",true).put("speed",data.optInt("speed",85).coerceIn(50,150)).put("reverb",data.optInt("reverb",25).coerceIn(0,100)).put("keep_pitch",data.optBoolean("pitch"))
                queueRepeat.value=data.optString("repeat").takeIf {it in listOf("Desativada","Todas","Uma")} ?: "Desativada";queueShuffle.value=data.optBoolean("shuffle")
                playbackQueue.value.getOrNull(queueCursor)?.put("_restore_seconds",data.optDouble("position",0.0))
            }
        }
        unifiedMigrated=true;savePlaybackSession(synchronous=true)
    }
    init {
        PlaybackSessions.load(context,"jukebox")?.let {data->
            unifiedMigrated=data.optBoolean("unified")
            data.optJSONObject("effects")?.let {effects.value=copyJsonObject(it)}
            playbackQueue.value=data.optJSONArray("queue")?.objects()?.map {copyJsonObject(it).put("_analysis","Pendente").apply {
                if(cleanString("_local_source").isNotBlank() && !java.io.File(cleanString("_local_source")).isFile && cleanString("source_url").isNotBlank())remove("_local_source")
            }} ?: emptyList()
            currentQueueId.value=data.optString("current");queueCursor=playbackQueue.value.indexOfFirst {it.optString("_queue_id")==currentQueueId.value}
            playbackQueue.value.filter {it.optString("_queue_id")==currentQueueId.value}.forEach {row->restoreQueueModel(row)?.let {model->
                preparedModels[row.getString("_queue_id")]=model;row.put("_analysis","Pronta").put("_error","")
            }}
            queueRepeat.value=data.optString("repeat").takeIf {it in listOf("Desativada","Todas","Uma")} ?: "Desativada";queueShuffle.value=data.optBoolean("shuffle")
            normal=data.optBoolean("normal");variation=data.optDouble("variation",45.0).takeIf {it.isFinite()}?.coerceIn(0.0,100.0)?.toFloat() ?: 45f;smooth=data.optDouble("smooth",35.0).takeIf {it.isFinite()}?.coerceIn(0.0,100.0)?.toFloat() ?: 35f
            val savedReference=data.optJSONObject("model")
            val savedModel=if(savedReference?.has("beats")==true)savedReference else savedReference?.let {
                preparedModels[currentQueueId.value] ?: restoreQueueModel(JSONObject().put("_prepared_cache",it)
                    .put("_cover",playbackQueue.value.firstOrNull {row->row.optString("_queue_id")==currentQueueId.value}?.optString("_cover").orEmpty()))
            }
            val seconds=data.optDouble("seconds",sessionSeconds(savedModel,data.optInt("index"),data.optDouble("phase",0.0))).takeIf {it.isFinite()}?.coerceAtLeast(0.0) ?: 0.0
            playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}?.put("_restore_seconds",seconds)
            val restoredRow=playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}
            if(restoredRow!=null)state.value=JukeboxState(title=restoredRow.cleanString("title"),message="Sessão restaurada. Toque em reproduzir.",restoredSeconds=seconds)
            savedModel?.takeIf {java.io.File(it.optString("cache"),"analysis.json").isFile}?.let {model->
                val beats=model.optJSONArray("beats")
                val position=seconds.coerceAtMost(model.optDouble("duration",seconds).coerceAtLeast(0.0))
                val index=if(beats==null)0 else (0 until (beats.length()-1).coerceAtLeast(0)).lastOrNull {beats.optDouble(it)<=position} ?: 0
                val a=beats?.optDouble(index,0.0) ?: 0.0;val b=beats?.optDouble(index+1,a) ?: a
                val phase=if(b>a)((position-a)/(b-a)).coerceIn(0.0,1.0).toFloat() else 0f
                state.value=JukeboxState(title=model.optString("media_title").ifBlank {model.optString("title")},model=model,index=index,phase=phase,message="Sessão restaurada. Toque em reproduzir.")
                if(currentQueueId.value.isNotBlank()) {
                    playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}?.remove("_restore_seconds")
                    preparedModels[currentQueueId.value]=model
                    updateQueue(currentQueueId.value,"Pronta")
                    playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}?.put("_prepared_cache",preparedQueueReference(model))
                }
            }
        }
        scope.launch {while(isActive){delay(5000);savePlaybackSession()}}
        scope.launch {OndaStore.settings.map {preparationAhead(it)}.distinctUntilChanged().drop(1).collect {startQueuePreparation();prewarmEffects()}}
        scope.launch {OndaStore.settings.map {it.optJSONObject("jukebox_equalizer")?.toString().orEmpty()}.distinctUntilChanged().drop(1).collect {restartPreparationMode();reconcileSource()}}
    }
    fun cancelSearch() {
        val id=searchIdentity;searchIdentity=""
        searchTask?.cancel();searchTask=null;searching.value=false
        if(id.isNotBlank())MobileEngine.cancel(id)
    }
    fun search(query:String) {
        if(query.isBlank()){state.update {it.copy(message=EMPTY_MUSIC_SEARCH)};return}
        cancelSearch()
        val id="jukebox-search-"+UUID.randomUUID();searchIdentity=id
        searching.value=true
        state.update {it.copy(records=emptyList(),message="Pesquisando…")}
        searchTask=scope.launch {
            try {
                val result=resolveQueueInput(query,id);val records=result.optJSONArray("tracks")?.objects().orEmpty()
                if(searchIdentity==id) {
                    if(result.optBoolean("is_collection")){val count=enqueueAll(records);state.update {it.copy(records=emptyList(),message="$count músicas adicionadas à fila. "+result.optString("coverage_summary")+if(count<records.size)" Limite de 5.000 músicas na fila de reprodução. Remova músicas antes de adicionar outras." else "")}}
                    else state.update {it.copy(records=records,message=if(records.isEmpty())"Nenhuma música encontrada." else "Escolha uma música nos resultados.")}
                }
            } catch(e:CancellationException){throw e}
            catch(e:Exception){if(searchIdentity==id)state.update {it.copy(message=uiExceptionMessage(e,"Falha de pesquisa."))}}
            finally {if(searchIdentity==id){searchIdentity="";searching.value=false}}
        }
    }
    fun pauseForRestart(){autoplayQueueId="";pause()}
    fun pause() {if(state.value.playing){state.update {it.copy(paused=true)};streaming?.pause();outgoingStream?.pause();runCatching {outgoingPcm?.output?.pause();track?.pause()};checkpointPosition()}}
    fun playPause() = playPauseInternal(true)
    private fun playPauseInternal(disconnectRemote:Boolean) {
        state.update {it.copy(playbackError="")}
        if(disconnectRemote && RemotePlaybackRuntime.state.value.connected)RemotePlaybackRuntime.disconnect()
        if(state.value.playing) {
            if(state.value.paused){if(audio.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED)return;stopOtherAudio();streaming?.resume();outgoingStream?.resume();runCatching {outgoingPcm?.output?.play()};if(pendingSeek.get()==null)runCatching {track?.play()};state.update {it.copy(paused=false)}} else pause()
            return
        }
        val model=state.value.model ?: run {if(playbackQueue.value.isNotEmpty())playQueued((nextQueueIndex-1).coerceAtLeast(0));return}
        if(model.optDouble("duration")>0 && sessionSeconds(model,state.value.index,state.value.phase.toDouble())>=model.optDouble("duration"))seekSeconds(0.0)
        if(model.has("_stream")){startStreaming(model);return}
        if(!java.io.File(model.optString("cache"),"analysis.json").isFile){
            val seconds=sessionSeconds(model,state.value.index,state.value.phase.toDouble())
            playbackQueue.value.firstOrNull {it.optString("_queue_id")==currentQueueId.value}?.put("_restore_seconds",seconds)
            state.value=state.value.copy(model=null)
            playQueued((nextQueueIndex-1).coerceAtLeast(0));return
        }
        val initial=state.value.index;val initialPhase=state.value.phase
        val keep=outgoingStream!=null || outgoingPcm!=null
        stopOtherAudio();stop(clearTimer=false,keepAudioFocus=keep,keepOverlap=keep);pendingSeek.set(SeekRequest(initial,initialPhase,seekEpoch.get()));val own=++revision;val id="jukebox-play-"+UUID.randomUUID();identity=id
        state.value=state.value.copy(model=model,playing=true,paused=false,message="Reproduzindo…",elapsed=0.0,jumps=0,index=initial,phase=initialPhase,flow=emptyList(),used=emptySet(),nextIndex=-1,jumpBlend=0f)
        try {ContextCompat.startForegroundService(context,Intent(context,JukeboxService::class.java))}
        catch(e:Exception){state.update {it.copy(playing=false,message=uiExceptionMessage(e,"Não foi possível reproduzir."))};return}
        if(audio.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED){state.value=state.value.copy(playing=false,message="A saída de áudio está ocupada.",playbackError="A saída de áudio está ocupada.");return}
        if(!noisyRegistered){ContextCompat.registerReceiver(context,noisy,IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),ContextCompat.RECEIVER_NOT_EXPORTED);noisyRegistered=true}
        fadeTask?.cancel()
        startGain=if(gradual())0f else 1f
        if(gradual())fadeTask=scope.launch {
            val old=outgoingStream;val pcm=outgoingPcm
            try {
                while(!audioReady.value && state.value.playing)delay(20)
                val steps=transitionSeconds()*20
                repeat(steps){while(state.value.paused)delay(50);startGain=(it+1)/steps.toFloat();applyGain();old?.volume(volume.value*(1f-startGain));pcm?.volume(volume.value*(1f-startGain));delay(50)}
            } finally {old?.close();pcm?.close();if(outgoingStream===old && outgoingPcm===pcm){outgoingStream=null;outgoingPcm=null}}
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
                    track=output;output.setVolume(volume.value*minOf(stopGain,switchGain,startGain));output.play()
                }
                val timeline=java.util.ArrayDeque<Pair<Long,JSONObject>>();var submitted=0L;var lastProgress=0L;var trackBase=0L
                var activeSeek=seekEpoch.get()
                fun progress() {
                    val now=android.os.SystemClock.elapsedRealtime()
                    if(now-lastProgress<40 || own!=revision || activeSeek!=seekEpoch.get())return
                    lastProgress=now
                    val played=output.playbackHeadPosition.toLong() and 0xffffffffL
                    fun announce(end:Long,packet:JSONObject) {
                        val cache=packet.optString("track_changed")
                        if(cache.isBlank())return
                        packet.remove("track_changed")
                        trackBase=end-(packet.optDouble("seconds")*44100).roundToLong()
                        switchModels.remove(cache)?.let {request->scope.launch(Dispatchers.Main.immediate) {
                            val queued=playbackQueue.value.indexOfFirst {it.optString("_queue_id")==request.row.optString("_queue_id")}
                            if(queued>=0){currentQueueId.value=request.row.optString("_queue_id");queueCursor=queued;startQueuePreparation()}
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
                    state.update {current->if(own==revision && activeSeek==seekEpoch.get())current.copy(
                        index=part?.second?.optInt("index") ?: heard.lastOrNull()?.let {it.optInt(if(it.optBoolean("edge_completed",true))"next" else "index")} ?: current.index,phase=phase,
                        nextIndex=outgoing?.optInt("next",-1) ?: -1,jumpBlend=blend,
                        used=if(heard.isEmpty())current.used else current.used+heard.filter {it.optBoolean("edge_completed",true)}.map {it.optInt("index") to it.optInt("next")},
                        flow=if(heard.isEmpty())current.flow else (current.flow+heard.filter {it.optBoolean("edge_completed",true)}.map {it.optInt("index") to it.optInt("next")}).takeLast(24),
                        jumps=heard.lastOrNull()?.optInt("jumps") ?: current.jumps,elapsed=(played-trackBase).coerceAtLeast(0)/44100.0) else current}
                    scope.launch(Dispatchers.Main.immediate) {if(own==revision)normalTransition()}
                }
                var transitioning=false
                while(isActive && (own==revision || outgoingPcm?.output===output)) {
                    if(state.value.paused)state.first {!it.paused}
                    ensureActive()
                    (if(own==revision && !transitioning)switchRequest.getAndSet(null) else null)?.let {request->
                        switchModels[request.model.getString("cache")]=request
                        try {call("jukebox_switch",JSONObject().put("session",id).put("cache",request.model.getString("cache")).put("seconds",request.seconds),id)}
                        catch(e:CancellationException){throw e}
                        catch(e:Exception){switchModels.remove(request.model.optString("cache"));state.update {it.copy(message=uiExceptionMessage(e,"Não foi possível trocar a música."))}}
                    }
                    val config=JSONObject().put("equalizer",OndaStore.settings.value.optJSONObject("jukebox_equalizer")).put("session",id).put("variation",variation).put("smooth",smooth).put("volume",100).put("normal",normal).put("effects",effects.value)
                    val seek=if(own==revision)pendingSeek.getAndSet(null) else null
                    if(seek!=null){activeSeek=seek.epoch;output.pause();output.flush();submitted=0L;trackBase=0L;timeline.clear();output.play();config.put("seek",seek.index).put("seek_phase",seek.phase)}
                    val packet=if(callOverride!=null) {
                        val metadata=call("jukebox_chunk",config,id)
                        val pcm=Base64.decode(metadata.getString("pcm"),Base64.NO_WRAP)
                        metadata.remove("pcm");metadata to pcm
                    } else withContext(Dispatchers.IO){MobileEngine.pcmChunk(context,id,config)}
                    if(activeSeek!=seekEpoch.get())continue
                    val part=packet.first
                    if(own==revision)state.update {it.copy(effectsPending=part.optBoolean("effects_pending"),effectsError=part.optString("effects_error"))}
                    transitioning=part.optBoolean("crossfade_active",false)
                    val data=packet.second;var offset=0
                    submitted+=data.size/4;timeline.addLast(submitted to part)
                    while(offset<data.size && isActive && (own==revision || outgoingPcm?.output===output)) {
                        if(state.value.paused)state.first {!it.paused}
                        ensureActive()
                        if(activeSeek!=seekEpoch.get())break
                        val count=output.write(data,offset,min(4096,data.size-offset),AudioTrack.WRITE_NON_BLOCKING)
                        require(count>=0){"A saída de áudio foi interrompida."}
                        if(count==0)delay(5) else {offset+=count;if(own==revision)audioReady.value=true}
                        progress()
                    }
                    if(activeSeek!=seekEpoch.get())continue
                    progress()
                    if(part.optBoolean("finished")&&part.optBoolean("edge_completed",true)) {
                        while(isActive&&own==revision&&activeSeek==seekEpoch.get()&&(output.playbackHeadPosition.toLong() and 0xffffffffL)<submitted){if(state.value.paused)state.first {!it.paused};delay(10);progress()}
                        if(activeSeek!=seekEpoch.get())continue
                        withContext(Dispatchers.Main) {
                            if(own==revision && activeSeek==seekEpoch.get()) {
                                stop(clearTimer=false)
                                if(queueRepeat.value=="Uma")playPause()
                                else if(nextQueueIndex<playbackQueue.value.size || queueRepeat.value=="Todas"&&playbackQueue.value.isNotEmpty())nextTrack()
                                else state.update {it.copy(index=(it.model?.optJSONArray("beats")?.length()?.minus(2) ?: 0).coerceAtLeast(0),phase=1f,message="Fim da fila de reprodução.")}
                            }
                        }
                        break
                    }
                }
            } catch(e:CancellationException){throw e} catch(e:Exception){if(own==revision)state.value=state.value.copy(message=uiExceptionMessage(e,"Não foi possível reproduzir."),playbackError=uiExceptionMessage(e,"Não foi possível reproduzir."))}
            finally {
                runCatching {output?.pause();output?.flush();output?.release()}
                appliedGain.clear(output)
                withContext(NonCancellable+Dispatchers.IO) {runCatching {call("jukebox_close",JSONObject().put("session",id),id+"-close")}}
                if(own==revision){track=null;audioReady.value=false;state.update {it.copy(playing=false,paused=false)};releaseNoisy();audio.abandonAudioFocusRequest(focus)}
            }
        }
    }
    fun stop(clearTimer:Boolean=true,keepAudioFocus:Boolean=false,keepOverlap:Boolean=false) {
        sourceChange?.cancel();sourceChange=null
        if(sourceChangeId.isNotBlank())MobileEngine.cancel(sourceChangeId)
        sourceChangeId=""
        if(!keepOverlap)finishStreamOverlap()
        streaming?.close();streaming=null;audioReady.value=false;streamBuffer.value=0.0 to 0.0
        audioReady.value=false
        switchRequest.set(null);switchModels.clear()
        cancelSearch()
        if(clearTimer){autoplayQueueId="";priorityQueueId="";timerTask?.cancel();switchTask?.cancel();timerTask=null;switchTask=null;timerMinutes.value=0;timerRemaining.value=0;switchMinutes.value=0;switchRemaining.value=0}
        fadeTask?.cancel();stopGain=1f;switchGain=1f;startGain=1f;normalEndGain=1f;applyGain()
        synchronized(this) {revision++;runCatching {track?.pause();track?.flush()};track=null}
        if(identity.isNotBlank())MobileEngine.cancel(identity)
        task?.cancel();task=null;runCatching {track?.pause();track?.flush()};track=null
        appliedGain.clear()
        if(!keepAudioFocus){releaseNoisy();audio.abandonAudioFocusRequest(focus)}
        state.value=state.value.copy(busy=false,playing=false,paused=false,effectsPending=false,index=0,phase=0f,flow=emptyList(),used=emptySet(),nextIndex=-1,jumpBlend=0f,message=if(state.value.playing||state.value.busy)"Reprodução encerrada." else state.value.message)
    }
    fun stopPreservingPosition() {
        val snapshot=state.value
        stop()
        state.value=state.value.copy(index=snapshot.index,phase=snapshot.phase)
        runCatching {savePlaybackSession()}.onFailure {android.util.Log.w("ONDA","Could not save stopped playback session",it)}
    }
    fun close(){checkpoint?.cancel();stopPreservingPosition();queueIndex.clear();effectPreparation?.cancel();if(effectPreparationId.isNotBlank())MobileEngine.cancel(effectPreparationId);cancelQueuePreparation();preparedModels.clear()}
}

@Composable internal fun PlaybackPage(vm:OndaViewModel) {
    val spacing=LocalLayoutSpacing.current
    LaunchedEffect(Unit){vm.playbackMode.value=1}
    CompositionLocalProvider(LocalLayoutSpacing provides spacing.copy(controls=spacing.controls+2.dp,section=spacing.section+4.dp)) {
        Column(Modifier.fillMaxSize()) {
            Row(Modifier.fillMaxWidth().padding(horizontal=LayoutSpacing.inset,vertical=12.dp),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
                UiText("Reprodução",modifier=Modifier.weight(1f),style=MaterialTheme.typography.headlineMedium,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                IconButton(onClick=vm::openPlaybackQueue,modifier=Modifier.testTag("unified-open-queue")){OndaIcon("queue","Fila",Modifier.size(24.dp))}
            }
            JukeboxPage(vm)
        }
    }
}

@Composable private fun JukeboxPage(vm:OndaViewModel) {
    val controller=vm.jukebox
    val state by controller.presentationState.collectAsStateWithLifecycle()
    val searching by controller.searching.collectAsStateWithLifecycle()
    val pendingPlaybackId by controller.pendingPlaybackId.collectAsStateWithLifecycle()
    val streamReady by controller.audioReady.collectAsStateWithLifecycle()
    val queuedTracks by controller.playbackQueue.collectAsStateWithLifecycle()
    val currentQueueId by controller.currentQueueId.collectAsStateWithLifecycle()
    val normal by controller.normalPlayback.collectAsStateWithLifecycle()
    var query by rememberSaveable {mutableStateOf("")}
    var variation by rememberSaveable {mutableFloatStateOf(controller.variation)}
    var smooth by rememberSaveable {mutableFloatStateOf(controller.smooth)}
    LaunchedEffect(variation,smooth){controller.variation=variation;controller.smooth=smooth}
    val chooser=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"audio") {file->controller.prepare(file.absolutePath)}}
    fun search(){if(!searching && !state.busy && vm.validateMusicQuery(query))controller.search(query)}
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=LayoutSpacing.inset).padding(top=4.dp,bottom=16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Column(Modifier.fillMaxWidth().testTag("jukebox-source-card"),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(query,{query=it},placeholder={UiText("Música, artista ou link",maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)},singleLine=true,
                    keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={search()}),shape=RoundedCornerShape(12.dp),
                    leadingIcon={IconButton(onClick={if(searching)controller.cancelSearch() else if(state.busy)controller.stop() else search()},enabled=true,modifier=Modifier.testTag("playback-search-submit")) {
                        OndaIcon(if(searching||state.busy)"close" else "search",if(searching||state.busy)"Cancelar" else "Pesquisar",Modifier.size(22.dp))
                    }},modifier=Modifier.weight(1f).testTag("playback-search-input").a11yLabel(PLAYBACK_INPUT_HINT))
                OutlinedIconButton(onClick={chooser.launch(arrayOf("audio/*"))},enabled=!state.busy,shape=RoundedCornerShape(12.dp),modifier=Modifier.size(56.dp).testTag("playback-open-file")) {OndaIcon("folder","Abrir arquivo",Modifier.size(24.dp))}
            }
            if(pendingPlaybackId.isNotBlank() || state.busy || searching || (state.playing && !state.paused && !streamReady))LinearProgressIndicator(Modifier.fillMaxWidth().testTag("playback-source-progress"))
            if(state.playbackError.isNotBlank())UiErrorText(state.playbackError,modifier=Modifier.testTag("playback-request-error"),color=MaterialTheme.colorScheme.error)
            if(state.records.isNotEmpty())PlaybackCard {
                Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
                    UiText("Resultados",Modifier.weight(1f),style=MaterialTheme.typography.titleSmall)
                    IconButton(onClick={controller.cancelSearch();controller.state.update {it.copy(records=emptyList())}}){OndaIcon("close","Fechar pesquisa",Modifier.size(22.dp))}
                }
                state.records.forEach {record->PlaybackSearchResult(record,vm,!state.busy&&!searching,{controller.playRecord(record)},{controller.enqueue(record)})}
            }
        }
        val model=state.model
        val current=queuedTracks.firstOrNull {it.optString("_queue_id")==currentQueueId}
        if(model!=null || current!=null) {
            val record=JSONObject(current?.toString() ?: "{}")
            if(model!=null) {
                record.put("title",state.title)
                model.optString("media_artist").takeIf {it.isNotBlank()}?.let {record.put("artists",org.json.JSONArray(listOf(it)))}
                model.optString("album").takeIf {it.isNotBlank()}?.let {record.put("album",it)}
                model.optString("cover_url").takeIf {it.isNotBlank()}?.let {record.put("cover_url",it)}
                model.optString("release_date").takeIf {it.isNotBlank()}?.let {record.put("release_date",it)}
            }
            val info=JSONObject().put("record",record).put("cover",model?.optString("media_cover").orEmpty())
            PlaybackCard(Modifier.testTag("effects-track-information")) {
                BoxWithConstraints {
                    val coverSize=if(maxWidth<300.dp)72.dp else 88.dp
                    Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(14.dp)) {
                        EffectsArtwork(info,Modifier.size(coverSize))
                        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                            Text(record.optString("title"),style=MaterialTheme.typography.titleMedium,fontWeight=androidx.compose.ui.text.font.FontWeight.SemiBold,maxLines=2,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                            Text(record.stringList("artists"),style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                            AlbumDateLabel(record)
                            if(model==null)TextButton(onClick={controller.playQueued(queuedTracks.indexOf(current))}){UiText("Reproduzir")}
                        }
                    }
                }
            }
        }
        UnifiedEffectsControls(controller,vm)
        PlaybackCard(Modifier.testTag("unified-jukebox-card")) {
            PlaybackSectionToggle("Jukebox infinito",!normal){controller.normal=!it}
            if(state.model==null || state.busy)UiText(state.message,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                    PlaybackAdjustment(translateUi("Variação")+" · ${variation.toInt()}%",variation,0f..100f,"jukebox-variation",!normal){variation=it;controller.variation=it}
                    PlaybackAdjustment(translateUi("Transição suave")+" · ${smooth.toInt()}%",smooth,0f..100f,"jukebox-transition",!normal){smooth=it;controller.smooth=it}
                }
                Box(Modifier.size(104.dp).testTag("playback-jukebox-graph")) {
                    LiveJukeboxGraph(controller,variation,smooth,normal)
                    if(state.model==null)OndaIcon("music",modifier=Modifier.size(26.dp).align(androidx.compose.ui.Alignment.Center),tint=MaterialTheme.colorScheme.primary)
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
        if(nextSong && queue.isEmpty())UiText("Adicione músicas à fila de reprodução para ativar a troca automática.",color=MaterialTheme.colorScheme.error,style=MaterialTheme.typography.bodySmall)
        if(switchMinutes>0)UiText(translateUi("Próxima música em")+": "+mediaClock(switchRemaining.toLong()))
        if(stopMinutes>0)UiText(translateUi("Parar em")+": "+mediaClock(stopRemaining.toLong()))
    }},confirmButton={TextButton(enabled=value!=null && value in 1..180 && (!nextSong || queue.isNotEmpty()),onClick={controller.setTimer(value!!,nextSong);close()}){UiText("Ativar")}},dismissButton={TextButton(onClick={controller.setTimer(0,nextSong);close()}){UiText("Desligar este timer")}})
}

@Composable private fun LiveJukeboxGraph(controller:JukeboxController,variation:Float,smooth:Float,normal:Boolean) {
    val state by controller.state.collectAsStateWithLifecycle()
    JukeboxGraph(state.model,state.index,state.phase,state.playing,state.flow,state.used,variation,smooth,normal,controller::seek,height=104.dp,nextIndex=state.nextIndex,jumpBlend=state.jumpBlend)
}

@Composable private fun JukeboxGraph(model:JSONObject?,current:Int,phase:Float,playing:Boolean,flow:List<Pair<Int,Int>>,used:Set<Pair<Int,Int>>,variation:Float,smooth:Float,normal:Boolean,onSeek:(Int)->Unit,height:Dp=230.dp,nextIndex:Int=-1,jumpBlend:Float=0f) {
    val colors=MaterialTheme.colorScheme;val rows=model?.optJSONArray("neighbors");val n=max(1,rows?.length() ?: 64)
    val graphColors=jukeboxGraphColors(colors)
    val visible=remember(model,normal,variation){jukeboxVisibleLinks(model,normal,variation)}
    val highlighted=remember(used){used.toList().let {edges->edges.filterIndexed {index,_->index % max(1,ceil(edges.size/600.0).toInt())==0}}}
    Box(Modifier.fillMaxWidth().height(height),contentAlignment=androidx.compose.ui.Alignment.Center) {
        JukeboxConnections(n,visible,if(normal)emptyList() else highlighted,colors.primary,graphColors.first)
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
            for((k,edge) in flow.withIndex()) {
                val (i,j)=edge
                if(j!=(i+1)%n && normal)continue
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
            drawCircle(colors.primary,3.dp.toPx(),point(current.coerceIn(0,n-1).toDouble()))
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

@Composable private fun JukeboxConnections(n:Int,links:List<Pair<Int,Int>>,used:List<Pair<Int,Int>>,ink:Color,ring:Color) {
    val drawing=remember(n,links,used,ink,ring) {Modifier.fillMaxSize().graphicsLayer().drawWithCache {
        val center=Offset(size.width/2,size.height/2)
        val radius=min(size.width,size.height)*.42f
        fun point(index:Int):Offset {val angle=index.toDouble()/n*2*PI-PI/2;return center+Offset((cos(angle)*radius).toFloat(),(sin(angle)*radius).toFloat())}
        fun curves(edges:List<Pair<Int,Int>>)=Path().apply {
            for((i,j) in edges) {val a=point(i);val b=point(j);moveTo(a.x,a.y);quadraticTo(center.x,center.y,b.x,b.y)}
        }
        val background=curves(links);val travelled=curves(used.filter {it.second!=(it.first+1)%n})
        val dots=(0 until n step max(1,ceil(n/150.0).toInt())).map(::point)
        onDrawBehind {
            drawPath(background,ink.copy(alpha=.28f),style=androidx.compose.ui.graphics.drawscope.Stroke(1.dp.toPx()))
            drawPath(travelled,ink.copy(alpha=.7f),style=androidx.compose.ui.graphics.drawscope.Stroke(1.8.dp.toPx()))
            dots.forEach {drawCircle(ring,3.dp.toPx(),it)}
        }
    }}
    Box(drawing)
}

internal fun jukeboxVisibleLinks(model:JSONObject?,normal:Boolean,variation:Float=100f):List<Pair<Int,Int>> {
    if(normal)return emptyList()
    val rows=model?.optJSONArray("neighbors") ?: return emptyList()
    val counts=IntArray(rows.length()) {i->val count=rows.optJSONArray(i)?.length() ?: 0;ceil(count*(.2+.8*variation.coerceIn(0f,100f)/100)).toInt().coerceIn(0,count)}
    val stride=max(1,ceil(counts.sum()/1800.0).toInt())
    return buildList {
        var offset=0
        for(i in counts.indices) {
            val row=rows.optJSONArray(i) ?: continue
            for(j in (stride-offset%stride)%stride until counts[i] step stride)add(i to row.getInt(j))
            offset+=counts[i]
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
