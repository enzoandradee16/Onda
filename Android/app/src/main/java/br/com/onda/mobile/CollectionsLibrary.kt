package br.com.onda.mobile

import android.util.AtomicFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** User-saved collection snapshots, separate from download and playback queues. */
internal object CollectionsLibrary {
    private val lock=Mutex()
    private fun file()=AtomicFile(File(OndaStore.context.filesDir,"saved-collections.json"))
    private fun readLocked():List<JSONObject> {
        return runCatching {
            val rows=JSONArray(file().openRead().bufferedReader().use {it.readText()})
            (0 until rows.length()).map {rows.getJSONObject(it)}
        }.getOrDefault(emptyList())
    }
    private fun writeLocked(rows:List<JSONObject>) {
        val target=file();val stream=target.startWrite()
        try {stream.write(JSONArray(rows).toString().toByteArray());target.finishWrite(stream)}
        catch(error:Exception){target.failWrite(stream);throw error}
    }
    suspend fun read():List<JSONObject> = withContext(Dispatchers.IO){lock.withLock {readLocked()}}
    suspend fun write(rows:List<JSONObject>)=withContext(Dispatchers.IO){lock.withLock {writeLocked(rows)}}
    suspend fun save(row:JSONObject):List<JSONObject> = withContext(Dispatchers.IO){lock.withLock {
        val rows=listOf(JSONObject(row.toString()))+readLocked().filter {identity(it)!=identity(row)}
        writeLocked(rows);rows
    }}
    suspend fun remove(row:JSONObject):List<JSONObject> = withContext(Dispatchers.IO){lock.withLock {
        val rows=readLocked().filter {identity(it)!=identity(row)}
        writeLocked(rows);rows
    }}
    fun identity(row:JSONObject)=row.optString("_collection_url").ifBlank {row.optString("title")+"|"+row.optString("subtitle")}
}
