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
        }
    }
    val pickCover=rememberImageSourcePicker {uri->vm.importLocal(uri,"batch-cover",dialog=true){file->if(cover.isNotBlank())File(cover).delete();cover=file.absolutePath}}
    DisposableEffect(Unit) {onDispose {if(cover.isNotBlank())File(cover).delete()}}
    fun apply() {
        if(locked)return
        preparing=true
        scope.launch {
            val imports=mutableListOf<File>()
            try {
                val entries=withContext(Dispatchers.IO) {
                    sources.map {value->
                        val item=localAudioItem(Uri.parse(value))
                        val file=OndaStore.importDocument(Uri.parse(value),"batch-audio");imports.add(file)
                        JSONObject().put("source",file.absolutePath).put("original_uri",value).put("output_name",item.title.substringBeforeLast('.',item.title))
                    }
                }
                val changes=JSONObject()
                selected.forEach {key->val value=fields[key].orEmpty();changes.put(key,if(key=="artists")JSONArray(value.split(';').map {it.trim()}.filter {it.isNotEmpty()}) else value)}
                val config=OndaStore.config().put("sources",JSONArray(entries)).put("changes",changes).put("cover_path",cover).put("overwrite_original",overwrite)
                vm.operation("audio_batch_edit",config,dialog=false){result->
                    summary=result.optString("message")
                    val errors=result.optJSONArray("errors")?.objects().orEmpty()
                    if(errors.isNotEmpty())vm.showNotice("Editar metadados em lote",errors.take(10).joinToString("\n"){it.optString("name")+": "+translateUi(it.optString("error"))})
                }
            } catch(error:Exception) {
                imports.forEach {it.delete()}
                if(error is kotlinx.coroutines.CancellationException)throw error
                vm.showNotice("Editar metadados em lote",error.message ?: "Não foi possível abrir o arquivo.")
            } finally {preparing=false}
        }
    }
    if(confirm)AlertDialog(onDismissRequest={confirm=false},title={UiText("Editar metadados em lote")},text={UiText("Os arquivos originais selecionados serão substituídos. Continuar?")},confirmButton={TextButton(onClick={confirm=false;apply()}){UiText("Continuar")}},dismissButton={TextButton(onClick={confirm=false}){UiText("Cancelar")}})
    Dialog(onDismissRequest={if(!locked)close()}) {
        Surface(shape=MaterialTheme.shapes.large) {
            Column(Modifier.fillMaxWidth().fillMaxHeight(.9f).padding(LayoutSpacing.inset)) {
                UiText("Editar metadados em lote",style=MaterialTheme.typography.titleLarge)
                Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                    UiText("${sources.size} arquivos selecionados")
                    OutlinedButton(onClick={picker.launch(arrayOf("audio/*","application/ogg"))},enabled=!locked){UiText("Escolher vários arquivos de áudio")}
                    UiText("Marque somente os campos que deseja alterar. Campos desmarcados serão preservados.",style=MaterialTheme.typography.bodySmall)
                    for((key,label) in listOf("artists" to "Artistas (separados por ;)","album" to "Álbum","genre" to "Gênero","release_date" to "Data","track_number" to "Faixa","disc_number" to "Disco")) {
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
                Button(onClick={if(overwrite)confirm=true else apply()},enabled=!locked && sources.size in 1..500 && (selected.isNotEmpty() || cover.isNotBlank()),modifier=Modifier.fillMaxWidth().testTag("batch-apply")){UiText("Aplicar aos arquivos selecionados")}
                TextButton(onClick=close,enabled=!locked,modifier=Modifier.align(Alignment.End)){UiText("Fechar")}
            }
        }
    }
}
