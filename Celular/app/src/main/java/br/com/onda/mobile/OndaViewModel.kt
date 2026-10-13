package br.com.onda.mobile

import android.app.Application
import android.content.Intent
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
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

fun JSONArray.objects(): List<JSONObject> = (0 until length()).mapNotNull { optJSONObject(it) }
fun JSONObject.cleanString(key: String): String = if(isNull(key)) "" else optString(key)
fun JSONObject.stringList(key: String): String = optJSONArray(key)?.let { a -> (0 until a.length()).joinToString(", ") { a.optString(it) } } ?: ""

class OndaViewModel(application: Application) : AndroidViewModel(application) {
    private val titleSlots=kotlinx.coroutines.sync.Semaphore(2)
    val effectsSource=MutableStateFlow("")
    val searchResults=MutableStateFlow<List<JSONObject>>(emptyList())
    val collection=MutableStateFlow(JSONObject())
    val busy=MutableStateFlow(false)
    val status=MutableStateFlow("")
    val dialogNotice=MutableStateFlow("")
    val queryId=MutableStateFlow("")
    private var previewFromDialog=false
    val player=ExoPlayer.Builder(application).build()
    val previewUrl=MutableStateFlow("")
    val previewActive=MutableStateFlow(false)
    init {player.addListener(object: androidx.media3.common.Player.Listener {
        override fun onEvents(player: androidx.media3.common.Player, events: androidx.media3.common.Player.Events) {
            previewActive.value=player.playWhenReady && player.playbackState in listOf(androidx.media3.common.Player.STATE_BUFFERING,androidx.media3.common.Player.STATE_READY)
        }
        override fun onPlayerError(error:androidx.media3.common.PlaybackException) {previewActive.value=false;val text="Não foi possível reproduzir esta prévia. Tente novamente ou escolha outra faixa.";if(previewFromDialog) dialogNotice.value=text else status.value=text}
    })}
    private var previewLimit: Job?=null
    val effectsPreviewEnabled=MutableStateFlow(false)
    private val effectRequests=kotlinx.coroutines.channels.Channel<Pair<Long,JSONObject>>(kotlinx.coroutines.channels.Channel.CONFLATED)
    private var effectRevision=0L
    private var effectRenderId=""
    private var effectSource=""
    private var effectStart=0
    private var effectAnchor=0.0
    private var effectSpeed=100
    private var effectOutput=""
    init {viewModelScope.launch {
        for(initial in effectRequests) {
            delay(300)
            var request=initial
            while(true) {val newer=effectRequests.tryReceive().getOrNull() ?: break;request=newer}
            val (revision,payload)=request
            if(!effectsPreviewEnabled.value || revision!=effectRevision) continue
            val id=UUID.randomUUID().toString();effectRenderId=id
            try {
                val position=if(player.isPlaying && previewUrl.value==effectOutput) effectAnchor+player.currentPosition/1000.0*effectSpeed/100.0 else payload.optDouble("start")
                payload.put("start",position).put("preview_id",id)
                val result=withContext(Dispatchers.IO) {MobileEngine.call(getApplication(),id,"preview",payload,EventCallback {})}
                val path=result.optString("path")
                if(revision!=effectRevision || !effectsPreviewEnabled.value) {if(path.isNotBlank()) java.io.File(path).delete();continue}
                if(result.has("error")) {status.value=result.getString("error");effectsPreviewEnabled.value=false;continue}
                val previous=effectOutput
                player.stop()
                effectOutput=path;effectAnchor=position;effectSpeed=payload.getInt("speed")
                preview(path,payload.getInt("duration"),effects=true)
                if(previous.isNotBlank() && previous!=path) java.io.File(previous).delete()
            } catch(error:Exception) {if(revision==effectRevision && effectsPreviewEnabled.value) {status.value=error.message ?: "Não foi possível atualizar a prévia";effectsPreviewEnabled.value=false}}
            finally {if(effectRenderId==id) effectRenderId=""}
        }
    }}
    fun previewEffects(source:String,speed:Int,reverb:Int,pitch:Boolean,start:Int) {
        val continuing=effectsPreviewEnabled.value && effectSource==source && effectStart==start
        if(!continuing) {player.stop();previewUrl.value=""}
        effectSource=source;effectStart=start
        effectsPreviewEnabled.value=true
        effectRevision++
        if(effectRenderId.isNotBlank()) MobileEngine.cancel(effectRenderId)
        effectRequests.trySend(effectRevision to JSONObject().put("source",source).put("speed",speed).put("reverb",reverb).put("keep_pitch",pitch).put("start",start).put("duration",OndaStore.settings.value.optInt("effects_preview",25)))
    }
    fun operation(action: String, payload: JSONObject, dialog: Boolean=false, finished: (JSONObject)->Unit = {}) {
        fun report(text:String) {if(dialog) dialogNotice.value=text else status.value=text}
        if(busy.value) { report("Aguarde a operação atual ou cancele."); return }
        val id=UUID.randomUUID().toString()
        busy.value=true; queryId.value=id; status.value="Preparando…"
        viewModelScope.launch {
            try {
                val result=withContext(Dispatchers.IO) { MobileEngine.call(getApplication(),id,action,payload,EventCallback { raw ->
                    val event=JSONObject(raw)
                    when(event.optString("type")) {
                        "choose_version","choose_catalog","choose_duplicate","choose_media","review_metadata"->OndaStore.ask(id,event)
                        "open_browser"->openSpotifyAuthorization(getApplication(),event.getString("url"))
                        "file"->if(!event.optBoolean("skipped")) OndaStore.publish(event.getString("path"),OndaStore.publicationConfig(payload,event).put("_identity",id),event.optString("mode", "MP3"))
                        "done"->if(event.has("path")) OndaStore.publish(event.getString("path"),payload,event.getString("path").substringAfterLast('.'))
                        "progress"->status.value="Processando: ${event.optInt("percent")}%"
                        "error"->status.value=event.optString("message")
                        else->if(event.has("message")) status.value=event.optString("message")
                    }
                }) }
                if(result.has("error")) report(result.optString("error")) else {
                    report(result.optString("message","Concluído"))
                    finished(result)
                }
            } catch(error: Exception) { report(error.message ?: "Erro na operação") }
            finally { busy.value=false; OndaStore.dismissQuestions(id); queryId.value="" }
        }
    }
    fun openHistoryFolder(uri: String) {
        viewModelScope.launch {
            try {
                val folder=withContext(Dispatchers.IO) {historyFolderUri(getApplication(),Uri.parse(uri))}
                openHistoryFolder(getApplication(),folder)
            } catch(error: Exception) {status.value=error.message ?: "Não foi possível abrir a pasta deste arquivo."}
        }
    }
    fun connectSpotify() {
        if(OndaStore.settings.value.optString("spotify_client_id").isBlank()) {
            dialogNotice.value="Preencha o Spotify Client ID antes de conectar sua conta. O Client Secret é opcional para esta conexão."
            return
        }
        operation("spotify_connect",OndaStore.config(),dialog=true)
    }
    fun cancel() { OndaStore.dismissQuestions(queryId.value);MobileEngine.cancel(queryId.value) }
    fun search(query: String, provider: String) = operation("search",OndaStore.config().put("query",query).put("provider",provider)) { searchResults.value=it.optJSONArray("tracks")?.objects() ?: emptyList() }
    fun loadCollection(url: String, options: JSONObject) = operation("collection",OndaStore.config(options).put("url",url)) { collection.value=it }
    fun importCollection(path: String) = operation("import",OndaStore.config().put("path",path).put("extension",path.substringAfterLast('.'))) { collection.value=it }
    fun importLocal(uri: Uri, category: String, dialog: Boolean=false, finished: (java.io.File)->Unit) {
        status.value="Importando arquivo…"
        viewModelScope.launch {
            try {
                val file=withContext(Dispatchers.IO) {OndaStore.importDocument(uri,category)}
                status.value="Arquivo importado"
                finished(file)
            } catch(error: Exception) {val message=error.message ?: "Não foi possível importar o arquivo";if(dialog) dialogNotice.value=message else status.value=message}
        }
    }
    fun enqueueLink(url: String, immediate: Boolean=false): String {
        val id=OndaStore.enqueue(url,extra=JSONObject().put("_immediate",immediate))
        viewModelScope.launch(Dispatchers.IO) {
            titleSlots.acquire()
            try {
                val result=MobileEngine.call(getApplication(),"title-$id","describe",OndaStore.config().put("url",url),EventCallback {})
                if(!result.has("error")) OndaStore.rename(id,result.optString("title"))
            } catch(_: Exception) { /* The original link remains usable if title lookup fails. */ }
            finally {titleSlots.release()}
        }
        return id
    }
    fun useInEffects(uri: String) {
        importLocal(Uri.parse(uri),"audio") { file ->
            stopPreview()
            effectsSource.value=file.absolutePath
        }
    }
    fun preview(url: String, seconds: Int=25, startSeconds: Int=0, effects:Boolean=false) {
        if(!effects) {effectsPreviewEnabled.value=false;effectRevision++;if(effectRenderId.isNotBlank()) MobileEngine.cancel(effectRenderId)}
        previewFromDialog=false
        previewUrl.value=url
        previewLimit?.cancel()
        player.setMediaItem(MediaItem.fromUri(url),startSeconds.coerceAtLeast(0)*1000L); player.prepare(); player.play()
        previewLimit=viewModelScope.launch { delay(seconds*1000L); player.pause();effectsPreviewEnabled.value=false }
    }
    fun stopPreview() { effectsPreviewEnabled.value=false;effectRevision++;if(effectRenderId.isNotBlank()) MobileEngine.cancel(effectRenderId);previewLimit?.cancel(); player.stop();previewActive.value=false;previewUrl.value="" }
    @androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
    fun previewYouTube(url: String) {
        stopPreview();previewFromDialog=true;previewUrl.value=url
        viewModelScope.launch {
            status.value="Preparando prévia da versão escolhida…"
            try {
                val result=withContext(Dispatchers.IO) {MobileEngine.call(getApplication(),UUID.randomUUID().toString(),"resolve_preview",OndaStore.config().put("url",url),EventCallback {})}
                if(result.has("error")) {dialogNotice.value=result.getString("error");return@launch}
                val headers=result.optJSONObject("headers") ?: JSONObject()
                val properties=headers.keys().asSequence().associateWith {headers.getString(it)}
                val http=DefaultHttpDataSource.Factory().setDefaultRequestProperties(properties)
                val source=DefaultMediaSourceFactory(DefaultDataSource.Factory(getApplication(),http)).createMediaSource(MediaItem.fromUri(result.getString("url")))
                player.setMediaSource(source);player.prepare();player.play()
                previewLimit?.cancel()
                previewLimit=viewModelScope.launch {delay(OndaStore.settings.value.optInt("search_preview",25)*1000L);player.pause()}
                status.value="Prévia da versão selecionada"
            } catch(error: Exception) {dialogNotice.value=error.message ?: "Não foi possível ouvir a prévia"}
        }
    }
    fun queueTrack(record: JSONObject, options: JSONObject=OndaStore.settings.value, group: String?=null, origin: String="", immediate: Boolean=false): String {
        val url=record.optString("source_url")
        require(url.isNotBlank()) { "Faixa sem link" }
        val extra=JSONObject().put("_origin",origin).put("_immediate",immediate)
        if(record.optString("platform")=="Spotify") extra.put("catalog_record",record)
        if(group!=null) extra.put("playlist_title",group)
        return OndaStore.enqueue(url,"${record.stringList("artists")} - ${record.optString("title")}".trim(' ','-'),options,extra)
    }
    fun queueCollection(rows:List<JSONObject>,options:JSONObject,group:String,now:Boolean) {
        viewModelScope.launch {
            val ids=withContext(Dispatchers.IO) {OndaStore.enqueueBatch {rows.map {queueTrack(it,options,group,immediate=now)}}}
            if(now && ids.isNotEmpty()) DownloadService.batch(getApplication(),ids)
            status.value="${ids.size} itens adicionados à fila"
        }
    }
    override fun onCleared() { stopPreview();cancel();effectRequests.close(); player.release(); super.onCleared() }
}
