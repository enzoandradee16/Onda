package br.com.onda.mobile

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Same versioned payload as metadata_clipboard.py; never copies file paths. */
internal object MetadataClipboard {
    const val MIME = "application/vnd.onda.tags+json"
    private const val MAX_FILE = 24L * 1024 * 1024
    private fun directory() = java.io.File(OndaStore.context.cacheDir, "metadata-tags").apply { mkdirs() }
    fun newCopyFile(): java.io.File = java.io.File.createTempFile("clipboard-", ".json", directory())
    fun publish(path: String) {
        val file = java.io.File(path).canonicalFile
        require(file.parentFile == directory().canonicalFile && file.length() in 1..MAX_FILE)
        val uri = androidx.core.content.FileProvider.getUriForFile(
            OndaStore.context,
            OndaStore.context.packageName + ".files",
            file
        )
        val description = android.content.ClipDescription("ONDA tags", arrayOf(MIME)).apply {
            extras = android.os.PersistableBundle().apply { putString("onda_tags_file", file.name) }
        }
        val manager = OndaStore.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        manager.setPrimaryClip(ClipData(description, ClipData.Item(uri)))
        directory().listFiles()?.filter {
            it.name.startsWith("clipboard-") && it.extension == "json" &&
                it.canonicalFile != file
        }?.forEach { it.delete() }
    }
    fun available(): Boolean {
        val manager = OndaStore.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val description = manager.primaryClipDescription ?: return false
        if (!description.hasMimeType(MIME)) return false
        val name = description.extras?.getString("onda_tags_file") ?: return false
        if (!Regex("clipboard-[A-Za-z0-9_-]+\\.json").matches(name)) return false
        return java.io.File(directory(), name).let { it.isFile && it.length() in 1..MAX_FILE }
    }
    fun draft(): java.io.File {
        require(available()) { "Copie as tags de uma música no ONDA primeiro." }
        val manager = OndaStore.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val uri = manager.primaryClip?.getItemAt(0)?.uri ?: error("Copie as tags de uma música no ONDA primeiro.")
        require(uri.authority == OndaStore.context.packageName + ".files")
        val name = manager.primaryClipDescription!!.extras!!.getString("onda_tags_file")!!
        return java.io.File.createTempFile("paste-", ".json", directory()).also { file ->
            java.io.File(directory(), name).copyTo(file, overwrite = true)
        }
    }
    private val keys =
        setOf("title", "artists", "album", "genre", "release_date", "track_number", "disc_number", "isrc", "album_artist", "composer", "comment")
    private const val LIMIT = 256 * 1024
    private fun validate(tags: JSONObject): JSONObject {
        require(
            tags.length() > 0 && tags.keys().asSequence().all {
                it in keys
            }
        ) { "Copie as tags de uma música no ONDA primeiro." }
        tags.keys().forEach { key ->
            val value = tags.get(key)
            val valid = if (key ==
                "artists"
            ) value is JSONArray && value.length() <= 128 &&
                (0 until value.length()).all { value.get(it) is String && value.getString(it).length <= 4096 }
            else value is String && value.length <= 4096
            require(valid) { "Campo de metadados inválido." }
        }
        return JSONObject(tags.toString())
    }
    internal fun encode(record: JSONObject): String {
        val tags = JSONObject()
        record.keys().forEach { if (it in keys) tags.put(it, record.get(it)) }
        return JSONObject().put("format", "onda.tags").put("version", 1).put("tags", validate(tags)).toString().also {
            require(it.length <= LIMIT) { "As tags excedem o limite de tamanho." }
        }
    }
    internal fun decode(raw: String): JSONObject {
        try {
            require(raw.length <= LIMIT)
            val payload = JSONObject(raw)
            require(payload.optString("format") == "onda.tags" && payload.get("version") == 1)
            return validate(payload.getJSONObject("tags"))
        } catch (_: Exception) {
            throw IllegalArgumentException("Copie as tags de uma música no ONDA primeiro.")
        }
    }
    fun copy(record: JSONObject) {
        val manager = OndaStore.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        manager.setPrimaryClip(ClipData.newPlainText("ONDA tags", encode(record)))
    }
    fun paste(): JSONObject {
        val manager = OndaStore.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = manager.primaryClip
        return decode(if (clip != null && clip.itemCount > 0) clip.getItemAt(0).text?.toString().orEmpty() else "")
    }
}

@androidx.compose.runtime.Composable
internal fun rememberMetadataPasteAvailable(): Boolean {
    val state = androidx.compose.runtime.remember {
        androidx.compose.runtime.mutableStateOf(MetadataClipboard.available())
    }
    val lifecycle = androidx.lifecycle.compose.LocalLifecycleOwner.current.lifecycle
    androidx.compose.runtime.DisposableEffect(lifecycle) {
        val manager = OndaStore.context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val listener = ClipboardManager.OnPrimaryClipChangedListener { state.value = MetadataClipboard.available() }
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event ==
                androidx.lifecycle.Lifecycle.Event.ON_RESUME
            ) state.value = MetadataClipboard.available()
        }
        manager.addPrimaryClipChangedListener(listener)
        lifecycle.addObserver(observer)
        onDispose {
            manager.removePrimaryClipChangedListener(listener)
            lifecycle.removeObserver(observer)
        }
    }
    return state.value
}
