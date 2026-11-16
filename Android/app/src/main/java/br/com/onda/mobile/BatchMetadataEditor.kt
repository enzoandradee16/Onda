package br.com.onda.mobile

import androidx.compose.ui.draw.clip

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

@Composable internal fun BatchMetadataEditor(vm:OndaViewModel,initialSources:List<String>,close:()->Unit) {
    val busy by vm.busy.collectAsStateWithLifecycle()
    val scope=rememberCoroutineScope()
    var sources by rememberSaveable {mutableStateOf(ArrayList(initialSources.distinct()))}
    var selected by rememberSaveable {mutableStateOf(arrayListOf<String>())}
    var fields by rememberSaveable(stateSaver=androidx.compose.runtime.saveable.Saver<Map<String,String>,String>(
        save={JSONObject(it).toString()},restore={raw->val obj=JSONObject(raw);obj.keys().asSequence().associateWith {obj.getString(it)}})) {mutableStateOf(mapOf<String,String>())}
    val pasteAvailable=rememberMetadataPasteAvailable()
    var transferPath by rememberSaveable {mutableStateOf("")}
    var transferCover by rememberSaveable {mutableStateOf("")}
    var recognized by remember {mutableStateOf(JSONObject())}
    var cover by rememberSaveable {mutableStateOf("")}
    var overwrite by rememberSaveable {mutableStateOf(false)}
    var confirm by remember {mutableStateOf(false)}
    var preparing by remember {mutableStateOf(false)}
    var summary by rememberSaveable {mutableStateOf("")}
    val locked=busy || preparing
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()){uris->
        if(uris.isNotEmpty()) {
            uris.forEach {uri->runCatching {OndaStore.context.contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)}
                .onFailure {runCatching {OndaStore.context.contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION)}}}
            sources=ArrayList(uris.map {it.toString()}.distinct())
            recognized=JSONObject();summary=""
        }
    }
    val pickCover=rememberImageSourcePicker {uri->vm.importLocal(uri,"batch-cover",dialog=true){file->if(cover.isNotBlank())File(cover).delete();cover=file.absolutePath}}
    DisposableEffect(Unit) {onDispose {listOf(cover,transferPath,transferCover).filter {it.isNotBlank()}.forEach {File(it).delete()}}}
    fun copyTags() {
        val first=sources.firstOrNull() ?: return
        vm.importLocal(Uri.parse(first),"tag-copy",dialog=false){file->
            val output=MetadataClipboard.newCopyFile()
            val tags=JSONObject()
            selected.forEach {key->val value=fields[key].orEmpty();tags.put(key,if(key=="artists")JSONArray(value.split(';').map {it.trim()}.filter {it.isNotEmpty()}) else value)}
            val request=JSONObject().put("source",file.absolutePath).put("record",tags).put("temporary_source",true)
                .put("clipboard_path",output.absolutePath).put("base_transfer_path",transferPath).put("cover_path",if(cover==transferCover)"" else cover)
            vm.operation("audio_tags_copy",request,dialog=false){result->MetadataClipboard.publish(result.getString("clipboard_path"))}
        }
    }
    fun pasteTags() {
        runCatching {
            val draft=MetadataClipboard.draft()
            vm.operation("audio_tags_paste",JSONObject().put("clipboard_path",draft.absolutePath),dialog=false){result->
                if(result.optBoolean("cancelled"))return@operation
                val tags=result.getJSONObject("record")
                fields=fields+tags.keys().asSequence().associateWith {key->if(key=="artists")tags.getJSONArray(key).let {a->(0 until a.length()).joinToString("; "){a.getString(it)}} else tags.getString(key)}
                selected=ArrayList((selected+tags.keys().asSequence().toList()).distinct())
                if(transferPath.isNotBlank())File(transferPath).delete()
                transferPath=result.getString("tag_transfer_path")
                if(result.optString("cover_path").isNotBlank()) {
                    if(cover.isNotBlank())File(cover).delete()
                    cover=result.getString("cover_path");transferCover=cover
                } else transferCover=""
            }
        }.onFailure {vm.showNotice("Colar tags",uiExceptionMessage(it,"Copie as tags de uma música no ONDA primeiro."))}
    }
    fun recognizeNames() {
        if(locked)return
        preparing=true
        val snapshot=sources.toList()
        scope.launch {
            try {
                val entries=withContext(Dispatchers.IO) {snapshot.map {value->
                    JSONObject().put("identity",value).put("filename",localAudioItem(Uri.parse(value)).title).put("record",localMetadataHint(Uri.parse(value)))
                }}
                vm.operation("audio_name_lookup",JSONObject().put("entries",JSONArray(entries)),dialog=false) nameResult@{result->
                    if(sources.toList()!=snapshot || result.optBoolean("cancelled"))return@nameResult
                    val matches=result.optJSONArray("matches")?.objects().orEmpty()
                    recognized=JSONObject().apply {matches.forEach {put(it.getString("identity"),it)}}
                    selected=arrayListOf()
                    summary="${matches.size}/${sources.size} · "+"Metadados prontos para revisar e salvar."
                    matches.firstOrNull()?.optJSONObject("changes")?.let {tags->
                        fields=tags.keys().asSequence().associateWith {key->if(key=="artists")tags.getJSONArray(key).let {a->(0 until a.length()).joinToString("; "){a.getString(it)}} else tags.getString(key)}
                    }
                    if(matches.isEmpty())vm.showNotice("Identificar pelo nome",result.optJSONArray("errors")?.optJSONObject(0)?.optString("error").orEmpty().ifBlank {"Nenhuma gravação correspondente foi encontrada."})
                }
            } catch(error:Exception) {
                if(error is kotlinx.coroutines.CancellationException)throw error
                vm.showNotice("Identificar pelo nome",uiExceptionMessage(error,"Não foi possível consultar os catálogos. Tente novamente."))
            } finally {preparing=false}
        }
    }
    fun apply() {
        if(locked)return
        preparing=true
        scope.launch {
            val imports=mutableListOf<File>()
            try {
                val entries=withContext(Dispatchers.IO) {
                    sources.filter {selected.isNotEmpty() || cover.isNotBlank() || transferPath.isNotBlank() || recognized.has(it)}.map {value->
                        val item=localAudioItem(Uri.parse(value))
                        val file=OndaStore.importDocument(Uri.parse(value),"batch-audio");imports.add(file)
                        JSONObject().put("source",file.absolutePath).put("original_uri",value).put("output_name",item.title.substringBeforeLast('.',item.title)).apply {recognized.optJSONObject(value)?.let {match->put("changes",match.getJSONObject("changes"));put("cover_url",match.optString("cover_url"))}}
                    }
                }
                val changes=JSONObject()
                selected.forEach {key->val value=fields[key].orEmpty();changes.put(key,if(key=="artists")JSONArray(value.split(';').map {it.trim()}.filter {it.isNotEmpty()}) else value)}
                val config=OndaStore.config().put("sources",JSONArray(entries)).put("changes",changes).put("cover_path",if(transferCover.isNotBlank() && cover==transferCover)"" else cover).put("tag_transfer_path",transferPath).put("tag_transfer_cover",transferCover.isNotBlank() && cover==transferCover).put("overwrite_original",overwrite)
                vm.operation("audio_batch_edit",config,dialog=false){result->
                    summary=result.optString("message")
                    val errors=result.optJSONArray("errors")?.objects().orEmpty()
                    if(errors.isNotEmpty())vm.showNotice("Editar metadados em lote",errors.take(10).joinToString("\n"){it.optString("name")+": "+translateError(it.optString("error"))})
                }
            } catch(error:Exception) {
                imports.forEach {it.delete()}
                if(error is kotlinx.coroutines.CancellationException)throw error
                vm.showNotice("Editar metadados em lote",uiExceptionMessage(error,"Não foi possível abrir o arquivo."))
            } finally {preparing=false}
        }
    }
    if(confirm)AlertDialog(onDismissRequest={confirm=false},title={UiText("Editar metadados em lote")},text={UiText("Os arquivos originais selecionados serão substituídos. Continuar?")},confirmButton={TextButton(onClick={confirm=false;apply()}){UiText("Continuar")}},dismissButton={TextButton(onClick={confirm=false}){UiText("Cancelar")}})
    Dialog(onDismissRequest={if(!locked)close()}) {
        Surface(shape=MaterialTheme.shapes.large) {
            Column(Modifier.fillMaxWidth().fillMaxHeight(.9f).padding(LayoutSpacing.inset)) {
                ToolHeading("Editar metadados em lote") {
                    var tagsMenu by remember {mutableStateOf(false)}
                    Box {
                        IconButton(onClick={tagsMenu=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                        DropdownMenu(tagsMenu,{tagsMenu=false}) {
                            DropdownMenuItem(text={UiText("Identificar pelo nome")},enabled=!locked && sources.isNotEmpty(),onClick={tagsMenu=false;recognizeNames()})
                            DropdownMenuItem(text={UiText("Copiar tags")},enabled=!locked && sources.isNotEmpty(),onClick={tagsMenu=false;copyTags()})
                            DropdownMenuItem(text={UiText("Colar tags")},enabled=!locked && pasteAvailable,onClick={tagsMenu=false;pasteTags()})
                        }
                    }
                }
                Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                    UiText("${sources.size} arquivos selecionados")
                    OutlinedButton(onClick={picker.launch(arrayOf("audio/*","application/ogg"))},enabled=!locked){UiText("Escolher vários arquivos de áudio")}
                    UiText("Marque somente os campos que deseja alterar. Campos desmarcados serão preservados.",style=MaterialTheme.typography.bodySmall)
                    for((key,label) in listOf("artists" to "Artistas (separados por ;)","album" to "Álbum","genre" to "Gênero","release_date" to "Data","track_number" to "Faixa","disc_number" to "Disco","title" to "Música","isrc" to "ISRC","album_artist" to "Artista do álbum","composer" to "Compositor")) {
                        Row(verticalAlignment=Alignment.CenterVertically) {
                            Checkbox(checked=key in selected,onCheckedChange={checked->selected=ArrayList(if(checked)selected+key else selected-key)},enabled=!locked,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel).a11yLabel(label))
                            OutlinedTextField(fields[key].orEmpty(),{fields=fields+(key to it)},label={UiText(label)},enabled=key in selected && !locked,singleLine=true,modifier=Modifier.weight(1f).testTag("batch-field-$key"))
                        }
                    }
                    OutlinedButton(onClick={pickCover()},enabled=!locked){UiText("Aplicar uma capa aos arquivos")}
                    if(cover.isNotBlank()) {
                        coil.compose.AsyncImage(model=File(cover),contentDescription=translateUi("Capa do álbum",LocalUiLanguage.current),modifier=Modifier.size(120.dp).clip(androidx.compose.foundation.shape.RoundedCornerShape(12.dp)))
                        TextButton(onClick={File(cover).delete();cover=""},enabled=!locked){UiText("Remover capa selecionada")}
                    }
                    Row(verticalAlignment=Alignment.CenterVertically) {Checkbox(overwrite,{overwrite=it},enabled=!locked,modifier=Modifier.padding(end=LayoutSpacing.checkboxLabel).a11yLabel("Sobrescrever arquivo original"));UiText("Sobrescrever arquivo original")}
                    UiText(if(overwrite)"Os arquivos originais selecionados serão substituídos." else "O arquivo original será preservado. Uma cópia será salva na pasta de destino.",style=MaterialTheme.typography.bodySmall)
                    if(preparing && !busy)LinearProgressIndicator(Modifier.fillMaxWidth())
                    if(summary.isNotBlank())UiText(summary)
                }
                Button(onClick={if(overwrite)confirm=true else apply()},enabled=!locked && sources.size in 1..500 && (selected.isNotEmpty() || cover.isNotBlank() || transferPath.isNotBlank() || recognized.length()>0),modifier=Modifier.fillMaxWidth().testTag("batch-apply")){UiText("Aplicar aos arquivos selecionados")}
                TextButton(onClick=close,enabled=!locked,modifier=Modifier.align(Alignment.End)){UiText("Fechar")}
            }
        }
    }
}
