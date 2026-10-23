package br.com.onda.mobile

import android.content.Context
import android.content.Intent
import android.util.AtomicFile
import org.json.JSONArray
import java.io.File
import java.util.UUID

/** Keep selections out of Binder; a small opaque token survives service startup. */
internal object DownloadBatchFiles {
    fun intent(context:Context,ids:List<String>):Intent {
        val token=UUID.randomUUID().toString()
        val directory=File(context.filesDir,"download-requests").apply {mkdirs()}
        val file=AtomicFile(File(directory,"$token.json"))
        val stream=file.startWrite()
        try {stream.write(JSONArray(ids.distinct()).toString().toByteArray(Charsets.UTF_8));file.finishWrite(stream)}
        catch(error:Exception) {file.failWrite(stream);throw error}
        return Intent(context,DownloadService::class.java).putExtra("batch_token",token)
    }
    fun consume(context:Context,token:String):Set<String> {
        require(Regex("[0-9a-f-]{36}").matches(token)) {"Pedido de download inválido."}
        val file=File(File(context.filesDir,"download-requests"),"$token.json")
        val array=JSONArray(file.readText())
        val ids=(0 until array.length()).map {array.getString(it)}.toSet()
        file.delete()
        return ids
    }
    fun discard(context:Context,intent:Intent) {intent.getStringExtra("batch_token")?.let {token->if(Regex("[0-9a-f-]{36}").matches(token))File(File(context.filesDir,"download-requests"),"$token.json").delete()}}
}
