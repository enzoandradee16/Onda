package br.com.onda.mobile

import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable fun MetadataPage(vm:OndaViewModel,requestedUri:String?=null,onRequestConsumed:()->Unit={}) {
    var batchSources by rememberSaveable {mutableStateOf(arrayListOf<String>())}
    var batchOpen by rememberSaveable {mutableStateOf(false)}
    if(batchOpen)BatchMetadataEditor(vm,batchSources){batchOpen=false}
    var selectedUri by rememberSaveable {mutableStateOf<String?>(null)}
    var item by remember {mutableStateOf<HistoryItem?>(null)}
    LaunchedEffect(requestedUri) {if(requestedUri!=null){selectedUri=requestedUri;item=null;onRequestConsumed()}}
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->
        if(uri!=null) {
            val resolver=OndaStore.context.contentResolver
            runCatching {resolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)}
                .onFailure {runCatching {resolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION)}}
            selectedUri=uri.toString()
        }
    }
    LaunchedEffect(selectedUri) {
        val value=selectedUri ?: return@LaunchedEffect
        try {
            item=withContext(Dispatchers.IO) {localAudioItem(Uri.parse(value))}
        } catch(cancelled:CancellationException) {throw cancelled}
        catch(error:Exception) {vm.showNotice("Escolher arquivo de áudio",error.message ?: "Não foi possível abrir o arquivo.");selectedUri=null}
    }
    val audio=item
    if(audio!=null) {
        key(audio.uri) {AudioFileEditor(audio,vm){item=null;selectedUri=null}}
    } else Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
        ToolHeading("Editar metadados")
        ToolEmpty("tag","Sua música, seus detalhes","Escolha um áudio para editar informações, capa e letra.")
        Button(onClick={picker.launch(arrayOf("audio/*","application/ogg"))},modifier=Modifier.fillMaxWidth()) {UiText("Escolher arquivo de áudio")}
        OutlinedButton(onClick={batchSources=arrayListOf();batchOpen=true},modifier=Modifier.fillMaxWidth()){UiText("Editar metadados em lote")}
        UiText("MP3, M4A, FLAC, WAV, OGG e OPUS. Edite música, artistas, álbum, gênero, data, capa e letra.",style=MaterialTheme.typography.bodySmall)
        UiText("Salve uma cópia ou ative Sobrescrever arquivo original. Para substituir o original, a pasta precisa permitir a edição.",style=MaterialTheme.typography.bodySmall)
    }
}

internal fun localAudioItem(uri:Uri):HistoryItem {
    val resolver=OndaStore.context.contentResolver
    var name=uri.lastPathSegment ?: "Áudio"
    var size=0L
    resolver.query(uri,arrayOf(OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE),null,null,null)?.use {cursor->
        if(cursor.moveToFirst()) {
            cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME).takeIf {it>=0 && !cursor.isNull(it)}?.let {name=cursor.getString(it)}
            cursor.getColumnIndex(OpenableColumns.SIZE).takeIf {it>=0 && !cursor.isNull(it)}?.let {size=cursor.getLong(it)}
        }
    }
    return HistoryItem(-1,name,uri.toString(),name.substringAfterLast('.',"").lowercase(),size)
}
