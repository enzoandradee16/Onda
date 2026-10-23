package br.com.onda.mobile

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.MediaStore
import java.io.File

private const val EXTERNAL_DOCUMENTS="com.android.externalstorage.documents"

fun externalFolderUri(relative: String, volume: String="primary"): Uri {
    val parts=relative.trim('/').split('/').filter {it.isNotEmpty()}
    require(parts.none {it==".." || it=="."}) {"Pasta inválida"}
    return DocumentsContract.buildDocumentUri(EXTERNAL_DOCUMENTS,"$volume:${parts.joinToString("/")}")
}

// Resolve the historical file, rather than the currently selected output folder.
fun historyFolderUri(context: Context, value: Uri): Uri {
    if(value.authority=="media" && Build.VERSION.SDK_INT>=29) {
        val relative=context.contentResolver.query(value,arrayOf(MediaStore.MediaColumns.RELATIVE_PATH),null,null,null)?.use {
            if(it.moveToFirst()) it.getString(0) else null
        } ?: error("O arquivo foi movido ou removido. Não foi possível localizar sua pasta.")
        val mediaVolume=MediaStore.getVolumeName(value)
        val volume=if(mediaVolume in setOf("external","external_primary")) "primary" else {
            context.getSystemService(android.os.storage.StorageManager::class.java).storageVolumes
                .firstOrNull {it.uuid.equals(mediaVolume,ignoreCase=true)}?.uuid ?: mediaVolume
        }
        return externalFolderUri(relative,volume)
    }
    if(DocumentsContract.isDocumentUri(context,value)) {
        val id=DocumentsContract.getDocumentId(value)
        val parent=if(value.authority==EXTERNAL_DOCUMENTS && id.contains(':')) {
            val relative=id.substringAfter(':')
            require(relative.isNotEmpty()) {"Não foi possível localizar a pasta deste arquivo."}
            id.substringBefore(':')+":"+relative.substringBeforeLast('/',"")
        } else {
            val path=runCatching {DocumentsContract.findDocumentPath(context.contentResolver,value)?.path}.getOrNull()
            path?.dropLast(1)?.lastOrNull() ?: error("Este provedor não informa a pasta do arquivo.")
        }
        return if(DocumentsContract.isTreeUri(value)) DocumentsContract.buildDocumentUriUsingTree(value,parent)
            else DocumentsContract.buildDocumentUri(value.authority!!,parent)
    }
    if(value.authority=="${context.packageName}.files" && value.pathSegments.firstOrNull()=="exports") {
        val base=context.getExternalFilesDir(null) ?: error("Armazenamento indisponível")
        val relative=value.pathSegments.drop(1).dropLast(1).joinToString("/")
        val folder=File(base,relative).canonicalFile
        require(folder.toPath().startsWith(base.canonicalFile.toPath())) {"Pasta inválida"}
        return externalFolderUri(folder.relativeTo(Environment.getExternalStorageDirectory().canonicalFile).invariantSeparatorsPath)
    }
    error("Não foi possível localizar a pasta deste arquivo.")
}

fun historyFolderPicker(folder: Uri)=Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
    addCategory(Intent.CATEGORY_OPENABLE)
    type="*/*"
    putExtra(DocumentsContract.EXTRA_INITIAL_URI,folder)
    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}

fun openHistoryFolder(context: Context, folder: Uri) {
    val intent=Intent(Intent.ACTION_VIEW).setDataAndType(folder,DocumentsContract.Document.MIME_TYPE_DIR)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    try {context.startActivity(intent)}
    catch(error: ActivityNotFoundException) {context.startActivity(historyFolderPicker(folder))}
    catch(error: SecurityException) {context.startActivity(historyFolderPicker(folder))}
}
