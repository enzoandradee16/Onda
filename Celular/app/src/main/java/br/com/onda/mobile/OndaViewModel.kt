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
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

fun JSONArray.objects(): List<JSONObject> = (0 until length()).mapNotNull { optJSONObject(it) }
fun JSONObject.cleanString(key: String): String = if(isNull(key)) "" else optString(key)
fun JSONObject.stringList(key: String): String = optJSONArray(key)?.let { a -> (0 until a.length()).joinToString(", ") { a.optString(it) } } ?: ""

data class DialogNotice(val title:String,val message:String)

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
    "video_probe","video_convert"->"Conversor de vídeos"
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
    private val titleSlots=kotlinx.coroutines.sync.Semaphore(2)
    val effectsSource=MutableStateFlow("")
    val searchResults=MutableStateFlow<List<JSONObject>>(emptyList())
    val collection=MutableStateFlow(JSONObject())
    val busy=MutableStateFlow(false)
    val status=MutableStateFlow("")
    val addingToQueue=MutableStateFlow(false)
    val queueNavigation=MutableStateFlow(false)
    val dialogNotice=MutableStateFlow<DialogNotice?>(null)
    fun showNotice(title:String,message:String) {dialogNotice.value=DialogNotice(title,message)}
    fun dismissNotice() {dialogNotice.value=null}
    val queryId=MutableStateFlow("")
    private var previewFromDialog=false
    val player=ExoPlayer.Builder(application).build()
    val previewUrl=MutableStateFlow("")
    val previewActive=MutableStateFlow(false)
    init {player.addListener(object: androidx.media3.common.Player.Listener {
        override fun onEvents(player: androidx.media3.common.Player, events: androidx.media3.common.Player.Events) {
            previewActive.value=player.playWhenReady && player.playbackState in listOf(androidx.media3.common.Player.STATE_BUFFERING,androidx.media3.common.Player.STATE_READY)
        }
        override fun onPlayerError(error:androidx.media3.common.PlaybackException) {previewActive.value=false;val text="Não foi possível reproduzir esta prévia. Tente novamente ou escolha outra faixa.";if(previewFromDialog) showNotice("Ouvir prévia",text) else status.value=text}
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
    init {
        viewModelScope.launch {
            delay(2000)
            val options=OndaStore.settings.value
            DownloadSchedule.configure(getApplication(),options,keepExisting=true)
            if(options.optBoolean("resume_queue") && !options.optBoolean("schedule_enabled") && OndaStore.items.value.any {it.state=="Pendente"})DownloadService.start(getApplication())
            if(options.optBoolean("check_updates")) {
                val result=withContext(Dispatchers.IO){MobileEngine.call(getApplication(),"startup-update","app_update",JSONObject().put("version",BuildConfig.VERSION_NAME),EventCallback {})}
                if(result.optBoolean("available"))status.value=result.optString("message")+" · Configurações → Ferramentas"
            }
        }
    }
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
        fun report(text:String) {if(dialog) showNotice(operationNoticeTitle(action),text) else status.value=text}
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
                        "error"->status.value=event.optString("message")
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
                if(result.has("error")) report(result.optString("error")) else {
                    report(result.optString("message","Concluído"))
                    finished(result)
                }
            } catch(error: Exception) { report(error.message ?: "Erro na operação") }
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
            } catch(error: Exception) {status.value=error.message ?: "Não foi possível abrir a pasta deste arquivo."}
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
    fun cancel() { OndaStore.dismissQuestions(queryId.value);MobileEngine.cancel(queryId.value) }
    private var searchRevision=0
    fun search(query: String, provider: String, refresh: Boolean=false) {
        if(busy.value)return
        val revision=++searchRevision
        operation("search",OndaStore.config().put("query",query).put("provider",provider).put("refresh_search",refresh)) {
            if(revision==searchRevision) {
                searchResults.value=it.optJSONArray("tracks")?.objects() ?: emptyList()
                status.value=listOf("${searchResults.value.size} resultado(s).",it.stringList("warnings"),it.stringList("suggestions")).filter {text->text.isNotBlank()}.joinToString(" ")
            }
        }
    }
    fun loadCollection(url: String, options: JSONObject, startDownload:Boolean=false) = operation("collection",OndaStore.config(options).put("url",url)) {
        collection.value=it
        if(startDownload)queueCollection(it.optJSONArray("tracks")?.objects() ?: emptyList(),options,it.optString("folder_title",it.optString("title","Playlist")),true)
    }
    fun importCollection(path: String) = operation("import",OndaStore.config().put("path",path).put("extension",path.substringAfterLast('.'))) { collection.value=it }
    fun importLocal(uri: Uri, category: String, dialog: Boolean=false, finished: (java.io.File)->Unit) {
        status.value="Importando arquivo…"
        viewModelScope.launch {
            try {
                val file=withContext(Dispatchers.IO) {OndaStore.importDocument(uri,category)}
                status.value="Arquivo importado"
                finished(file)
            } catch(error: Exception) {val message=error.message ?: "Não foi possível importar o arquivo";if(dialog) showNotice(importNoticeTitle(category),message) else status.value=message}
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
                if(result.has("error")) {showNotice("Ouvir prévia",result.getString("error"));return@launch}
                val headers=result.optJSONObject("headers") ?: JSONObject()
                val properties=headers.keys().asSequence().associateWith {headers.getString(it)}
                val http=DefaultHttpDataSource.Factory().setDefaultRequestProperties(properties)
                val source=DefaultMediaSourceFactory(DefaultDataSource.Factory(getApplication(),http)).createMediaSource(MediaItem.fromUri(result.getString("url")))
                player.setMediaSource(source);player.prepare();player.play()
                previewLimit?.cancel()
                previewLimit=viewModelScope.launch {delay(OndaStore.settings.value.optInt("search_preview",25)*1000L);player.pause()}
                status.value="Prévia da versão selecionada"
            } catch(error: Exception) {showNotice("Ouvir prévia",error.message ?: "Não foi possível ouvir a prévia")}
        }
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
        val options=JSONObject(OndaStore.settings.value.toString())
        viewModelScope.launch {
            val ids=mutableListOf<String>()
            try {
                for(chunk in urls.chunked(100)) {
                    ids+=withContext(Dispatchers.IO) {OndaStore.enqueueBatch {chunk.map {OndaStore.enqueue(it,options=options,extra=JSONObject().put("_immediate",now))}}}
                    status.value="${ids.size} de ${urls.size} itens adicionados à fila";yield()
                }
                if(now && ids.isNotEmpty()) {DownloadService.batch(getApplication(),ids);queueNavigation.value=true}
                status.value="${ids.size} itens adicionados à fila"
            } catch(error:CancellationException) {throw error}
            catch(error:Exception) {showNotice("Adicionar à fila","${ids.size} de ${urls.size} itens adicionados à fila"+"\n"+(error.message ?: "Falha ao adicionar itens. Os itens já adicionados foram preservados."))}
            finally {addingToQueue.value=false}
        }
    }
    fun queueCollection(rows:List<JSONObject>,options:JSONObject,group:String,now:Boolean) {
        if(addingToQueue.value || rows.isEmpty())return
        addingToQueue.value=true
        viewModelScope.launch {
            val ids=mutableListOf<String>()
            try {
                // Bounded transactions publish progress without one refresh per song.
                for(chunk in rows.chunked(100)) {
                    ids+=withContext(Dispatchers.IO) {OndaStore.enqueueBatch {chunk.map {queueTrack(it,options,group,immediate=now)}}}
                    status.value="${ids.size} de ${rows.size} itens adicionados à fila"
                    yield()
                }
                if(now && ids.isNotEmpty()) {DownloadService.batch(getApplication(),ids);queueNavigation.value=true}
                status.value="${ids.size} itens adicionados à fila"
            } catch(error:CancellationException) {throw error}
            catch(error:Exception) {showNotice("Adicionar à fila","${ids.size} de ${rows.size} itens adicionados à fila"+"\n"+(error.message ?: "Falha ao adicionar itens. Os itens já adicionados foram preservados."))}
            finally {addingToQueue.value=false}
        }
    }
    override fun onCleared() { stopPreview();cancel();effectRequests.close(); player.release(); super.onCleared() }
}
