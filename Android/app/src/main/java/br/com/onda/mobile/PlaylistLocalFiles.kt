package br.com.onda.mobile

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import org.json.JSONArray
import org.json.JSONObject

internal fun playlistInventory(context:Context,tree:Uri,history:JSONArray,check:()->Unit):JSONArray {
    val root=DocumentFile.fromTreeUri(context,tree)
    require(root!=null && root.isDirectory && root.canRead()) {"Escolha uma pasta de músicas acessível."}
    val files=linkedMapOf<String,JSONObject>()
    for(index in 0 until history.length()) {
        check()
        val row=history.getJSONObject(index);val uri=Uri.parse(row.getString("path"))
        val exists=try {context.contentResolver.openAssetFileDescriptor(uri,"r")?.use {it.declaredLength!=0L} ?: false}
            catch(_:java.io.FileNotFoundException){false}
            catch(_:Exception){row.put("uncertain",true);true}
        if(exists)files.putIfAbsent(uri.toString(),row)
    }
    val pending=java.util.ArrayDeque<DocumentFile>();pending.add(root)
    val visited=mutableSetOf<String>()
    val extensions=setOf("mp3","m4a","flac","wav","ogg","opus","aac","mp4","mkv","webm","mov")
    while(pending.isNotEmpty()) {
        check()
        val folder=pending.removeFirst()
        if(!visited.add(folder.uri.toString()))continue
        require(folder.canRead()) {"Escolha uma pasta de músicas acessível."}
        for(file in folder.listFiles()) {
            check()
            if(file.isDirectory) {if(file.name !in setOf(".onda-work",".git"))pending.add(file);continue}
            val name=file.name.orEmpty()
            if(!file.isFile || name.substringAfterLast('.',"").lowercase() !in extensions)continue
            val key=file.uri.toString()
            if(key in files)continue
            val record=JSONObject().put("path",key).put("filename",name).put("title",name.substringBeforeLast('.'))
            val retriever=MediaMetadataRetriever()
            try {
                retriever.setDataSource(context,file.uri)
                retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_TITLE)?.let {record.put("title",it)}
                retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_ARTIST)?.let {record.put("artists",JSONArray().put(it))}
                retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_ALBUM)?.let {record.put("album",it)}
                retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toDoubleOrNull()?.let {record.put("duration",it/1000)}
            } catch(_:Exception) {record.put("uncertain",true)}
            finally {retriever.release()}
            files[key]=record
        }
    }
    return JSONArray(files.values.toList())
}

internal fun collectionSyncSummary(report:JSONObject):String {
    val counts=report.getJSONObject("counts")
    var text=translateUi("Presentes: {present} · Ausentes: {missing} · Revisar: {review} · Na fila: {queued}")
    for(key in listOf("present","missing","review","queued"))text=text.replace("{$key}",counts.optInt(key).toString())
    if(report.optBoolean("has_previous"))text+=" · "+translateUi("Novas na coleção: {count}").replace("{count}",report.optInt("new_count").toString())
    return text
}
internal fun collectionSyncState(state:String):String=when(state) {
    "present"->"Presente";"missing"->"Ausente";"queued"->"Na fila";else->"Revisar"
}
