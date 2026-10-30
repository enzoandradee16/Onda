package br.com.onda.mobile

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.sync.withPermit
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

fun JSONArray.objects(): List<JSONObject> = (0 until length()).mapNotNull { optJSONObject(it) }
fun JSONObject.cleanString(key: String): String = if(isNull(key)) "" else optString(key)
fun JSONObject.stringList(key: String): String = optJSONArray(key)?.let { a -> (0 until a.length()).joinToString(", ") { a.optString(it) } } ?: ""

data class DialogNotice(val title:String,val message:String,val error:Boolean=false)

private fun operationNoticeTitle(action:String)=when(action) {
    "settings_export"->"Exportar configurações"
    "settings_import"->"Importar configurações"
    "spotify_connect"->"Conectar Spotify"
    "spotify_disconnect"->"Desconectar Spotify"
    "app_update"->"Verificar atualização do ONDA"
    "update"->"Atualizar ferramentas"
    "self_test"->"Verificar ferramentas"
    "audio_batch_edit"->"Editar metadados em lote"
    "audio_read","audio_edit"->"Editar metadados"
    "normalize_preview"->"Ouvir normalizado"
    "image_preview"->"Ver prévia"
    "image_convert"->"Baixar agora"
    "search"->"Pesquisar músicas"
    "collection"->"Carregar álbum ou playlist"
    "import"->"Importar arquivo"
    "matches"->"Conferir correspondências"
    "export_list"->"Exportar lista"
    "cache_info","cache_clear"->"Cache"
    "video_probe","video_convert","convert_batch"->"Conversor"
    "probe"->"Escolher arquivo de áudio"
    else->"ONDA"
}

private fun importNoticeTitle(category:String)=when(category) {
    "preferences"->"Importar configurações"
    "cover"->"Escolher outra capa"
    "cookies"->"Importar cookies.txt"
    "lyrics"->"Importar letra"
    "flac-browser"->"Escolher arquivo FLAC"
    "audio-editor"->"Editar metadados"
    "audio"->"Usar em efeitos"
    "video-converter"->"Escolher vídeo"
    "image"->"Escolher imagem"
    "playlist"->"Importar álbum ou playlist"
    else->"Importar arquivo"
}

