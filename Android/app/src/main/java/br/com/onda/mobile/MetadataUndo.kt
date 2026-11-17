package br.com.onda.mobile

import android.net.Uri
import com.chaquo.python.Python
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import org.json.JSONObject

internal object MetadataUndo {
    val available=MutableStateFlow(false)
    fun refresh(){available.value=File(OndaStore.context.filesDir,"metadata-undo/last.json").isFile}
    fun record(result:JSONObject,target:String) {
        if(result.optString("undo_snapshot").isBlank())return
        Python.getInstance().getModule("metadata_undo").callAttr("register",result.getString("undo_snapshot"),target,null,result.getString("undo_transaction"),result.getString("undo_sha256"))
        refresh()
    }
    fun restore():Int {
        MobileEngine.initialize(OndaStore.context)
        val module=Python.getInstance().getModule("metadata_undo")
        val rows=module.callAttr("pending").asList()
        require(rows.isNotEmpty()) {"Não há edição de metadados para desfazer."}
        var count=0
        try {for(row in rows.reversed()) {
            val target=row.callAttr("__getitem__","target").toString()
            val source=OndaStore.importDocument(Uri.parse(target),"metadata-undo")
            val edited=File.createTempFile("undo-edited-","."+source.extension,source.parentFile)
            try {
                source.copyTo(edited,overwrite=true)
                module.callAttr("restore_file",edited.absolutePath,row.callAttr("__getitem__","snapshot"),row.callAttr("__getitem__","sha256"))
                OndaStore.overwriteAudio(edited,JSONObject().put("original_uri",target).put("source",source.absolutePath))
                module.callAttr("finish",target);count++
            } finally {source.delete();edited.delete()}
        }} finally {refresh()}
        return count
    }
}
