package br.com.onda.mobile

import android.content.Context
import android.content.Intent
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.net.Uri
import android.provider.OpenableColumns
import android.provider.MediaStore
import android.content.ContentValues
import android.os.Build
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.flow.MutableStateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

data class DownloadItem(val id: String, val title: String, val config: JSONObject, val state: String = "Pendente", val progress: Float = 0f, val message: String = "", val activity:String="")
data class HistoryItem(val id: Long, val title: String, val uri: String, val mode: String, val size: Long, val metadataPlatform:String="",val source:String="",val completedAt:Long=0L)
data class Question(val identity: String, val event: JSONObject, val callback: ((JSONObject)->Unit)?=null)

private class OndaDatabase(context: Context) : SQLiteOpenHelper(context,"onda.sqlite3",null,1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE queue (id TEXT PRIMARY KEY, title TEXT NOT NULL, config TEXT NOT NULL, state TEXT NOT NULL)")
        db.execSQL("CREATE TABLE history (id INTEGER PRIMARY KEY, title TEXT NOT NULL, uri TEXT NOT NULL, mode TEXT NOT NULL, size INTEGER NOT NULL)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
}

object OndaStore {
    lateinit var context: Context
    private lateinit var database: OndaDatabase
    val items = MutableStateFlow<List<DownloadItem>>(emptyList())
    val history = MutableStateFlow<List<HistoryItem>>(emptyList())
    val settings = MutableStateFlow(JSONObject())
    val question = MutableStateFlow<Question?>(null)
    val messages = MutableStateFlow<List<String>>(emptyList())
    val running = MutableStateFlow(false)
    val queuePause=MutableStateFlow("")
    val failureSummary=MutableStateFlow<List<String>?>(null)
    internal val queueTiming=QueueTiming()
    val sharedLink = MutableStateFlow("")
    val active = MutableStateFlow("")
    val selectAll = kotlinx.coroutines.flow.MutableSharedFlow<Unit>(extraBufferCapacity=1)
    private val questions = java.util.ArrayDeque<Question>()
    private val cancelledDuplicateBatches=linkedSetOf<String>()
    private var batchDepth=0
    private val batchItems=mutableListOf<DownloadItem>()
    private val batchDuplicateKeys=hashSetOf<QueueDuplicateKey>()
    private var batchPosition=0L
    private val batchQuestions=mutableListOf<()->Unit>()
    @Synchronized fun <T> enqueueBatch(action: ()->T):T {
        val outer=batchDepth==0
        if(outer){
            batchItems.clear();batchQuestions.clear();batchDuplicateKeys.clear()
            items.value.filter {it.state!="Erro"}.mapNotNullTo(batchDuplicateKeys){queueDuplicateKey(it.config)}
            database.readableDatabase.rawQuery("SELECT COALESCE(MAX(position),0) FROM queue_order",null).use {it.moveToFirst();batchPosition=it.getLong(0)}
        }
        var committed=false
        database.writableDatabase.beginTransaction();batchDepth++
        try {val result=action();database.writableDatabase.setTransactionSuccessful();committed=true;return result}
        finally {
            batchDepth--;database.writableDatabase.endTransaction()
            if(outer){val prompts=batchQuestions.toList();batchItems.clear();batchQuestions.clear();batchDuplicateKeys.clear();refreshQueue();if(committed)prompts.forEach {it()}}
        }
    }
    fun initialize(value: Context) {
        context = value.applicationContext
        database = OndaDatabase(context)
        settings.value = defaults().apply {
            val text = context.getSharedPreferences("preferences",0).getString("settings",null)
            if (text != null) {val saved=JSONObject(text);saved.keys().forEach {put(it,saved.get(it))}}
        }
        context.getSharedPreferences("preferences",0).getString("display",null)?.let { text ->
            runCatching { JSONObject(text) }.getOrNull()?.let { saved ->
                displayFields.forEach { key -> if(saved.has(key)) settings.value.put(key,saved.get(key)) }
            }
        }
        normalizeAppearance(settings.value)
        database.writableDatabase.execSQL("UPDATE queue SET state='Pendente' WHERE state IN ('Baixando','Aguardando escolha')")
        database.writableDatabase.execSQL("CREATE TABLE IF NOT EXISTS queue_order (id TEXT PRIMARY KEY, position INTEGER NOT NULL)")
        database.writableDatabase.execSQL("INSERT OR IGNORE INTO queue_order SELECT id,rowid FROM queue")
        database.writableDatabase.execSQL("CREATE TABLE IF NOT EXISTS history_sources (history_id INTEGER PRIMARY KEY, source TEXT NOT NULL, mode TEXT NOT NULL)")
        database.writableDatabase.execSQL("CREATE TABLE IF NOT EXISTS history_metadata_platform (history_id INTEGER PRIMARY KEY, platform TEXT NOT NULL)")
        database.writableDatabase.execSQL("CREATE TABLE IF NOT EXISTS history_dates (history_id INTEGER PRIMARY KEY, completed_at INTEGER NOT NULL)")
        database.writableDatabase.execSQL("CREATE INDEX IF NOT EXISTS history_source_index ON history_sources(source,mode)")
        database.writableDatabase.execSQL("UPDATE queue SET state='Erro' WHERE state='Duplicata'")
        refresh()
    }
    fun defaults() = JSONObject().put("wifi_only",false).put("wifi_loss","Pausar downloads").put("notification_controls",true).put("finish_action","Notificação").put("clipboard_links",true).put("auto_select_media",true).put("simple_download_ui",false).put("social_best_quality",true).put("language","pt-BR").put("mode","mp3").put("audio_quality","320 kbps").put("height",1080).put("fps",JSONObject.NULL)
        .put("queue_actions_at_top",true).put("queue_view","Completa").put("queue_card_size","Grande").put("catalog_card_size","Grande").put("pure_black_separators",false).put("history_card_size","Grande").put("history_view","Compacto").put("playlist_limit",2000).put("link_playlist",false).put("auto_metadata",false).put("auto_match",false).put("confirm_version",false).put("review_metadata",false)
        .put("detect_duplicates",true).put("filename_template","Original").put("duplicate_policy","ask").put("organization","Pasta de destino").put("interface_font",DEFAULT_INTERFACE_FONT).put("interface_font_size","100%").put("interface_spacing","Padrão").put("theme","Seguir o sistema").put("accent","Verde-Água")
        .put("concurrent_downloads","1").put("resume_downloads",true).put("resume_queue",false).put("normalize_volume",false)
        .put("schedule_enabled",false).put("schedule_start","22:00").put("schedule_stop","07:00").put("check_updates",true).put("notice_duration","Após 3 segundos").put("notice_animation",true)
        .put("playback_tab_order","Efeitos primeiro").put("jukebox_transition_seconds",2).put("jukebox_gradual_transition",true).put("jukebox_equalizer",JSONObject()).put("jukebox_background",false).put("synced_lyrics",false).put("search_preview",25).put("effects_preview",25).put("keep_preview",false).put("remember",true)
        .put("image_format","Original").put("image_size","Original").put("image_width",0).put("image_height",0).put("keep_ratio",true)
        .put("bottom_bar_order",JSONArray(bottomBarDefaults))
        .put("hidden_tabs",JSONArray())
        .put("tab_order",JSONArray(listOf("Pesquisar","Links e fila","Fila","Imagens","Conversor de vídeos","Playlists / Álbuns","Histórico","Efeitos","Metadados")))
        .put("output_uri", "").put("cookies_file", "").put("youtube_cookies_file", "").put("spotify_client_id", "")
    fun normalizeAppearance(value:JSONObject) {
        value.put("jukebox_transition_seconds",value.optInt("jukebox_transition_seconds",2).coerceIn(1,10))
        if(value.optString("playback_tab_order") !in listOf("Efeitos primeiro","Jukebox infinito primeiro"))value.put("playback_tab_order","Efeitos primeiro")
        if(value.optString("finish_action") !in finishActions)value.put("finish_action","Notificação")
        if(value.optString("wifi_loss") !in wifiLossActions)value.put("wifi_loss","Pausar downloads")
        if(value.optString("image_size")=="Original" && (value.optInt("image_width")>0 || value.optInt("image_height")>0))value.put("image_size","Personalizado")
        value.put("interface_spacing",normalizedSpacing(value.optString("interface_spacing","Padrão")))
        if(value.optString("queue_view") !in listOf("Compacto","Completa"))value.put("queue_view","Completa")
        if(value.optString("queue_card_size") !in listOf("Pequeno","Médio","Grande"))value.put("queue_card_size","Grande")
        value.put("language",normalizedLanguage(value.optString("language","pt-BR")))
        value.put("interface_font",normalizeInterfaceFont(value.optString("interface_font",DEFAULT_INTERFACE_FONT)))
        val available=defaults().getJSONArray("tab_order").let {a->(0 until a.length()).map {a.getString(it)}}
        val saved=value.optJSONArray("tab_order")
        val ordered=if(saved==null) emptyList() else (0 until saved.length()).map {saved.optString(it).let {name->if(name=="Conversor") "Conversor de vídeos" else name}}.filter {it in available}.distinct()
        val complete=(ordered+available.filter {it !in ordered && it!="Fila" && it!="Conversor de vídeos"}).toMutableList()
        if("Fila" !in complete)complete.add(complete.indexOf("Links e fila")+1,"Fila")
        if("Conversor de vídeos" !in complete)complete.add(complete.indexOf("Imagens")+1,"Conversor de vídeos")
        value.put("tab_order",JSONArray(complete))
        value.put("hidden_tabs",JSONArray(hiddenTabs(value)))
        value.put("bottom_bar_order",JSONArray(bottomBarOrder(value)))
        val aliases=mapOf("Menta" to "Verde-Água","Verde-água" to "Verde-Água","Lima" to "Verde-limão","Lavanda" to "Lilás","Pêssego" to "Coral","Prata" to "Cinza")
        aliases[value.optString("accent")]?.let {value.put("accent",it)}
        if(value.optString("theme")=="Sistema") value.put("theme","Seguir o sistema")
    }
    private val displayFields=listOf("queue_view","queue_card_size","history_view","history_card_size","catalog_card_size")
    @Synchronized fun saveSettings(value: JSONObject) {
        normalizeAppearance(value)
        val scheduleChanged=listOf("schedule_enabled","schedule_start","schedule_stop","wifi_only").any {settings.value.opt(it)!=value.opt(it)}
        val controlsChanged=settings.value.optBoolean("notification_controls",true)!=value.optBoolean("notification_controls",true)
        settings.value = JSONObject(value.toString())
        if(controlsChanged && DownloadRuntime.running.get())refreshDownloadNotification(context)
        if(scheduleChanged)DownloadSchedule.configure(context,value)
        val persisted = if (value.optBoolean("remember",true)) value else defaults().put("remember",false).put("language",value.optString("language","pt-BR"))
        context.getSharedPreferences("preferences",0).edit().putString("settings",persisted.toString()).putString("display",JSONObject().apply { displayFields.forEach { key -> put(key,value.optString(key,defaults().optString(key))) } }.toString()).apply()
        LauncherIcons.sync(context,value)
    }
    fun config(options: JSONObject = settings.value, includeSecrets: Boolean = true): JSONObject = JSONObject(options.toString()).apply {
        remove("confirm_version")
        if(optString("mode")=="m4a" && optString("audio_quality") !in listOf("256 kbps","192 kbps","128 kbps","96 kbps")) put("audio_quality","256 kbps")
        put("folder", File(context.getExternalFilesDir(null),"Onda Downloads").absolutePath)
        put("ffmpeg", "android-native")
        applyVersionSelection(this, settings.value)
        put("playlist",options.optBoolean("link_playlist",false))
        if(includeSecrets) put("spotify_client_secret", SecureVault.get("spotify-api") ?: "")
        if(optString("mode")=="photos") put("image_options",JSONObject().put("format", options.optString("image_format","Original"))
            .put("width",options.optInt("image_width")).put("height",options.optInt("image_height"))
            .put("keep_ratio",options.optBoolean("keep_ratio",true)))
    }
    fun executionConfig(stored:JSONObject):JSONObject=JSONObject(stored.toString()).apply {
        val live=settings.value
        listOf("cookies_file","youtube_cookies_file","youtube_user_agent").forEach {key->put(key,live.optString(key))}
    }
    @Synchronized fun refresh() {refreshQueue();refreshHistory()}
    @Synchronized private fun refreshQueue() {
        val previous=items.value.associateBy {it.id}
        val queue = mutableListOf<DownloadItem>()
        database.readableDatabase.rawQuery("SELECT q.id,q.title,q.config,q.state FROM queue q LEFT JOIN queue_order o ON q.id=o.id ORDER BY COALESCE(o.position,q.rowid),q.rowid",null).use { cursor ->
            while(cursor.moveToNext()) {
                val id=cursor.getString(0)
                val old=previous[id]
                queue += DownloadItem(id,cursor.getString(1),JSONObject(cursor.getString(2)),cursor.getString(3),old?.progress ?: 0f,old?.message ?: "",old?.activity ?: "")
            }
        }
        items.value = queue
        if(queue.isEmpty())queueTiming.reset()
    }
    @Synchronized fun comparisonHistory():JSONArray {
        val rows=JSONArray()
        database.readableDatabase.rawQuery("SELECT h.uri,h.title,COALESCE(s.source,'') FROM history h LEFT JOIN history_sources s ON s.history_id=h.id ORDER BY h.id DESC",null).use {cursor->
            while(cursor.moveToNext())rows.put(JSONObject().put("path",cursor.getString(0)).put("title",cursor.getString(1)).put("source_url",cursor.getString(2)))
        }
        return rows
    }

    @Synchronized private fun refreshHistory() {
        val past = mutableListOf<HistoryItem>()
        database.readableDatabase.rawQuery("SELECT h.id,h.title,h.uri,h.mode,h.size,COALESCE(m.platform,''),COALESCE(s.source,''),COALESCE(d.completed_at,0) FROM history h LEFT JOIN history_dates d ON d.history_id=h.id LEFT JOIN history_metadata_platform m ON m.history_id=h.id LEFT JOIN history_sources s ON s.history_id=h.id ORDER BY h.id DESC LIMIT 3000",null).use { cursor ->
            while(cursor.moveToNext()) past += HistoryItem(cursor.getLong(0),cursor.getString(1),cursor.getString(2),cursor.getString(3),cursor.getLong(4),cursor.getString(5),cursor.getString(6),cursor.getLong(7))
        }
        history.value = past
    }
    @Synchronized fun enqueue(url: String, title: String = url, options: JSONObject = settings.value, extra: JSONObject? = null): String {
        val id = UUID.randomUUID().toString()
        var config = config(options,includeSecrets=false).put("url",url)
        extra?.keys()?.forEach { config.put(it,extra.get(it)) }
        config.put("auto_select_media",settings.value.optBoolean("auto_select_media",true))
        config.put("simple_download_ui",settings.value.optBoolean("simple_download_ui",false)).put("social_best_quality",settings.value.optBoolean("social_best_quality",true))
        config.put("simple_download_mode",settings.value.optString("mode","mp3"))
        config=effectiveDownloadOptions(config)
        val duplicateKey=queueDuplicateKey(config)
        val queuedDuplicate=if(batchDepth>0) duplicateKey!=null && duplicateKey in batchDuplicateKeys else items.value.any {it.state!="Erro" && duplicateJob(it.config,config)}
        val duplicate=config.optBoolean("detect_duplicates",true) && config.optString("_operation").isBlank() && (
            queuedDuplicate || (!config.optBoolean("playlist") && config.optString("playlist_title").isBlank() && database.readableDatabase.rawQuery("SELECT 1 FROM history_sources WHERE source=? AND lower(mode)=lower(?) LIMIT 1",arrayOf(jobSource(config),config.optString("mode"))).use {it.moveToFirst()}))
        if(duplicate && config.optString("_duplicate_batch",id) in cancelledDuplicateBatches)return ""
        val state=if(duplicate) "Duplicata" else "Pendente"
        // Secrets are injected at execution and never stored in the queue database.
        config.remove("spotify_client_secret")
        database.writableDatabase.execSQL("INSERT INTO queue VALUES(?,?,?,?)",arrayOf(id,title,config.toString(),state))
        if(batchDepth>0) {
            database.writableDatabase.execSQL("INSERT INTO queue_order VALUES(?,?)",arrayOf(id,++batchPosition))
            if(duplicateKey!=null)batchDuplicateKeys.add(duplicateKey)
        } else database.writableDatabase.execSQL("INSERT INTO queue_order VALUES(?,(SELECT COALESCE(MAX(position),0)+1 FROM queue_order))",arrayOf(id))
        val added=DownloadItem(id,title,config,state)
        if(batchDepth==0)items.value=items.value+added else batchItems.add(added)
        val prompt:()->Unit = {ask("duplicate-$id",JSONObject().put("type","choose_queue_duplicate").put("path",title)) {answer->
            synchronized(this) {
                val start=duplicateStarts.remove(id)
                if(items.value.none {it.id==id})return@synchronized
                if(!answer.optBoolean("cancel") && answer.optBoolean("add")) {
                    update(id,"Pendente")
                    if(start)DownloadService.start(context,id)
                } else remove(setOf(id))
            }
        }}
        if(duplicate){if(batchDepth>0)batchQuestions.add(prompt) else prompt()}
        return id
    }
    private val duplicateStarts=mutableSetOf<String>()
    @Synchronized fun deferDuplicateStart(id:String):Boolean {
        if(items.value.any {it.id==id && it.state=="Duplicata"}) {duplicateStarts.add(id);return true}
        return false
    }
    @Synchronized fun update(id: String, state: String, progress: Float? = null, message: String? = null, activity:String?=null) {
        val previous = items.value.firstOrNull { it.id == id } ?: return
        if(previous.state==state && (progress==null || progress==previous.progress) && (message==null || message==previous.message) && (activity==null || activity==previous.activity)) return
        if(previous.state != state) database.writableDatabase.execSQL("UPDATE queue SET state=? WHERE id=?",arrayOf(state,id))
        if(previous.state!="Concluído" && state=="Concluído")queueTiming.recordCompletion()
        items.value = items.value.map { if(it.id==id) it.copy(state=state,progress=progress ?: it.progress,message=message ?: it.message,activity=if(state in listOf("Baixando","Aguardando escolha"))activity ?: it.activity else "") else it }
    }
    @Synchronized fun rename(id: String, title: String) {
        if(title.isBlank() || items.value.firstOrNull {it.id==id}?.title==title) return
        database.writableDatabase.execSQL("UPDATE queue SET title=? WHERE id=?",arrayOf(title,id))
        items.value=items.value.map {if(it.id==id) it.copy(title=title) else it}
    }
    @Synchronized fun renamePendingLink(id:String,url:String,title:String,info:JSONObject?=null):Boolean {
        val item=items.value.firstOrNull {it.id==id} ?: return false
        if(item.state !in setOf("Pendente","Duplicata") || item.title!=url || item.config.optString("url")!=url || title.isBlank() || title==url)return false
        val config=JSONObject(item.config.toString())
        if(info!=null)config.put("queue_info",JSONObject(info.toString()))
        database.writableDatabase.execSQL("UPDATE queue SET title=?,config=? WHERE id=?",arrayOf(title,config.toString(),id))
        items.value=items.value.map {if(it.id==id)it.copy(title=title,config=config) else it}
        return true
    }
    @Synchronized fun updateQueueInformation(id:String,url:String,info:JSONObject) {
        val item=items.value.firstOrNull {it.id==id && it.config.optString("url")==url} ?: return
        val merged=JSONObject(info.toString())
        item.config.optJSONObject("queue_info")?.let {known->known.keys().forEach {key->if(!known.isNull(key) && known.optString(key).isNotBlank() && known.optString(key)!="[]")merged.put(key,known.get(key))}}
        val config=JSONObject(item.config.toString()).put("queue_info",merged)
        database.writableDatabase.execSQL("UPDATE queue SET config=? WHERE id=?",arrayOf(config.toString(),id))
        items.value=items.value.map {if(it.id==id)it.copy(config=config) else it}
    }
    fun collectionOptions(): JSONObject {
        val text=context.getSharedPreferences("preferences",0).getString("collection_options",null)
        return if(text!=null) JSONObject(text) else JSONObject(settings.value.toString())
    }
    fun saveCollectionOptions(value: JSONObject) {
        val edit=context.getSharedPreferences("preferences",0).edit()
        if(settings.value.optBoolean("remember",true)) edit.putString("collection_options",value.toString()) else edit.remove("collection_options")
        edit.apply()
    }
    fun resetCollectionOptions() {
        context.getSharedPreferences("preferences",0).edit().remove("collection_options").apply()
    }
    @Synchronized fun remove(ids: Set<String>) {
        val removable=ids-active.value-DownloadRuntime.ids
        if(removable.isEmpty()) return
        val db=database.writableDatabase
        db.beginTransaction()
        try {
            removable.forEach {db.execSQL("DELETE FROM queue WHERE id=?",arrayOf(it));db.execSQL("DELETE FROM queue_order WHERE id=?",arrayOf(it))}
            db.setTransactionSuccessful()
        } finally {db.endTransaction()}
        items.value=items.value.filterNot {it.id in removable}
        if(items.value.isEmpty())queueTiming.reset()
    }
    fun retry(ids: Set<String>) { ids.filter { it!=active.value && it !in DownloadRuntime.ids }.forEach { update(it,"Pendente",0f,"") } }
    @Synchronized fun useFailureMetadata(id:String,record:JSONObject):Boolean {
        val item=items.value.firstOrNull {it.id==id && it.state in setOf("Erro","Pendente")} ?: return false
        if(id in DownloadRuntime.ids || id==active.value)return false
        val config=repairedFailureConfig(item.config,record) ?: return false
        val title=(record.stringList("artists")+" - "+record.optString("title")).trim(' ','-')
        database.writableDatabase.execSQL("UPDATE queue SET config=?, title=?, state=? WHERE id=?",arrayOf(config.toString(),title,"Pendente",id))
        items.value=items.value.map {if(it.id==id)it.copy(title=title,config=config,state="Pendente",progress=0f,message="Metadados escolhidos") else it}
        return true
    }
    @Synchronized fun retryWithVersionChoice(id:String) {
        val item=items.value.firstOrNull {it.id==id && it.state=="Erro"} ?: return
        if(id==active.value || id in DownloadRuntime.ids)return
        val config=JSONObject(item.config.toString()).put("_manual_version",true)
        database.writableDatabase.execSQL("UPDATE queue SET config=? WHERE id=?",arrayOf(config.toString(),id))
        items.value=items.value.map {if(it.id==id)it.copy(config=config) else it}
        retry(setOf(id))
        DownloadService.start(context,only=id)
    }
    @Synchronized fun reorderPending(ids:List<String>) {
        val next=pendingOrder(items.value,ids) ?: return
        val db=database.writableDatabase;db.beginTransaction()
        try {next.forEachIndexed {position,item->db.execSQL("INSERT OR REPLACE INTO queue_order VALUES(?,?)",arrayOf<Any>(item.id,position))};db.setTransactionSuccessful()}
        finally {db.endTransaction()}
        items.value=next
    }
    @Synchronized fun sortPending(order:String) {
        val original=mutableListOf<String>()
        database.readableDatabase.rawQuery("SELECT id FROM queue ORDER BY rowid",null).use {cursor->while(cursor.moveToNext())original+=cursor.getString(0)}
        reorderPending(orderedPending(items.value,order,original))
    }
    @Synchronized fun movePendingBefore(id:String,target:String) {
        val pending=items.value.filter {it.state=="Pendente" && it.id !in DownloadRuntime.ids}.map {it.id}.toMutableList()
        val from=pending.indexOf(id);val to=pending.indexOf(target)
        if(from<0 || to<0 || from==to)return
        pending.removeAt(from);pending.add(to,id);reorderPending(pending)
    }
    @Synchronized fun queueEstimate(id:String,size:Long) {
        if(size<=0)return
        val item=items.value.firstOrNull {it.id==id} ?: return
        val config=JSONObject(item.config.toString()).put("_queue_estimate",size)
        database.writableDatabase.execSQL("UPDATE queue SET config=? WHERE id=?",arrayOf(config.toString(),id))
        items.value=items.value.map {if(it.id==id)it.copy(config=config) else it}
    }
    fun confirmQueueSpace(ids:Set<String>?,proceed:()->Unit):Boolean {
        val report=queueSpace(items.value.filter {it.state=="Pendente" && (ids==null || it.id in ids)})
        if(!report.low)return true
        ask("queue-space-"+UUID.randomUUID(),JSONObject().put("type","choose_queue_space").put("message",report.text(settings.value.optString("language","pt-BR")))) {reply->if(!reply.optBoolean("cancel"))proceed()}
        return false
    }
    @Synchronized fun move(id:String,direction:Int) {
        val pending=items.value.filter {it.state=="Pendente" && it.id !in DownloadRuntime.ids}.map {it.id}
        val index=pending.indexOf(id)
        if(index<0)return
        val target=if(direction==0)0 else (index+direction).coerceIn(0,pending.lastIndex)
        movePendingBefore(id,pending[target])
    }
    @Synchronized fun log(message: String) { messages.value = (messages.value + message).takeLast(120) }
    @Synchronized fun ask(identity: String, event: JSONObject, callback: ((JSONObject)->Unit)?=null) {
        val value = Question(identity,event,callback)
        if(question.value==null) question.value = value else questions.add(value)
    }
    @Synchronized fun cancelAllDuplicates() {
        val duplicates=items.value.filter {it.state=="Duplicata"}
        duplicates.forEach {cancelledDuplicateBatches.add(it.config.optString("_duplicate_batch",it.id))}
        while(cancelledDuplicateBatches.size>64)cancelledDuplicateBatches.remove(cancelledDuplicateBatches.first())
        val ids=duplicates.map {it.id}.toSet()
        duplicateStarts.removeAll(ids)
        questions.removeIf {it.event.optString("type")=="choose_queue_duplicate"}
        remove(ids)
        if(question.value?.event?.optString("type")=="choose_queue_duplicate")
            question.value=if(questions.isEmpty()) null else questions.removeFirst()
    }
    @Synchronized fun answer(value: JSONObject) {
        question.value?.let { if(it.callback!=null) it.callback.invoke(value) else MobileEngine.reply(it.identity,value) }
        question.value = if(questions.isEmpty()) null else questions.removeFirst()
    }
    @Synchronized fun dismissQuestions(identity: String) {
        questions.filter {it.identity==identity}.forEach {it.callback?.invoke(JSONObject().put("cancel",true))}
        questions.removeIf { it.identity==identity }
        if(question.value?.identity==identity) {
            question.value?.callback?.invoke(JSONObject().put("cancel",true))
            question.value = if(questions.isEmpty()) null else questions.removeFirst()
        }
    }
    private fun duplicateChoice(path: String, config: JSONObject): String {
        val policy=config.optString("duplicate_policy","keep")
        if(policy!="ask") return policy
        val future=java.util.concurrent.CompletableFuture<JSONObject>()
        val identity=config.optString("_identity",active.value.ifBlank {"publish-${UUID.randomUUID()}"})
        ask(identity,JSONObject().put("type","choose_duplicate").put("path",path)) {future.complete(it)}
        val result=future.get()
        require(!result.optBoolean("cancel")) {"Exportação cancelada"}
        return result.getString("choice")
    }
    fun importDocument(uri: Uri, category: String): File {
        val name = context.contentResolver.query(uri,arrayOf(OpenableColumns.DISPLAY_NAME),null,null,null)?.use { if(it.moveToFirst()) it.getString(0) else null } ?: "arquivo"
        val safe = name.replace(Regex("[^\\p{L}\\p{N}._ -]"),"_")
        val file = File(context.filesDir,"imports/$category-${UUID.randomUUID()}-$safe")
        file.parentFile?.mkdirs()
        context.contentResolver.openInputStream(uri)!!.use { source -> file.outputStream().use { source.copyTo(it) } }
        return file
    }
    private fun destination(path: File, config: JSONObject): Uri {
        val tree = config.optString("output_uri")
        if(tree.isEmpty()) {
            if(Build.VERSION.SDK_INT<29) return androidx.core.content.FileProvider.getUriForFile(context,"${context.packageName}.files",path)
            val base=File(config.getString("folder"))
            val relative=path.parentFile!!.relativeTo(base).invariantSeparatorsPath.takeIf {it!="."} ?: ""
            val values=ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME,path.name)
                put(MediaStore.Downloads.MIME_TYPE,mimeFor(path.name))
                put(MediaStore.Downloads.RELATIVE_PATH,"Download/ONDA/"+relative)
                put(MediaStore.Downloads.IS_PENDING,1)
            }
            val existing=context.contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI,arrayOf(MediaStore.Downloads._ID),
                "${MediaStore.Downloads.DISPLAY_NAME}=? AND ${MediaStore.Downloads.RELATIVE_PATH}=?",arrayOf(path.name,"Download/ONDA/"+relative.trimEnd('/')+if(relative.isBlank()) "" else "/"),null)?.use {
                if(it.moveToFirst()) android.content.ContentUris.withAppendedId(MediaStore.Downloads.EXTERNAL_CONTENT_URI,it.getLong(0)) else null
            }
            if(existing!=null) {
                when(duplicateChoice(path.name,config)) {
                    "skip"->return existing
                    "replace"->{replacePublished(existing,path);return existing}
                }
            }
            val uri=context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,values) ?: error("Não foi possível criar o arquivo em Downloads")
            try {
                context.contentResolver.openOutputStream(uri)!!.use { out->path.inputStream().use {it.copyTo(out)} }
                context.contentResolver.update(uri,ContentValues().apply {put(MediaStore.Downloads.IS_PENDING,0)},null,null)
            } catch(error: Exception) {context.contentResolver.delete(uri,null,null);throw error}
            return uri
        }
        var directory = DocumentFile.fromTreeUri(context,Uri.parse(tree)) ?: error("Pasta de destino indisponível")
        val base = File(config.getString("folder"))
        val relative = path.relativeTo(base).invariantSeparatorsPath.split('/')
        for(part in relative.dropLast(1)) {
            require(part!=".." && part!=".")
            directory = directory.findFile(part)?.takeIf { it.isDirectory } ?: directory.createDirectory(part) ?: error("Não foi possível criar a pasta")
        }
        val mime = mimeFor(path.name)
        val existing = directory.findFile(path.name)
        // The shared engine resolves duplicates in the retained staging/output tree.
        // A newly chosen external folder defaults to preserving existing files.
        val choice=if(existing!=null) duplicateChoice(path.name,config) else "keep"
        if(existing!=null && choice=="skip") return existing.uri
        val document = if(existing!=null && choice=="replace") {
            replacePublished(existing.uri,path)
            return existing.uri
        } else directory.createFile(mime,path.name)
        requireNotNull(document) { "Não foi possível salvar na pasta escolhida" }
        try {
            context.contentResolver.openOutputStream(document.uri,"wt")!!.use { target -> path.inputStream().use { it.copyTo(target) } }
        } catch(error: Exception) { document.delete(); throw error }
        return document.uri
    }
    private fun replacePublished(uri:Uri, replacement:File) {
        val original=importDocument(uri,"replace-backup")
        try {replaceAudioOriginal(context,uri,original,replacement);invalidateHistoryDetails()}
        finally {original.delete()}
    }
    fun publicationConfig(config: JSONObject, event: JSONObject)=JSONObject(config.toString()).apply {
        if(event.has("duplicate_choice")) put("duplicate_policy",event.getString("duplicate_choice"))
    }
    fun publish(path: String, config: JSONObject, mode: String): Uri {
        val file = File(path)
        val uri = destination(file,config)
        val completedAt=System.currentTimeMillis()
        val historyId=database.writableDatabase.insertOrThrow("history",null,ContentValues().apply {
            put("title",file.name);put("uri",uri.toString());put("mode",mode);put("size",file.length())
        })
        database.writableDatabase.execSQL("INSERT INTO history_dates(history_id,completed_at) VALUES(?,?)",arrayOf<Any>(historyId,completedAt))
        if(config.optString("url").isNotBlank() && config.optString("_operation").isBlank()) {
            database.writableDatabase.execSQL("INSERT INTO history_sources(history_id,source,mode) VALUES(?,?,?)",arrayOf<Any>(historyId,jobSource(config),mode))
        }
        val metadata=config.optJSONObject("catalog_record") ?: config.optJSONObject("queue_info")
        val platform=metadata?.cleanString("platform").orEmpty()
        if(platform.isNotBlank())database.writableDatabase.execSQL("INSERT OR REPLACE INTO history_metadata_platform(history_id,platform) VALUES(?,?)",arrayOf<Any>(historyId,platform))
        synchronized(this) {
            history.value=insertHistoryRow(history.value,HistoryItem(historyId,file.name,uri.toString(),mode,file.length(),platform,
                if(config.optString("url").isNotBlank() && config.optString("_operation").isBlank())jobSource(config) else "",completedAt))
        }
        // MediaStore/SAF now owns the exported copy. Keep custom inputs and the
        // Android 8/9 FileProvider source, which still backs the published URI.
        val staging=File(context.getExternalFilesDir(null),"Onda Downloads").canonicalFile.toPath()
        if(uri.authority!="${context.packageName}.files" && file.canonicalFile.toPath().startsWith(staging)) {
            file.delete()
        }
        return uri
    }
    fun overwriteAudio(edited: File, config: JSONObject) {
        val uri=Uri.parse(config.getString("original_uri"))
        replaceAudioOriginal(context,uri,File(config.getString("source")),edited)
        invalidateHistoryDetails()
        database.writableDatabase.execSQL("UPDATE history SET size=? WHERE uri=?",arrayOf<Any>(edited.length(),uri.toString()))
        synchronized(this) {refreshHistory()}
    }
    fun open(uri: String, mode: String = "") {
        val value=Uri.parse(uri)
        context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(value,if(mode.isEmpty()) "*/*" else mimeFor("file.$mode"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION))
    }
    fun share(uri: String, title: String) {
        val intent = Intent(Intent.ACTION_SEND).setType(mimeFor(title)).putExtra(Intent.EXTRA_STREAM,Uri.parse(uri)).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        context.startActivity(Intent.createChooser(intent,"Compartilhar").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
    @Synchronized fun removeHistory(id: Long) { database.writableDatabase.delete("history_dates","history_id=?",arrayOf(id.toString())); database.writableDatabase.delete("history_metadata_platform","history_id=?",arrayOf(id.toString())); database.writableDatabase.delete("history_sources","history_id=?",arrayOf(id.toString())); database.writableDatabase.delete("history","id=?",arrayOf(id.toString())); refreshHistory() }
    @Synchronized fun clearHistory() { database.writableDatabase.execSQL("DELETE FROM history_dates"); database.writableDatabase.execSQL("DELETE FROM history_metadata_platform"); database.writableDatabase.execSQL("DELETE FROM history_sources"); database.writableDatabase.execSQL("DELETE FROM history"); refreshHistory() }
    fun mimeFor(name: String): String = when(name.substringAfterLast('.').lowercase()) {
        "mp3"->"audio/mpeg"; "m4a"->"audio/mp4"; "flac"->"audio/flac"; "wav"->"audio/wav"
        "mov"->"video/quicktime"; "mp4"->"video/mp4"; "mkv"->"video/x-matroska"; "webm"->"video/webm"
        "jpg","jpeg"->"image/jpeg"; "png"->"image/png"; "webp"->"image/webp"; "svg"->"image/svg+xml"
        else->"application/octet-stream"
    }
}
