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

data class DownloadItem(val id: String, val title: String, val config: JSONObject, val state: String = "Pendente", val progress: Float = 0f, val message: String = "")
data class HistoryItem(val id: Long, val title: String, val uri: String, val mode: String, val size: Long)
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
    val sharedLink = MutableStateFlow("")
    val active = MutableStateFlow("")
    val selectAll = kotlinx.coroutines.flow.MutableSharedFlow<Unit>(extraBufferCapacity=1)
    private val questions = java.util.ArrayDeque<Question>()
    private var batchDepth=0
    @Synchronized fun <T> enqueueBatch(action: ()->T):T {
        database.writableDatabase.beginTransaction();batchDepth++
        try {val result=action();database.writableDatabase.setTransactionSuccessful();return result}
        finally {batchDepth--;database.writableDatabase.endTransaction();refresh()}
    }
    fun initialize(value: Context) {
        context = value.applicationContext
        database = OndaDatabase(context)
        settings.value = defaults().apply {
            val text = context.getSharedPreferences("preferences",0).getString("settings",null)
            if (text != null) JSONObject(text).keys().forEach { put(it,JSONObject(text).get(it)) }
        }
        normalizeAppearance(settings.value)
        database.writableDatabase.execSQL("UPDATE queue SET state='Pendente' WHERE state IN ('Baixando','Aguardando escolha')")
        refresh()
    }
    fun defaults() = JSONObject().put("mode","mp3").put("audio_quality","320 kbps").put("height",1080).put("fps",JSONObject.NULL)
        .put("playlist_limit",2000).put("link_playlist",false).put("auto_match",false).put("confirm_version",false).put("review_metadata",false)
        .put("duplicate_policy","ask").put("organization","Pasta de destino").put("interface_font",DEFAULT_INTERFACE_FONT).put("theme","Seguir o sistema").put("accent","Verde-Água")
        .put("search_preview",25).put("effects_preview",25).put("keep_preview",false).put("remember",true)
        .put("image_format","Original").put("image_width",0).put("image_height",0).put("keep_ratio",true)
        .put("tab_order",JSONArray(listOf("Pesquisar","Links e fila","Imagens","Playlists / Álbuns","Histórico","Efeitos")))
        .put("output_uri", "").put("cookies_file", "").put("youtube_cookies_file", "").put("spotify_client_id", "")
    fun normalizeAppearance(value:JSONObject) {
        val aliases=mapOf("Menta" to "Verde-Água","Verde-água" to "Verde-Água","Lima" to "Verde-limão","Lavanda" to "Lilás","Pêssego" to "Coral","Prata" to "Cinza")
        aliases[value.optString("accent")]?.let {value.put("accent",it)}
        if(value.optString("theme")=="Sistema") value.put("theme","Seguir o sistema")
    }
    @Synchronized fun saveSettings(value: JSONObject) {
        normalizeAppearance(value)
        settings.value = JSONObject(value.toString())
        val persisted = if (value.optBoolean("remember",true)) value else defaults().put("remember",false)
        context.getSharedPreferences("preferences",0).edit().putString("settings",persisted.toString()).apply()
    }
    fun config(options: JSONObject = settings.value): JSONObject = JSONObject(options.toString()).apply {
        if(optString("mode")=="m4a" && optString("audio_quality") !in listOf("256 kbps","192 kbps","128 kbps","96 kbps")) put("audio_quality","256 kbps")
        put("folder", File(context.getExternalFilesDir(null),"Onda Downloads").absolutePath)
        put("ffmpeg", "android-native")
        put("playlist",options.optBoolean("link_playlist",false))
        put("spotify_client_secret", SecureVault.get("spotify-api") ?: "")
        if(optString("mode")=="photos") put("image_options",JSONObject().put("format", options.optString("image_format","Original"))
            .put("width",options.optInt("image_width")).put("height",options.optInt("image_height"))
            .put("keep_ratio",options.optBoolean("keep_ratio",true)))
    }
    @Synchronized fun refresh() {
        val queue = mutableListOf<DownloadItem>()
        database.readableDatabase.rawQuery("SELECT id,title,config,state FROM queue ORDER BY rowid",null).use { cursor ->
            while(cursor.moveToNext()) queue += DownloadItem(cursor.getString(0),cursor.getString(1),JSONObject(cursor.getString(2)),cursor.getString(3))
        }
        items.value = queue
        val past = mutableListOf<HistoryItem>()
        database.readableDatabase.rawQuery("SELECT id,title,uri,mode,size FROM history ORDER BY id DESC LIMIT 3000",null).use { cursor ->
            while(cursor.moveToNext()) past += HistoryItem(cursor.getLong(0),cursor.getString(1),cursor.getString(2),cursor.getString(3),cursor.getLong(4))
        }
        history.value = past
    }
    @Synchronized fun enqueue(url: String, title: String = url, options: JSONObject = settings.value, extra: JSONObject? = null): String {
        val id = UUID.randomUUID().toString()
        val config = config(options).put("url",url)
        extra?.keys()?.forEach { config.put(it,extra.get(it)) }
        // Secrets are injected at execution and never stored in the queue database.
        config.remove("spotify_client_secret")
        database.writableDatabase.execSQL("INSERT INTO queue VALUES(?,?,?,?)",arrayOf(id,title,config.toString(),"Pendente"))
        if(batchDepth==0) refresh()
        return id
    }
    @Synchronized fun update(id: String, state: String, progress: Float? = null, message: String? = null) {
        val previous = items.value.firstOrNull { it.id == id } ?: return
        if(previous.state != state) database.writableDatabase.execSQL("UPDATE queue SET state=? WHERE id=?",arrayOf(state,id))
        items.value = items.value.map { if(it.id==id) it.copy(state=state,progress=progress ?: it.progress,message=message ?: it.message) else it }
    }
    @Synchronized fun rename(id: String, title: String) {
        if(title.isBlank()) return
        database.writableDatabase.execSQL("UPDATE queue SET title=? WHERE id=?",arrayOf(title,id))
        items.value=items.value.map {if(it.id==id) it.copy(title=title) else it}
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
        ids.filter { it!=active.value }.forEach { database.writableDatabase.execSQL("DELETE FROM queue WHERE id=?",arrayOf(it)) }
        refresh()
    }
    fun retry(ids: Set<String>) { ids.filter { it!=active.value }.forEach { update(it,"Pendente",0f,"") } }
    @Synchronized fun log(message: String) { messages.value = (messages.value + message).takeLast(120) }
    @Synchronized fun ask(identity: String, event: JSONObject, callback: ((JSONObject)->Unit)?=null) {
        val value = Question(identity,event,callback)
        if(question.value==null) question.value = value else questions.add(value)
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
                    "replace"->context.contentResolver.delete(existing,null,null)
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
            require(existing.delete()) { "Não foi possível substituir o arquivo" }
            directory.createFile(mime,path.name)
        } else directory.createFile(mime,path.name)
        requireNotNull(document) { "Não foi possível salvar na pasta escolhida" }
        try {
            context.contentResolver.openOutputStream(document.uri,"wt")!!.use { target -> path.inputStream().use { it.copyTo(target) } }
        } catch(error: Exception) { document.delete(); throw error }
        return document.uri
    }
    fun publicationConfig(config: JSONObject, event: JSONObject)=JSONObject(config.toString()).apply {
        if(event.has("duplicate_choice")) put("duplicate_policy",event.getString("duplicate_choice"))
    }
    fun publish(path: String, config: JSONObject, mode: String): Uri {
        val file = File(path)
        val uri = destination(file,config)
        database.writableDatabase.execSQL("INSERT INTO history(title,uri,mode,size) VALUES(?,?,?,?)",arrayOf(file.name,uri.toString(),mode,file.length()))
        refresh()
        return uri
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
    fun removeHistory(id: Long) { database.writableDatabase.delete("history","id=?",arrayOf(id.toString())); refresh() }
    fun clearHistory() { database.writableDatabase.execSQL("DELETE FROM history"); refresh() }
    fun mimeFor(name: String): String = when(name.substringAfterLast('.').lowercase()) {
        "mp3"->"audio/mpeg"; "m4a"->"audio/mp4"; "flac"->"audio/flac"; "wav"->"audio/wav"
        "mp4"->"video/mp4"; "mkv"->"video/x-matroska"; "webm"->"video/webm"
        "jpg","jpeg"->"image/jpeg"; "png"->"image/png"; "webp"->"image/webp"; "svg"->"image/svg+xml"
        else->"application/octet-stream"
    }
}