class OndaViewModel(application: Application) : AndroidViewModel(application) {
    private val cardSlots=kotlinx.coroutines.sync.Semaphore(3)
    private val cardDetails=linkedMapOf<String,JSONObject>()
    suspend fun completeCard(record:JSONObject):JSONObject {
        val url=record.cleanString("source_url")
        if(url.isBlank() || record.optBoolean("_details_checked"))return record
        cardDetails[url]?.let {cached->return JSONObject(record.toString()).apply {cached.keys().forEach {put(it,cached.get(it))}}}
        return cardSlots.withPermit {
            val id="card-details-"+UUID.randomUUID()
            try {
                val result=withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"record_details",OndaStore.config().put("record",record),EventCallback {})}
                val value=if(result.has("error"))record else result
                cardDetails[url]=JSONObject().apply {for(field in listOf("cover_url","release_date","album","album_artists","duration_ms","preview_url","_details_checked"))if(value.has(field))put(field,value.get(field))};while(cardDetails.size>256)cardDetails.remove(cardDetails.keys.first())
                value
            } catch(e:CancellationException){throw e} catch(e:Exception){record}
            finally {MobileEngine.cancel(id)}
        }
    }
    private val titleSlots=kotlinx.coroutines.sync.Semaphore(2)
    val effectsSource=MutableStateFlow("")
    val effectsQueueOpen=MutableStateFlow(false)
    val playbackMode=MutableStateFlow<Int?>(null)
    val compactPlaybackMode=MutableStateFlow<Int?>(null)
    val searchResults=MutableStateFlow<List<JSONObject>>(emptyList())
    val collection=MutableStateFlow(JSONObject())
    val collectionComparison=MutableStateFlow<JSONObject?>(null)
    private var collectionSyncJob:Job?=null
    val spotifyConnected=MutableStateFlow(false)

    val busy=MutableStateFlow(false)
    val status=MutableStateFlow("")
    val addingToQueue=MutableStateFlow(false)
    val queueNavigation=MutableStateFlow(false)
    val effectsNavigation=MutableStateFlow(false)
    val playbackQueueOpen=MutableStateFlow(false)
    fun openPlaybackQueue(){playbackQueueOpen.value=true}
    val dialogNotice=MutableStateFlow<DialogNotice?>(null)
    fun showNotice(title:String,message:String,error:Boolean=false) {dialogNotice.value=DialogNotice(title,message,error)}
    fun dismissNotice() {dialogNotice.value=null}
    val queryId=MutableStateFlow("")
    private var previewFromDialog=false
    var player=ExoPlayer.Builder(application).build()
        private set
    val previewUrl=MutableStateFlow("")
    val previewActive=MutableStateFlow(false)
    internal val jukebox=JukeboxRuntime.get(application).also {it.stopOtherAudio={pauseEffectsPlayback();if(!effectFullTrack)stopPreview(false)}}
    private val previewListener=object: androidx.media3.common.Player.Listener {
        override fun onEvents(player: androidx.media3.common.Player, events: androidx.media3.common.Player.Events) {
            previewActive.value=player.playWhenReady && player.playbackState in listOf(androidx.media3.common.Player.STATE_BUFFERING,androidx.media3.common.Player.STATE_READY)
        }
        override fun onPlayerError(error:androidx.media3.common.PlaybackException) {clearEffectTail();previewActive.value=false;effectsPreviewEnabled.value=false;effectsPreparing.value=false;val text="Não foi possível reproduzir esta prévia. Tente novamente ou escolha outra faixa.";if(previewFromDialog) showNotice("Ouvir prévia",text) else status.value=text}
    }
    init {player.addListener(previewListener)}
    init {viewModelScope.launch {
        runCatching {withContext(Dispatchers.IO) {MobileEngine.call(getApplication(),"startup-account","spotify_status",JSONObject(),EventCallback {})}}
            .onSuccess {spotifyConnected.value=it.optBoolean("connected")}
            .onFailure {status.value="Não foi possível preparar as ferramentas. Tente novamente nas Configurações."}
    }}
    private var previewLimit: Job?=null
    val onlineImageGallery=MutableStateFlow<JSONObject?>(null)
    val onlineImageLoading=MutableStateFlow("")
    val onlineImageEmbedded=MutableStateFlow(false)
    val onlineImageError=MutableStateFlow("")
    val onlineImageIndex=MutableStateFlow(0)
    val onlineImageThumbnail=MutableStateFlow<JSONObject?>(null)
    private val onlineThumbnailRequest=PreviewRequest(viewModelScope) {MobileEngine.cancel(it)}
    fun closeOnlineImages(){onlineThumbnailRequest.cancel();onlineImageGallery.value=null;onlineImageThumbnail.value=null;onlineImageEmbedded.value=false;onlineImageError.value=""}
    fun previewOnlineImageAt(index:Int) {
        val gallery=onlineImageGallery.value ?: return
        if(index !in 0 until (gallery.optJSONArray("images")?.length() ?: 0))return
        onlineImageIndex.value=index;onlineImageThumbnail.value=null
        onlineThumbnailRequest.start(
            resolve={id->withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"image_gallery_thumbnail",JSONObject().put("token",gallery.getString("token")).put("index",index),EventCallback {})}},
            onResult={onlineImageThumbnail.value=it},
            onError={onlineImageThumbnail.value=JSONObject().put("error",uiExceptionMessage(it,"Não foi possível abrir este arquivo."))}
        )
    }
    private val onlineImageRequest=PreviewRequest(viewModelScope) {MobileEngine.cancel(it)}
    fun cancelOnlineImagePreview(){onlineImageRequest.cancel();onlineImageLoading.value=""}
    fun previewOnlineImages(url:String,embedded:Boolean=false) {
        closeOnlineImages();onlineImageEmbedded.value=embedded;onlineImageLoading.value=url
        onlineImageRequest.start(
            resolve={id->withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"image_gallery_manifest",OndaStore.config().put("url",url),EventCallback {})}},
            onResult={result->onlineImageLoading.value="";if(result.has("error")){if(embedded)onlineImageError.value=translateError(result.optString("error")) else showNotice("Prévia de imagens",result.optString("error"))} else {onlineImageGallery.value=result;previewOnlineImageAt(0)}},
            onError={error->onlineImageLoading.value="";val message=uiExceptionMessage(error,"Não foi possível abrir este arquivo.");if(embedded)onlineImageError.value=message else showNotice("Prévia de imagens",message)}
        )
    }
    fun downloadOnlineImages(keepPreview:Boolean=false) {
        val url=onlineImageGallery.value?.optString("source_url").orEmpty()
        if(url.isBlank())return
        val id=OndaStore.enqueue(url,options=JSONObject(OndaStore.settings.value.toString()).put("mode","photos"),extra=JSONObject().put("_immediate",true))
        if(!keepPreview)closeOnlineImages()
        if(id.isNotBlank())DownloadService.start(getApplication(),id)
    }
    private val previewRequest=PreviewRequest(viewModelScope) {MobileEngine.cancel(it)}
    val effectsPreviewEnabled=MutableStateFlow(false)
    val effectsPreparing=MutableStateFlow(false)
    val effectsPosition=MutableStateFlow(0.0)
    val effectsEnded=MutableStateFlow(false)
    val effectsVolume=MutableStateFlow(1f)
    val effectsRepeat=MutableStateFlow("Desativada")
    val effectsShuffle=MutableStateFlow(false)
    val loadingPlaybackCollection=MutableStateFlow(false)
    private var playbackCollectionJob:Job?=null
    private var playbackCollectionId=""
    fun cancelPlaybackCollection(){playbackCollectionJob?.cancel();if(playbackCollectionId.isNotBlank())MobileEngine.cancel(playbackCollectionId)}
    val effectsPlaylist=MutableStateFlow<List<String>>(emptyList())
    val effectsInfo=MutableStateFlow<Map<String,JSONObject>>(emptyMap())
    private var effectsCursor=-1
    fun effectsQueueIndex(source:String):Int=effectsPlaylist.value.indexOf(source).takeIf {it>=0} ?: effectsCursor
    private val effectsInfoRequests=mutableSetOf<String>()
    private val effectsCatalogRecords=mutableMapOf<String,JSONObject>()
    fun appendEffectsRecord(source:String,record:JSONObject){
        jukebox.enqueue(JSONObject(record.toString()).apply {if(java.io.File(source).isFile)put("_local_source",source)})
    }
    private val effectsInfoSlots=kotlinx.coroutines.sync.Semaphore(2)
    val appUpdate=MutableStateFlow<JSONObject?>(null)
    private var restartRequested=false
    internal fun restartReturned() {
        if(restartRequested){restartRequested=false;busy.value=false;status.value="Não foi possível reiniciar o ONDA."}
    }
    fun restartAfterToolCheck() {
        if(restartRequested || busy.value || DownloadRuntime.running.get() || MobileEngine.toolsState.value.running || effectsPreparing.value || loadingPlaybackCollection.value || jukebox.state.value.busy)return
        restartRequested=true;busy.value=true
        viewModelScope.launch {
            try {
                val result=withContext(Dispatchers.IO){MobileEngine.call(getApplication(),"restart-tool-check","tools_status",JSONObject(),EventCallback {})}
                if(!restartRequested)return@launch
                require(result.optJSONObject("display")?.optBoolean("can_restart")==true){"Verifique as ferramentas antes de reiniciar."}
                require(!DownloadRuntime.running.get() && !effectsPreparing.value && !loadingPlaybackCollection.value && !jukebox.state.value.busy){"Aguarde as operações em andamento antes de reiniciar."}
                pauseEffectsPlayback();jukebox.pauseForRestart()
                savePlaybackSession(synchronous=true);jukebox.savePlaybackSession(synchronous=true)
                val context=getApplication<Application>()
                check(context.getSharedPreferences("preferences",0).edit().commit()){"Não foi possível salvar a sessão antes de reiniciar."}
                status.value="Reiniciando ONDA…"
                context.startActivity(android.content.Intent(context,RestartActivity::class.java)
                    .putExtra("parent_pid",android.os.Process.myPid()).putExtra("message",translateUi("Reiniciando ONDA…"))
                    .putExtra("dark",OndaStore.settings.value.optString("theme") !in listOf("Claro","Claro puro")).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch(e:Exception){showNotice("Reiniciar ONDA",uiExceptionMessage(e,"Não foi possível reiniciar o ONDA."),true);restartRequested=false;busy.value=false}
        }
    }

    val effectsPreparation=MutableStateFlow<Map<String,String>>(emptyMap())
    val effectsPreparationErrors=MutableStateFlow<Map<String,String>>(emptyMap())
    private fun effectPreparation(source:String,value:String){effectsPreparation.value=effectsPreparation.value+(source to value);if(value!="Erro na preparação")effectsPreparationErrors.value=effectsPreparationErrors.value-source}
    private fun effectFailure(source:String,message:String){effectPreparation(source,"Erro na preparação");effectsPreparationErrors.value=effectsPreparationErrors.value+(source to message)}
    private val retryingEffects=mutableSetOf<String>()
    fun retryEffectsPreparation(source:String) {
        if(!retryingEffects.add(source))return
        viewModelScope.launch {
            var target=source
            try {
                val original=effectsInfo.value[source]
                if(original?.optBoolean("_remote")==true) {
                    effectPreparation(source,"Preparando efeitos…")
                    val id="effects-retry-"+UUID.randomUUID()
                    val result=try {withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"effects_load",OndaStore.config().put("record",original.getJSONObject("record")),EventCallback {})}} finally {MobileEngine.cancel(id)}
                    require(!result.has("error")){result.optString("error")}
                    ensureActive();target=result.getString("source")
                    if(source !in effectsPlaylist.value)return@launch
                    effectsCatalogRecords[target]=result.optJSONObject("record") ?: original.getJSONObject("record")
                    effectsPlaylist.value=effectsPlaylist.value.map {if(it==source)target else it}
                    effectsInfo.value=effectsInfo.value-source
                }
                loadEffectsInfo(listOf(target),retryErrors=true)
                val info=effectsInfo.first {it.containsKey(target)}[target] ?: return@launch
                if(info.has("error"))return@launch
                val duration=info.optDouble("duration")
                if(duration>0){val (speed,reverb,pitch)=effectsControlSnapshot();preloadEffectsTrack(target,speed,reverb,pitch,duration)}
            } catch(e:CancellationException){throw e}
            catch(e:Exception){effectFailure(target,uiExceptionMessage(e,"Não foi possível preparar esta música."))}
            finally {retryingEffects.remove(source)}
        }
    }
    fun loadEffectsInfo(sources:List<String>,retryErrors:Boolean=false) {
        for(source in sources) {
            val cached=effectsInfo.value[source]
            if(cached!=null && (!cached.has("error") || !retryErrors))continue
            if(!effectsInfoRequests.add(source))continue
            if(cached!=null)effectsInfo.value=effectsInfo.value-source
            effectPreparation(source,"Lendo informações…")
            viewModelScope.launch {
                val id="effects-info-"+UUID.randomUUID()
                try {
                    val payload=JSONObject().put("source",source).apply {effectsCatalogRecords[source]?.let {put("record",it)}}
                    val result=effectsInfoSlots.withPermit {withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"effects_info",payload,EventCallback {})}}
                    require(!result.has("error")){result.optString("error")}
                    effectsCatalogRecords[source]?.let {catalog->
                        val tags=result.optJSONObject("record") ?: JSONObject()
                        for(field in listOf("title","artists","album","cover_url"))if(catalog.has(field)&&catalog.optString(field).isNotBlank())tags.put(field,catalog.get(field))
                        result.put("record",tags)
                    }
                    effectsInfo.value=effectsInfo.value+(source to result)
                    effectPreparation(source,"Pronta para reproduzir")
                    lyricRequests.remove(source)?.cancel()
                    // Metadata may arrive after an initial lookup without usable tags.
                    if(lyricsCache.value[source]?.isEmpty()==true)lyricsCache.value=lyricsCache.value-source
                    lookupLyrics(source)
                } catch(error:CancellationException){throw error}
                catch(error:Exception){effectFailure(source,uiExceptionMessage(error,"Não foi possível ler o áudio."));effectsInfo.value=effectsInfo.value+(source to JSONObject().put("error",uiExceptionMessage(error,"Não foi possível ler o áudio.")))}
                finally {effectsInfoRequests.remove(source);MobileEngine.cancel(id)}
            }
        }
    }
    fun appendEffectsFiles(sources:List<String>){sources.forEach {path->jukebox.enqueue(JSONObject().put("_local_source",path).put("title",importedAudioName(path)))}}
    fun moveEffectsTrack(index:Int,direction:Int){val rows=effectsPlaylist.value;if(index !in rows.indices||index+direction !in rows.indices)return;effectsCursor=playbackCursorAfterMove(effectsQueueIndex(effectsSource.value),index,index+direction);effectsPlaylist.value=movePlaybackEntry(rows,index,direction)}
    fun removeEffectsTrack(index:Int){if(index !in effectsPlaylist.value.indices)return;effectsCursor=effectsQueueIndex(effectsSource.value);if(index<=effectsCursor)effectsCursor--;effectsPlaylist.value=effectsPlaylist.value.filterIndexed {i,_->i!=index}}
    fun clearEffectsQueue(){effectsPlaylist.value=emptyList();effectsCursor=-1}
    internal val lyricsCache=MutableStateFlow<Map<String,List<Pair<Double,String>>>>(emptyMap())
    private val lyricRequests=mutableMapOf<String,Job>()
    internal fun storeLyrics(source:String,lines:List<Pair<Double,String>>) {lyricsCache.value=lyricsCache.value+(source to lines)}
    internal fun lookupLyrics(source:String,alternatives:Boolean=false,refresh:Boolean=false,finished:(JSONObject)->Unit={}) {
        if(source.isBlank() || (!alternatives && !refresh && lyricsCache.value.containsKey(source)))return
        if(!alternatives && !refresh && lyricRequests[source]?.isActive==true)return
        lyricRequests.remove(source)?.cancel()
        lyricRequests[source]=viewModelScope.launch {
            val id="lyrics-"+UUID.randomUUID()
            try {
                val record=effectsInfo.value[source]?.optJSONObject("record") ?: effectsCatalogRecords[source]
                    ?: jukebox.state.value.model?.takeIf {it.optString("source")==source}
                val payload=JSONObject().put("source",source).put("alternatives",alternatives)
                record?.let {payload.put("record",JSONObject(it.toString()).apply {if(!has("duration") && !has("duration_ms"))put("duration",effectsInfo.value[source]?.optDouble("duration",0.0) ?: 0.0)})}
                val result=withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"lyrics_online",payload,EventCallback {})}
                ensureActive()
                if(!result.has("error")) {
                    result.optJSONArray("lines")?.let {rows->if(refresh || !lyricsCache.value.containsKey(source))storeLyrics(source,(0 until rows.length()).map {i->rows.getJSONArray(i).let {it.getDouble(0) to it.getString(1)}})}
                }
                finished(result)
            } catch(error:CancellationException){throw error}
            catch(error:Exception){finished(JSONObject().put("error",uiExceptionMessage(error,"Não foi possível buscar a letra.")))}
            finally {MobileEngine.cancel(id)}
        }
    }
    private var effectFullTrack=false
    private var effectDuration=0.0
    private val effectRequests=kotlinx.coroutines.channels.Channel<Pair<Long,JSONObject>>(kotlinx.coroutines.channels.Channel.CONFLATED)
    private var effectRevision=0L
    private var effectRenderId=""
    private var effectSource=""
    private var effectStart=0.0
    private var effectAnchor=0.0
    private var effectSpeed=100
    private var effectOutput=""
    private var effectsSelectedSpeed=85
    private var effectsSelectedReverb=25
    private var effectsSelectedPitch=false
    private var effectsMediaVisible=false
    private var effectsQueueRequest:Job?=null
    fun rememberEffectsControls(speed:Int,reverb:Int,pitch:Boolean){
        if(!effectsControlsMatch(speed,reverb,pitch))effectsPreparation.value=effectsPreparation.value.mapValues {if(it.value in listOf("Efeitos prontos","Preparando efeitos…"))"Aguardando preparação" else it.value}
        effectsSelectedSpeed=speed;effectsSelectedReverb=reverb;effectsSelectedPitch=pitch
    }
    fun effectsControlSnapshot()=Triple(effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch)
    fun effectsControlsMatch(speed:Int,reverb:Int,pitch:Boolean)=effectsSelectedSpeed==speed&&effectsSelectedReverb==reverb&&effectsSelectedPitch==pitch
    internal fun mediaToggleEffects(){if(effectSource.isNotBlank())toggleEffectsPlayback(effectSource,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch)}
    internal fun mediaSeekEffects(seconds:Double){if(effectSource.isNotBlank())seekEffectsPlayback(seconds,effectSource,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch)}
    internal fun mediaPreviousEffects(){val current=effectsQueueIndex(effectSource);if(current>0)playEffectsQueueTrack(current-1) else mediaSeekEffects(0.0)}
    internal fun mediaNextEffects(){advanceEffects(false)}
    private fun advanceEffects(automatic:Boolean) {
        val rows=effectsPlaylist.value.toMutableList()
        val current=effectsQueueIndex(effectSource)
        val target=nextPlaybackIndex(rows.size,current,effectsRepeat.value,automatic)
        if(target !in rows.indices)return
        if(effectsShuffle.value && !(automatic && effectsRepeat.value=="Uma")) {
            val chosen=shuffledNextIndex(rows.size,current,target)
            val temp=rows[target];rows[target]=rows[chosen];rows[chosen]=temp;effectsPlaylist.value=rows
        }
        playEffectsQueueTrack(target)
    }
    fun addPlaybackCollection(records:List<JSONObject>,jukeboxTarget:Boolean) {records.forEach {jukebox.enqueue(it)}}
    internal fun mediaPauseEffects(){pauseEffectsPlayback()}
    fun stopTransientPreview(){if(!effectFullTrack)stopPreview(false)}
    fun playEffectsQueueTrack(index:Int) {
        val source=effectsPlaylist.value.getOrNull(index) ?: return
        effectsQueueRequest?.cancel()
        effectsQueueRequest=viewModelScope.launch {
            loadEffectsInfo(listOf(source),retryErrors=true)
            val info=effectsInfo.first {it.containsKey(source)}[source] ?: return@launch
            if(info.has("error")){status.value=translateError(info.optString("error"));return@launch}
            val duration=info.optDouble("duration",0.0)
            if(duration<=0)return@launch
            effectsQueueRequest=null
            beginEffectsTrackChange();effectsSource.value=source
            selectEffectsSource(source,duration)
            previewEffects(source,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch,0.0,fullTrack=true)
        }
    }
    private fun publishEffectsMedia() {
        if(!effectsMediaVisible){EffectsPlaybackRuntime.clear(this);return}
        val record=effectsInfo.value[effectSource]?.optJSONObject("record")
        EffectsPlaybackRuntime.publish(this,EffectsMediaState(
            source=effectSource,title=record?.optString("title")?.ifBlank {importedAudioName(effectSource)} ?: importedAudioName(effectSource),
            artist=record?.stringList("artists").orEmpty(),album=record?.optString("album").orEmpty(),
            duration=effectDuration,position=effectsPosition.value.toLong(),playing=player.isPlaying,preparing=effectsPreparing.value,
            speed=effectSpeed/100f,hasPrevious=effectDuration>0,hasNext=effectsQueueIndex(effectSource)+1<effectsPlaylist.value.size,
            cover=effectsInfo.value[effectSource]?.optString("cover").orEmpty()))
    }
    private var effectTail:ExoPlayer?=null
    private var effectTailPath=""
    private var effectFade:Job?=null
    private var effectTransitionPending=false
    private var effectGain=1f
    private var effectTailGain=1f
    private data class EffectRenderKey(val source:String,val speed:Int,val reverb:Int,val pitch:Boolean)
    private val preloadedEffects=linkedMapOf<EffectRenderKey,String>()
    private var effectPreload:Job?=null
    private var effectPreloadKey:EffectRenderKey?=null
    private var effectPreloadId=""
    fun isEffectsTrackPreloaded(source:String,speed:Int,reverb:Int,pitch:Boolean)=preloadedEffects.containsKey(EffectRenderKey(source,speed,reverb,pitch))
    fun effectsTransitionSeconds():Int=if(OndaStore.settings.value.optBoolean("jukebox_gradual_transition",true))OndaStore.settings.value.optInt("jukebox_transition_seconds",2).coerceIn(1,10) else 0
    private fun clearEffectTail() {
        effectFade?.cancel();effectFade=null
        effectTail?.release();effectTail=null
        if(effectTailPath.isNotBlank()&&effectTailPath!=effectOutput)java.io.File(effectTailPath).delete()
        effectTailPath="";effectTransitionPending=false;effectGain=1f;effectTailGain=1f
        if(effectFullTrack)player.volume=effectsVolume.value
    }
    fun beginEffectsTrackChange() {
        clearEffectTail()
        if(effectFullTrack&&player.isPlaying&&effectsTransitionSeconds()>0) {
            effectRevision++;if(effectRenderId.isNotBlank())MobileEngine.cancel(effectRenderId)
            effectTail=player;effectTailPath=effectOutput;player.removeListener(previewListener)
            player=ExoPlayer.Builder(getApplication()).build().also {it.addListener(previewListener)}
            effectTransitionPending=true;previewUrl.value="";previewActive.value=false;effectsPreviewEnabled.value=false;effectsPreparing.value=false;effectsPosition.value=0.0;effectsEnded.value=false
        } else stopEffectsPlayback()
    }
    private fun fadeEffectsIn() {
        val outgoing=effectTail ?: return
        val incoming=player
        effectGain=0f;incoming.volume=0f
        effectFade=viewModelScope.launch {
            val ready=withTimeoutOrNull(15000){while(incoming.playbackState!=androidx.media3.common.Player.STATE_READY)delay(20);true} ?: false
            if(!ready){clearEffectTail();return@launch}
            val seconds=minOf(effectsTransitionSeconds().toDouble(),(incoming.duration.coerceAtLeast(0)/2000.0)).coerceAtLeast(.05)
            val steps=(seconds*40).toInt().coerceAtLeast(1)
            for(step in 1..steps){
                effectGain=step.toFloat()/steps;effectTailGain=1f-effectGain
                incoming.volume=effectsVolume.value*effectGain;outgoing.volume=effectsVolume.value*effectTailGain
                delay(25)
            }
            effectFade=null;clearEffectTail()
        }
    }
    fun preloadEffectsTrack(source:String,speed:Int,reverb:Int,pitch:Boolean,duration:Double) {
        if(duration<=0)return
        val key=EffectRenderKey(source,speed,reverb,pitch)
        if(preloadedEffects.containsKey(key) || (effectPreloadKey==key && effectPreload?.isActive==true))return
        effectPreloadKey?.let {old->if(effectsPreparation.value[old.source]=="Preparando efeitos…")effectPreparation(old.source,"Aguardando preparação")}
        effectPreload?.cancel();if(effectPreloadId.isNotBlank())MobileEngine.cancel(effectPreloadId)
        effectPreloadKey=key
        effectPreparation(source,"Preparando efeitos…")
        effectPreload=viewModelScope.launch {
            val id=UUID.randomUUID().toString();effectPreloadId=id
            try {
                val payload=JSONObject().put("source",source).put("speed",speed).put("reverb",reverb).put("keep_pitch",pitch).put("start",0).put("full_track",true).put("duration",EffectsTimeline.remaining(0.0,duration,speed)).put("preview_id",id)
                val result=withContext(Dispatchers.IO){MobileEngine.call(getApplication(),id,"preview",payload,EventCallback {})}
                val path=result.optString("path")
                if(!isActive||effectPreloadKey!=key){if(path.isNotBlank())java.io.File(path).delete()}
                else if(path.isNotBlank()){preloadedEffects[key]=path;effectPreparation(source,"Efeitos prontos")}
                else if(effectPreloadKey==key){effectPreloadKey=null;effectFailure(source,result.optString("error").ifBlank {"Não foi possível preparar esta música."})}
            } catch(error:CancellationException){throw error}
            catch(error:Exception){if(effectPreloadKey==key){effectPreloadKey=null;effectFailure(source,uiExceptionMessage(error,"Não foi possível preparar esta música."))}}
            finally {MobileEngine.cancel(id);if(effectPreloadId==id)effectPreloadId=""}
        }
    }
    init {
        viewModelScope.launch {
            delay(2000)
            val options=OndaStore.settings.value
            if(options.optBoolean("automatic_cache_cleanup",true) && !DownloadRuntime.running.get() && !previewActive.value && onlineImageGallery.value==null)withContext(Dispatchers.IO){MobileEngine.call(getApplication(),"auto-cache-cleanup","cache_auto",JSONObject(),EventCallback {})}
            DownloadSchedule.configure(getApplication(),options,keepExisting=true)
            if(options.optBoolean("resume_queue") && !options.optBoolean("schedule_enabled") && OndaStore.items.value.any {it.state=="Pendente"})DownloadService.start(getApplication())
            if(options.optBoolean("check_updates")) {
                val result=withContext(Dispatchers.IO){MobileEngine.call(getApplication(),"startup-update","app_update",JSONObject().put("version",BuildConfig.VERSION_NAME),EventCallback {})}
                appUpdate.value=result
                if(result.optBoolean("available"))status.value=result.optString("message")+" · Configurações → Ferramentas"
            }
        }
    }
    init {viewModelScope.launch {
        while(isActive) {
            delay(6*3600000L)
            if(OndaStore.settings.value.optBoolean("automatic_cache_cleanup",true) && !busy.value && !DownloadRuntime.running.get() && !previewActive.value && !jukebox.state.value.playing && onlineImageGallery.value==null)
                withContext(Dispatchers.IO){MobileEngine.call(getApplication(),"auto-cache-cleanup","cache_auto",JSONObject(),EventCallback {})}
        }
    }}
    init {viewModelScope.launch {
        for(initial in effectRequests) {
            delay(300)
            var request=initial
            while(true) {val newer=effectRequests.tryReceive().getOrNull() ?: break;request=newer}
            val (revision,payload)=request
            if(!effectsPreviewEnabled.value || revision!=effectRevision) continue
            val id=UUID.randomUUID().toString();effectRenderId=id
            try {
                val position=if(payload.optBoolean("continue_position") && previewUrl.value==effectOutput) effectAnchor+player.currentPosition/1000.0*effectSpeed/100.0 else payload.optDouble("start")
                payload.put("start",position).put("preview_id",id)
                if(payload.optBoolean("full_track"))payload.put("duration",EffectsTimeline.remaining(position,effectDuration,payload.getInt("speed")))
                val key=EffectRenderKey(payload.getString("source"),payload.getInt("speed"),payload.getInt("reverb"),payload.optBoolean("keep_pitch"))
                if(position==0.0 && payload.optBoolean("full_track") && effectPreloadKey==key)effectPreload?.join()
                val cached=if(position==0.0 && payload.optBoolean("full_track"))preloadedEffects.remove(key) else null
                val result=if(cached!=null){JSONObject().put("path",cached)} else withContext(Dispatchers.IO) {MobileEngine.call(getApplication(),id,"preview",payload,EventCallback {})}
                val path=result.optString("path")
                if(revision!=effectRevision || !effectsPreviewEnabled.value) {if(path.isNotBlank()) java.io.File(path).delete();continue}
                if(result.has("error")) {effectFailure(payload.getString("source"),result.getString("error"));clearEffectTail();status.value=translateError(result.getString("error"));effectsPreviewEnabled.value=false;effectsPreparing.value=false;continue}
                val previous=effectOutput
                player.stop()
                effectOutput=path;effectAnchor=position;effectSpeed=payload.getInt("speed")
                effectsPosition.value=position
                preview(path,payload.optDouble("duration",25.0).toInt(),effects=true,fullTrack=payload.optBoolean("full_track"))
                player.volume=effectsVolume.value
                fadeEffectsIn()
                effectsPreparing.value=false
                if(previous.isNotBlank() && previous!=path && previous!=effectTailPath) java.io.File(previous).delete()
            } catch(error:Exception) {if(revision==effectRevision && effectsPreviewEnabled.value) {effectFailure(payload.getString("source"),uiExceptionMessage(error,"Não foi possível preparar esta música."));clearEffectTail();status.value=uiExceptionMessage(error,"Não foi possível atualizar a prévia");effectsPreviewEnabled.value=false;effectsPreparing.value=false}}
            finally {if(effectRenderId==id) effectRenderId=""}
        }
    }}
    init {viewModelScope.launch {
        while(true) {
            if(effectFullTrack && effectsPreviewEnabled.value && previewUrl.value==effectOutput) {
                effectsPosition.value=EffectsTimeline.position(effectAnchor,player.currentPosition,effectSpeed,effectDuration)
                if(player.playbackState==androidx.media3.common.Player.STATE_ENDED) {
                    effectsPosition.value=effectDuration;effectsPreviewEnabled.value=false;effectsEnded.value=true
                    if(effectsQueueRequest?.isActive!=true)advanceEffects(true)
                }
                val upcoming=effectsPlaylist.value.drop((effectsQueueIndex(effectSource)+1).coerceAtLeast(0)).take(2)
                if(!effectsPreparing.value) {
                    val wanted=upcoming.map {EffectRenderKey(it,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch)}.toSet()
                    preloadedEffects.keys.filter {it !in wanted}.forEach {key->preloadedEffects.remove(key)?.also {effectPreparation(key.source,"Aguardando preparação")}?.takeIf {it!=effectOutput&&it!=effectTailPath}?.let {java.io.File(it).delete()}}
                    if(effectPreload?.isActive!=true || effectPreloadKey !in wanted) {
                        upcoming.firstOrNull {!isEffectsTrackPreloaded(it,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch)}?.let {next->
                            val duration=effectsInfo.value[next]?.optDouble("duration",0.0) ?: 0.0
                            preloadEffectsTrack(next,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch,duration)
                        }
                    }
                }
                upcoming.firstOrNull()?.let {next->
                    if(!effectsShuffle.value&&effectsRepeat.value!="Uma"&&player.isPlaying&&!effectsPreparing.value&&effectsQueueRequest?.isActive!=true&&effectsTransitionSeconds()>0&&isEffectsTrackPreloaded(next,effectsSelectedSpeed,effectsSelectedReverb,effectsSelectedPitch)&&EffectsTimeline.remaining(effectsPosition.value,effectDuration,effectSpeed)<=effectsTransitionSeconds())mediaNextEffects()
                }
            }
            publishEffectsMedia()
            delay(100)
        }
    }}
    fun lyricsPosition():Double=if(effectFullTrack)effectsPosition.value else if(effectsPreviewEnabled.value) effectAnchor+player.currentPosition/1000.0*effectSpeed/100.0 else player.currentPosition/1000.0
    fun selectEffectsSource(source:String,duration:Double) {
        val changed=effectSource!=source
        if(changed) {
            if(!effectTransitionPending)stopEffectsPlayback();effectSource=source
            if(source.isNotBlank() && source !in effectsPlaylist.value)effectsPlaylist.value=effectsPlaylist.value+source
        }
        if(changed||duration>0)effectDuration=duration.coerceAtLeast(0.0)
        effectsPlaylist.value.indexOf(source).takeIf {it>=0}?.let {effectsCursor=it}
    }
    fun setEffectsVolume(value:Float) {effectsVolume.value=value.coerceIn(0f,1f);if(effectFullTrack)player.volume=effectsVolume.value*effectGain;effectTail?.volume=effectsVolume.value*effectTailGain}
    fun pauseEffectsPlayback() {
        effectsQueueRequest?.cancel();effectsQueueRequest=null
        clearEffectTail()
        effectsEnded.value=false
        if(effectFullTrack && previewUrl.value==effectOutput)effectsPosition.value=EffectsTimeline.position(effectAnchor,player.currentPosition,effectSpeed,effectDuration)
        effectsPreviewEnabled.value=false;effectsPreparing.value=false;effectRevision++
        if(effectRenderId.isNotBlank())MobileEngine.cancel(effectRenderId)
        previewLimit?.cancel()
        if(effectFullTrack)player.pause()
        publishEffectsMedia()
    }
    fun stopEffectsPlayback() {effectsQueueRequest?.cancel();pauseEffectsPlayback();if(effectFullTrack){player.stop();previewUrl.value=""};effectsPosition.value=0.0;effectsMediaVisible=false;EffectsPlaybackRuntime.clear(this)}
    fun toggleEffectsPlayback(source:String,speed:Int,reverb:Int,pitch:Boolean) {
        if(effectsPreviewEnabled.value) {pauseEffectsPlayback();return}
        if(effectsPosition.value>=effectDuration)effectsPosition.value=0.0
        previewEffects(source,speed,reverb,pitch,effectsPosition.value,fullTrack=true)
    }
    fun seekEffectsPlayback(seconds:Double,source:String,speed:Int,reverb:Int,pitch:Boolean) {
        val running=effectsPreviewEnabled.value
        pauseEffectsPlayback();effectsPosition.value=seconds.coerceIn(0.0,effectDuration)
        if(running && effectsPosition.value<effectDuration)previewEffects(source,speed,reverb,pitch,effectsPosition.value,fullTrack=true)
    }
    fun importConversionBatch(uris:List<Uri>,finished:(List<String>)->Unit) {
        if(busy.value)return
        if(uris.size>1000) {showNotice("Converter em lote","Selecione de 1 a 1000 arquivos.");return}
        busy.value=true
        viewModelScope.launch {
            val imported=mutableListOf<java.io.File>()
            try {
                withContext(Dispatchers.IO) {for(uri in uris) {ensureActive();imported+=OndaStore.importDocument(uri,"conversion-batch")}}
                finished(imported.map {it.absolutePath})
            } catch(error:CancellationException) {imported.forEach {it.delete()};throw error}
            catch(error:Exception) {imported.forEach {it.delete()};status.value=uiExceptionMessage(error,"Não foi possível importar o arquivo")}
            finally {busy.value=false}
        }
    }
    fun previewEffects(source:String,speed:Int,reverb:Int,pitch:Boolean,start:Int) = previewEffects(source,speed,reverb,pitch,start.toDouble())
    fun previewEffects(source:String,speed:Int,reverb:Int,pitch:Boolean,start:Double,fullTrack:Boolean=effectFullTrack) {
        if(fullTrack)jukebox.pause()
        rememberEffectsControls(speed,reverb,pitch)
        val continuing=effectsPreviewEnabled.value && effectSource==source && effectStart==start
        if(!continuing) {player.stop();previewUrl.value=""}
        effectSource=source;effectStart=start;effectFullTrack=fullTrack
        effectsPreviewEnabled.value=true
        effectsEnded.value=false
        effectsPreparing.value=true
        if(fullTrack){effectsMediaVisible=true;publishEffectsMedia();EffectsPlaybackService.start(getApplication())}
        effectRevision++
        if(effectRenderId.isNotBlank()) MobileEngine.cancel(effectRenderId)
        effectRequests.trySend(effectRevision to JSONObject().put("source",source).put("speed",speed).put("reverb",reverb).put("keep_pitch",pitch).put("start",start).put("continue_position",continuing).put("full_track",fullTrack).put("duration",25))
    }
    fun operation(action: String, payload: JSONObject, dialog: Boolean=false, finished: (JSONObject)->Unit = {}) {
        fun report(text:String,error:Boolean=false) {if(dialog) showNotice(operationNoticeTitle(action),text,error) else status.value=if(error)translateError(text) else text}
        if(busy.value) { report("Aguarde a operação atual ou cancele."); return }
        val id=UUID.randomUUID().toString()
        busy.value=true; queryId.value=id; status.value="Preparando…"
        viewModelScope.launch {
            try {
                val result=withContext(Dispatchers.IO) { MobileEngine.call(getApplication(),id,action,payload,EventCallback { raw ->
                    val event=JSONObject(raw)
                    when(event.optString("type")) {
                        "choose_flac","choose_version","choose_catalog","choose_duplicate","choose_media","review_metadata"->OndaStore.ask(id,event)
                        "open_browser"->openSpotifyAuthorization(getApplication(),event.getString("url"))
                        "file"->if(!event.optBoolean("skipped")) OndaStore.publish(event.getString("path"),OndaStore.publicationConfig(payload,event).put("_identity",id),event.optString("mode", "MP3"))
                        "batch_original"->{
                            val edited=java.io.File(event.getString("path"))
                            val original=JSONObject(payload.toString()).put("source",event.getString("source")).put("original_uri",event.getString("original_uri"))
                            try {OndaStore.overwriteAudio(edited,original)} finally {edited.delete()}
                        }
                        "done"->if(event.has("path")) OndaStore.publish(event.getString("path"),payload,event.getString("path").substringAfterLast('.'))
                        "progress"->status.value="Processando: ${event.optInt("percent")}%"
                        "error"->status.value=translateError(event.optString("message"))
                        else->if(event.has("message")) status.value=event.optString("message")
                    }
                }) }
                if(!result.has("error") && action=="audio_edit" && payload.optBoolean("overwrite_original")) {
                    withContext(Dispatchers.IO) {
                        val edited=java.io.File(result.getString("path"))
                        try { OndaStore.overwriteAudio(edited,payload) }
                        finally {edited.delete();java.io.File(edited.parentFile,edited.nameWithoutExtension+".lrc").delete()}
                    }
                }
                if(result.has("error")) report(result.optString("error"),true) else {
                    report(result.optString("message","Concluído"))
                    if(result.has("connected"))spotifyConnected.value=result.optBoolean("connected")
                    finished(result)
                }
            } catch(error: Exception) { report(uiExceptionMessage(error,"Erro na operação"),true) }
            finally {
                if(action=="audio_batch_edit")payload.optJSONArray("sources")?.objects()?.forEach {entry->
                    val file=java.io.File(entry.optString("source"))
                    val imports=java.io.File(getApplication<Application>().filesDir,"imports").canonicalFile
                    if(file.canonicalFile.parentFile==imports && file.name.startsWith("batch-audio-"))file.delete()
                }
                busy.value=false; OndaStore.dismissQuestions(id); queryId.value=""
            }
        }
    }
    fun openHistoryFolder(uri: String) {
        viewModelScope.launch {
            try {
                val folder=withContext(Dispatchers.IO) {historyFolderUri(getApplication(),Uri.parse(uri))}
                openHistoryFolder(getApplication(),folder)
            } catch(error: Exception) {status.value=uiExceptionMessage(error,"Não foi possível abrir a pasta deste arquivo.")}
        }
    }
    fun connectSpotify() {
        if(OndaStore.settings.value.optString("spotify_client_id").isBlank()) {
            showNotice("Conectar Spotify","Preencha o Spotify Client ID antes de conectar sua conta. O Client Secret é opcional para esta conexão.")
            return
        }
        val options=OndaStore.config()
        val callbackMessages=JSONObject()
        for(text in listOf("Autorização recebida. Volte para o ONDA.","Autorização não concedida. Volte para o ONDA.","Retorno inválido. Volte para o ONDA e tente novamente.","Voltar para o ONDA","Fechar esta aba","Voltando em {seconds} segundos…","Voltando para o ONDA…","Se a aba continuar aberta, você pode fechá-la e voltar para o ONDA.","Voltando em 3 segundos…","Feche esta aba e tente conectar novamente.")) callbackMessages.put(text,translateUi(text))
        options.put("ui_messages",callbackMessages)
        operation("spotify_connect",options,dialog=true)
    }
    fun cancel() { if(MobileEngine.toolsState.value.running)return;collectionSyncJob?.cancel();OndaStore.dismissQuestions(queryId.value);MobileEngine.cancel(queryId.value) }
    private val releaseDates=mutableMapOf<String,String>()
    private val releaseDateSlots=kotlinx.coroutines.sync.Semaphore(2)
    suspend fun releaseDate(record:JSONObject):String {
        val existing=record.cleanString("release_date")
        if(existing.isNotBlank() || record.cleanString("platform")!="Deezer")return existing
        val url=record.cleanString("source_url")
        releaseDates[url]?.let {return it}
        releaseDateSlots.acquire()
        try {
            releaseDates[url]?.let {return it}
            val date=try {
                withContext(Dispatchers.IO) {
                    MobileEngine.call(getApplication(),UUID.randomUUID().toString(),"release_date",JSONObject().put("record",JSONObject(record.toString())),EventCallback {}).cleanString("release_date")
                }
            } catch(e:CancellationException) {throw e} catch(_:Exception) {""}
            if(releaseDates.size>=500)releaseDates.clear()
            releaseDates[url]=date
            return date
        } finally {releaseDateSlots.release()}
    }
    private var searchRevision=0
    fun search(query: String, provider: String, refresh: Boolean=false) {
        if(busy.value)return
        val config=OndaStore.config()
        val configured=spotifyConnected.value || (config.optString("spotify_client_id").isNotBlank() && config.optString("spotify_client_secret").isNotBlank())
        if(provider=="Spotify" && !configured && !query.trim().let {it.startsWith("https://") || it.startsWith("http://") || it.startsWith("spotify:")}) {
            showNotice("Configure a API do Spotify","Para pesquisar músicas no Spotify, configure a API em Configurações → Contas. Informe o Client ID e conecte sua conta, ou preencha Client ID e Client Secret. Você também pode pesquisar no Deezer ou Apple / iTunes.")
            return
        }
        val revision=++searchRevision
        operation("search",config.put("query",query).put("provider",provider).put("refresh_search",refresh)) {
            if(revision==searchRevision) {
                searchResults.value=it.optJSONArray("tracks")?.objects() ?: emptyList()
                status.value=listOf("${searchResults.value.size} resultado(s).",it.stringList("warnings"),it.stringList("suggestions")).filter {text->text.isNotBlank()}.joinToString(" ")
            }
        }
    }
    fun loadCollection(url: String, options: JSONObject, startDownload:Boolean=false,queueOnly:Boolean=false) = operation("collection",OndaStore.config(options).put("url",url)) {
        collectionComparison.value=null
        collection.value=it.put("_collection_url",url)
        if(startDownload || queueOnly)queueCollection(it.optJSONArray("tracks")?.objects() ?: emptyList(),options,it.optString("folder_title",it.optString("title","Playlist")),startDownload)
    }
    fun compareCollectionLocal(tree:Uri,url:String,options:JSONObject,reload:Boolean) {
        if(busy.value || addingToQueue.value)return
        busy.value=true;collectionComparison.value=null
        val id="collection-sync-"+java.util.UUID.randomUUID()
        queryId.value=id;status.value="Conferindo arquivos locais…"
        val current=collection.value
        val queued=JSONArray(OndaStore.items.value.filter {it.state!="Concluído"}.map {JSONObject(it.config.toString()).put("state",it.state)})
        collectionSyncJob=viewModelScope.launch {
            try {
                val snapshot=withContext(Dispatchers.IO) {
                    val loaded=if(reload)MobileEngine.call(getApplication(),id,"collection",OndaStore.config(options).put("url",url),EventCallback {}) else JSONObject(current.toString())
                    require(!loaded.has("error")) {loaded.optString("error")}
                    if(reload)loaded.put("_collection_url",url)
                    require((loaded.optJSONArray("tracks")?.length() ?: 0)>0) {"Carregue um álbum ou playlist"}
                    val scopeContext=coroutineContext
                    val inventory=playlistInventory(getApplication(),tree,OndaStore.comparisonHistory()) {scopeContext.ensureActive()}
                    val payload=JSONObject().put("tracks",loaded.getJSONArray("tracks")).put("inventory",inventory).put("queued",queued)
                        .put("source",loaded.optString("_collection_url")).put("database",getApplication<Application>().getDatabasePath("onda.sqlite3").absolutePath)
                    val report=MobileEngine.call(getApplication(),id,"collection_compare",payload,EventCallback {})
                    require(!report.has("error")) {report.optString("error")}
                    loaded to report
                }
                collection.value=snapshot.first;collectionComparison.value=snapshot.second
                status.value=collectionSyncSummary(snapshot.second)
            } catch(error:CancellationException) {status.value="Conferência cancelada.";throw error}
            catch(error:Exception) {showNotice("Conferir arquivos locais",uiExceptionMessage(error,"Não foi possível conferir os arquivos."))}
            finally {busy.value=false;queryId.value="";collectionSyncJob=null}
        }
    }
    fun importCollection(path: String) = operation("import",OndaStore.config().put("path",path).put("extension",path.substringAfterLast('.'))) { collectionComparison.value=null;collection.value=it }
    fun importLocal(uri: Uri, category: String, dialog: Boolean=false, finished: (java.io.File)->Unit) {
        status.value="Importando arquivo…"
        viewModelScope.launch {
            try {
                val file=withContext(Dispatchers.IO) {OndaStore.importDocument(uri,category)}
                status.value="Arquivo importado"
                finished(file)
            } catch(error: Exception) {val message=uiExceptionMessage(error,"Não foi possível importar o arquivo");if(dialog) showNotice(importNoticeTitle(category),message) else status.value=message}
        }
    }
    fun enqueueLink(url: String, immediate: Boolean=false): String {
        val id=OndaStore.enqueue(url,extra=JSONObject().put("_immediate",immediate))
        queueInformationRequested.add(id)
        viewModelScope.launch(Dispatchers.IO) {
            titleSlots.acquire()
            try {
                repeat(2) {attempt->
                    val current=OndaStore.items.value.firstOrNull {it.id==id}
                    if(current==null || current.state !in setOf("Pendente","Duplicata") || current.title!=url)return@launch
                    val result=MobileEngine.call(getApplication(),"title-$id","describe",OndaStore.config().put("url",url),EventCallback {})
                    if(!result.has("error")) {
                        OndaStore.renamePendingLink(id,url,result.optString("title"),result.optJSONObject("queue_info"))
                        return@launch
                    }
                    if(attempt==0)delay(1000)
                }
            } catch(_: Exception) { /* The original link remains usable if title lookup fails. */ }
            finally {titleSlots.release()}
        }
        return id
    }
    private val queueInformationRequested=java.util.concurrent.ConcurrentHashMap.newKeySet<String>()
    fun loadQueueInformation(item:DownloadItem) {
        if(!queueInformationRequested.add(item.id))return
        val url=item.config.optString("url")
        if(!url.contains("spotify") && !url.contains("deezer") && !url.contains("apple.com") && !url.contains("youtu"))return
        viewModelScope.launch(Dispatchers.IO) {
            titleSlots.acquire()
            try {
                val result=MobileEngine.call(getApplication(),"info-${item.id}","describe",OndaStore.config().put("url",url),EventCallback {})
                result.optJSONObject("queue_info")?.let {OndaStore.updateQueueInformation(item.id,url,it)}
            } catch(_:Exception) { /* Optional display metadata must not block the queue. */ }
            finally {titleSlots.release()}
        }
    }
    fun useInEffects(uri: String) {
        importLocal(Uri.parse(uri),"audio") { file ->
            stopPreview(false)
            jukebox.prepare(file.absolutePath);playbackMode.value=1;effectsNavigation.value=true
        }
    }
    fun preview(url: String, seconds: Int=25, startSeconds: Int=0, effects:Boolean=false,fullTrack:Boolean=false) {
        previewRequest.cancel()
        if(!effects) {effectsPreviewEnabled.value=false;effectRevision++;if(effectRenderId.isNotBlank()) MobileEngine.cancel(effectRenderId)}
        previewFromDialog=false
        if(effects && fullTrack)jukebox.pause() else jukebox.stop()
        previewUrl.value=url
        previewLimit?.cancel()
        player.setMediaItem(MediaItem.fromUri(url),startSeconds.coerceAtLeast(0)*1000L); player.prepare(); player.play()
        if(!effects) {effectFullTrack=false;effectsMediaVisible=false;EffectsPlaybackRuntime.clear(this);player.volume=1f}
        if(!fullTrack)previewLimit=viewModelScope.launch { delay(seconds*1000L); player.pause();effectsPreviewEnabled.value=false }
    }
    fun stopPreview(stopJukebox:Boolean=true) { if(effectFullTrack)pauseEffectsPlayback();previewRequest.cancel();if(stopJukebox)jukebox.stop(); effectsPreviewEnabled.value=false;effectsPreparing.value=false;effectRevision++;if(effectRenderId.isNotBlank()) MobileEngine.cancel(effectRenderId);previewLimit?.cancel(); player.stop();previewActive.value=false;previewUrl.value="" }
    @androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
    fun previewYouTube(url: String) {
        stopPreview();previewFromDialog=true;previewUrl.value=url
        status.value="Preparando prévia da versão escolhida…"
        previewRequest.start(
            resolve={id->withContext(Dispatchers.IO) {MobileEngine.call(getApplication(),id,"resolve_preview",OndaStore.config().put("url",url),EventCallback {})}},
            onResult={result->
                if(result.has("error"))throw IllegalStateException(result.getString("error"))
                val headers=result.optJSONObject("headers") ?: JSONObject()
                val properties=headers.keys().asSequence().associateWith {headers.getString(it)}
                val http=DefaultHttpDataSource.Factory().setDefaultRequestProperties(properties)
                val source=DefaultMediaSourceFactory(DefaultDataSource.Factory(getApplication(),http)).createMediaSource(MediaItem.fromUri(result.getString("url")))
                player.setMediaSource(source);player.prepare();player.play()
                previewLimit?.cancel()
                previewLimit=viewModelScope.launch {delay(OndaStore.settings.value.optInt("search_preview",25)*1000L);player.pause()}
                status.value="Prévia da versão selecionada"
            },
            onError={error->showNotice("Ouvir prévia",uiExceptionMessage(error,"Não foi possível ouvir a prévia"))}
        )
    }
    fun queueTrack(record: JSONObject, options: JSONObject=OndaStore.settings.value, group: String?=null, origin: String="", immediate: Boolean=false): String {
        val url=record.optString("source_url")
        require(url.isNotBlank()) { "Faixa sem link" }
        val extra=JSONObject().put("_origin",origin).put("_immediate",immediate).put("queue_info",JSONObject().apply {listOf("title","artists","album","cover_url","duration_ms","release_date","genre","track_number","disc_number","platform").forEach {key->if(record.has(key) && !record.isNull(key))put(key,record.get(key))}})
        if(record.optString("platform")=="Spotify") extra.put("catalog_record",record)
        if(group!=null) extra.put("playlist_title",group)
        return OndaStore.enqueue(url,"${record.stringList("artists")} - ${record.optString("title")}".trim(' ','-'),options,extra)
    }
    fun enqueueLinks(urls:List<String>,now:Boolean) {
        if(addingToQueue.value || urls.isEmpty())return
        addingToQueue.value=true
        val options=JSONObject(OndaStore.settings.value.toString()).put("_duplicate_batch",UUID.randomUUID().toString())
        viewModelScope.launch {
            val ids=mutableListOf<String>()
            try {
                for(chunk in urls.chunked(100)) {
                    ids+=withContext(Dispatchers.IO) {OndaStore.enqueueBatch {chunk.map {OndaStore.enqueue(it,options=options,extra=JSONObject().put("_immediate",now))}.filter {it.isNotBlank()}}}
                    status.value="${ids.size} de ${urls.size} itens adicionados à fila";yield()
                }
                if(now && ids.isNotEmpty()) {DownloadService.batch(getApplication(),ids);queueNavigation.value=true}
                status.value="${ids.size} itens adicionados à fila"
            } catch(error:CancellationException) {throw error}
            catch(error:Exception) {showNotice("Adicionar à fila","${ids.size} de ${urls.size} itens adicionados à fila"+"\n"+(uiExceptionMessage(error,"Falha ao adicionar itens. Os itens já adicionados foram preservados.")))}
            finally {addingToQueue.value=false}
        }
    }
    fun queueCollection(rows:List<JSONObject>,options:JSONObject,group:String,now:Boolean) {
        if(addingToQueue.value || rows.isEmpty())return
        addingToQueue.value=true
        val batchOptions=JSONObject(options.toString()).put("_duplicate_batch",UUID.randomUUID().toString())
        viewModelScope.launch {
            val ids=mutableListOf<String>()
            try {
                // Bounded transactions publish progress without one refresh per song.
                for(chunk in rows.chunked(100)) {
                    ids+=withContext(Dispatchers.IO) {OndaStore.enqueueBatch {chunk.map {queueTrack(it,batchOptions,group,immediate=now)}.filter {it.isNotBlank()}}}
                    status.value="${ids.size} de ${rows.size} itens adicionados à fila"
                    yield()
                }
                if(now && ids.isNotEmpty()) {DownloadService.batch(getApplication(),ids);queueNavigation.value=true}
                status.value="${ids.size} itens adicionados à fila"
            } catch(error:CancellationException) {throw error}
            catch(error:Exception) {showNotice("Adicionar à fila","${ids.size} de ${rows.size} itens adicionados à fila"+"\n"+(uiExceptionMessage(error,"Falha ao adicionar itens. Os itens já adicionados foram preservados.")))}
            finally {addingToQueue.value=false}
        }
    }
    internal fun savePlaybackSession(synchronous:Boolean=false) {
        val data=JSONObject().put("source",effectsSource.value).put("position",effectsPosition.value.takeIf {it.isFinite()} ?: 0.0).put("duration",effectDuration.takeIf {it.isFinite()} ?: 0.0)
            .put("queue",JSONArray(effectsPlaylist.value)).put("repeat",effectsRepeat.value).put("shuffle",effectsShuffle.value)
            .put("speed",effectsSelectedSpeed).put("reverb",effectsSelectedReverb).put("pitch",effectsSelectedPitch).put("mode",playbackMode.value)
            .put("info",JSONObject().apply {effectsInfo.value.forEach {(key,value)->put(key,JSONObject(value.toString()).apply {remove("cover")})}})
        PlaybackSessions.save(getApplication(),"effects",data,synchronous)
    }
    init {
        PlaybackSessions.load(getApplication(),"effects")?.let {data->
            effectsPlaylist.value=data.optJSONArray("queue")?.let {a->(0 until a.length()).map {a.optString(it)}.filter {java.io.File(it).isFile}} ?: emptyList()
            data.optJSONObject("info")?.let {infos->effectsInfo.value=infos.keys().asSequence().mapNotNull {key->infos.optJSONObject(key)?.let {key to it}}.toMap()}
            val source=data.optString("source")
            if(java.io.File(source).isFile()) {
                effectSource=source;effectsSource.value=source;effectDuration=data.optDouble("duration",0.0).takeIf {it.isFinite()&&it>=0} ?: 0.0
                effectsPosition.value=(data.optDouble("position",0.0).takeIf {it.isFinite()} ?: 0.0).coerceIn(0.0,effectDuration)
                effectsCursor=effectsPlaylist.value.indexOf(source)
            }
            effectsRepeat.value=data.optString("repeat").takeIf {it in listOf("Desativada","Todas","Uma")} ?: "Desativada";effectsShuffle.value=data.optBoolean("shuffle")
            effectsSelectedSpeed=data.optInt("speed",85).coerceIn(50,150);effectsSelectedReverb=data.optInt("reverb",25).coerceIn(0,100);effectsSelectedPitch=data.optBoolean("pitch")
            if(!data.isNull("mode"))playbackMode.value=data.optInt("mode").takeIf {it in 0..1}
        }
        jukebox.migrateEffectsSession(PlaybackSessions.load(getApplication(),"effects"))
        playbackMode.value=1
        viewModelScope.launch {while(isActive){delay(5000);savePlaybackSession()}}
    }
    override fun onCleared() { closeOnlineImages();cancelOnlineImagePreview();cancelPlaybackCollection();savePlaybackSession();jukebox.stopOtherAudio={};stopPreview(false);EffectsPlaybackRuntime.clear(this);cancel();effectRequests.close();effectPreload?.cancel();if(effectPreloadId.isNotBlank())MobileEngine.cancel(effectPreloadId);preloadedEffects.values.forEach {java.io.File(it).delete()};player.release(); super.onCleared() }
}
