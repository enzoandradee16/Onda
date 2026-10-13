package br.com.onda.mobile

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject
import java.io.File

@Composable fun AdvancedDownloadOptions(settings:JSONObject,put:(String,Any)->Unit) {
    Text("Fila e agendamento",style=MaterialTheme.typography.titleMedium)
    SettingsDivider()
    Select("Downloads simultâneos (1 a 4)",settings.optString("concurrent_downloads","1"),listOf("1","2","3","4")){put("concurrent_downloads",it)}
    SettingsDivider()
    Toggle("Retomar arquivos interrompidos quando possível",settings.optBoolean("resume_downloads",true)){put("resume_downloads",it)}
    SettingsDivider()
    Toggle("Retomar fila ao abrir o ONDA",settings.optBoolean("resume_queue")){put("resume_queue",it)}
    SettingsDivider()
    Toggle("Normalizar volume dos próximos downloads",settings.optBoolean("normalize_volume")){put("normalize_volume",it)}
    SettingsDivider()
    Toggle("Agendar downloads",settings.optBoolean("schedule_enabled")){put("schedule_enabled",it)}
    SettingsDivider()
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(settings.optString("schedule_start","22:00"),{put("schedule_start",it)},label={Text("Começar · HH:MM")},singleLine=true,modifier=Modifier.weight(1f))
        OutlinedTextField(settings.optString("schedule_stop","07:00"),{put("schedule_stop",it)},label={Text("Parar · HH:MM")},singleLine=true,modifier=Modifier.weight(1f))
    }
    if(settings.optBoolean("schedule_enabled")) {
        val valid=runCatching {java.time.LocalTime.parse(settings.optString("schedule_start"))!=java.time.LocalTime.parse(settings.optString("schedule_stop"))}.getOrDefault(false)
        if(!valid)Text("Informe horários diferentes no formato HH:MM.",color=MaterialTheme.colorScheme.error)
    }
    Text("O Android pode atrasar o início para economizar bateria. A fila interrompida fica pendente para retomar.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun PreferenceTransfer(vm:OndaViewModel) {
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) {uri->if(uri!=null) {
        vm.operation("settings_export",JSONObject().put("settings",OndaStore.settings.value),dialog=true){result->
            runCatching {OndaStore.context.contentResolver.openOutputStream(uri)!!.bufferedWriter().use {it.write(result.getJSONObject("payload").toString(2))}}
                .onSuccess {vm.showNotice("Exportar configurações","Configurações exportadas.")}.onFailure {vm.showNotice("Exportar configurações",it.message ?: "Não foi possível salvar.")}
        }
    }}
    val importFile=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) {
        vm.importLocal(uri,"preferences",dialog=true) {file->
            if(file.length()>131072)vm.showNotice("Importar configurações","Arquivo muito grande.") else vm.operation("settings_import",JSONObject().put("path",file.absolutePath),dialog=true){result->
                val updated=JSONObject(OndaStore.settings.value.toString());val changes=result.getJSONObject("settings");changes.keys().forEach {updated.put(it,changes.get(it))};OndaStore.saveSettings(updated);vm.showNotice("Importar configurações","Configurações importadas.");file.delete()
            }
        }
    }}
    SettingsDivider()
    TextButton(onClick={export.launch("ONDA-configuracoes.json")}){Text("Exportar configurações…")}
    SettingsDivider()
    TextButton(onClick={importFile.launch(arrayOf("application/json","text/plain"))}){Text("Importar configurações…")}
    Text("A transferência não inclui contas, cookies nem caminhos de pastas.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun AppUpdateControls(vm:OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var update by remember {mutableStateOf<JSONObject?>(null)}
    SettingsDivider()
    Toggle("Verificar atualizações do ONDA ao abrir",settings.optBoolean("check_updates")){OndaStore.saveSettings(JSONObject(settings.toString()).put("check_updates",it))}
    SettingsDivider()
    OutlinedButton(onClick={vm.operation("app_update",JSONObject().put("version",BuildConfig.VERSION_NAME),dialog=true){update=it;vm.showNotice("Verificar atualização do ONDA",it.optString("message"))}}){Text("Verificar atualização do ONDA")}
    if(update?.optBoolean("available")==true)Button(onClick={
        runCatching {OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(update!!.getString("url"))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.showNotice("Baixar nova versão","Não foi possível abrir o navegador.")}
    }){Text("Baixar nova versão")}
    Text("O download usa a Release oficial. A instalação é confirmada pelo Android e preserva os dados quando o APK é compatível.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun AudioFileEditor(item:HistoryItem,vm:OndaViewModel,close:()->Unit) {
    var source by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf("")}
    var changes by androidx.compose.runtime.saveable.rememberSaveable(stateSaver=androidx.compose.runtime.saveable.Saver<JSONObject,String>(save={it.toString()},restore={JSONObject(it)})) {mutableStateOf(JSONObject())}
    var loaded by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf(false)}
    var editing by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf(true)}
    var overwrite by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf(false)}
    var normalize by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf(false)}
    var lyrics by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf("")}
    var cover by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf("")}
    var cropCandidate by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf("")}
    var originalCover by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf("")}
    var preview by androidx.compose.runtime.saveable.rememberSaveable {mutableStateOf("")}
    val busy by vm.busy.collectAsStateWithLifecycle()
    val pickLyrics=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()){uri->if(uri!=null)vm.importLocal(uri,"lyrics",dialog=false){lyrics=it.absolutePath}}
    val pickCover=rememberImageSourcePicker {uri->vm.importLocal(uri,"cover",dialog=false){if(cover.isNotBlank())File(cover).delete();cover=it.absolutePath}}
    LaunchedEffect(item.uri) {if(!loaded)vm.importLocal(Uri.parse(item.uri),"audio-editor",dialog=false){file->source=file.absolutePath;vm.operation("audio_read",JSONObject().put("source",source),dialog=false){changes=it.getJSONObject("record").apply {if(optString("title")==file.nameWithoutExtension)put("title",item.title.substringBeforeLast('.'))};originalCover=it.optString("cover_preview");loaded=true}}}
    fun config()=OndaStore.config().put("source",source).put("output_name",item.title.substringBeforeLast('.'))
        .put("overwrite_original",overwrite).put("original_uri",item.uri).put("edit_metadata",editing).put("normalize_volume",normalize).put("changes",changes).put("lyrics_path",lyrics).put("cover_path",cover)
    fun finish() {vm.stopPreview();listOf(preview,source,cover,lyrics,cropCandidate).filter {it.isNotBlank()}.forEach {File(it).delete()};close()}
    if(cropCandidate.isNotBlank())CoverCropper(cropCandidate,
        onCancel={cropCandidate=""},
        onApply={cropped->if(cover.isNotBlank())File(cover).delete();cover=cropped;File(cropCandidate).delete();cropCandidate=""})
    Column(Modifier.fillMaxSize().padding(horizontal=16.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
            Text(item.title,modifier=Modifier.weight(1f),maxLines=2,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            Button(enabled=!busy,onClick={finish()},contentPadding=PaddingValues(horizontal=16.dp)){Text("Escolher outro arquivo",maxLines=1,softWrap=false)}
        }
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(16.dp),horizontalAlignment=androidx.compose.ui.Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(8.dp)) {
                    Text("Capa do álbum",style=MaterialTheme.typography.titleMedium)
            val originalBitmap=remember(originalCover) {runCatching {val bytes=android.util.Base64.decode(originalCover,android.util.Base64.DEFAULT);android.graphics.BitmapFactory.decodeByteArray(bytes,0,bytes.size)}.getOrNull()}
            if(cover.isNotBlank() || originalBitmap!=null) coil.compose.AsyncImage(model=if(cover.isNotBlank())File(cover) else originalBitmap,contentDescription="Capa do álbum",modifier=Modifier.size(208.dp))
            else Text("Sem capa",style=MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement=Arrangement.Center) {
                TextButton(onClick={pickCover()},enabled=editing && !busy){Text("Escolher outra capa…")}
                TextButton(onClick={File(cover).delete();cover=""},enabled=cover.isNotBlank() && !busy){Text("Desfazer capa")}
            }
            OutlinedButton(onClick={cropCandidate=cover},enabled=cover.isNotBlank() && editing && !busy){Text("Ajustar capa")}
                }
            }
            Toggle("Editar metadados",editing){editing=it}
            for((key,label) in listOf("title" to "Música","artists" to "Artistas (separados por ;)","album" to "Álbum","genre" to "Gênero","release_date" to "Data")) {
                val text=if(key=="artists")changes.optJSONArray(key)?.let {a->(0 until a.length()).joinToString("; "){a.optString(it)}} ?: "" else changes.optString(key)
                OutlinedTextField(text,{value->changes=JSONObject(changes.toString()).put(key,if(key=="artists")org.json.JSONArray(value.split(';').map {it.trim()}.filter {it.isNotBlank()}) else value)},label={Text(label)},singleLine=true,enabled=editing && !busy,modifier=Modifier.fillMaxWidth())
            }
            TextButton(onClick={pickLyrics.launch(arrayOf("text/plain","application/x-lrc","application/octet-stream"))},enabled=!busy){Text(if(lyrics.isBlank())"Importar letra · TXT ou LRC" else "Letra selecionada")}
            Toggle("Normalizar volume (−16 LUFS)",normalize){normalize=it}
            Row {
                TextButton(onClick={vm.preview(source,20)},enabled=source.isNotBlank() && !busy){Text("Ouvir original")}
                TextButton(onClick={vm.stopPreview();vm.operation("normalize_preview",config(),dialog=false){preview=it.getString("path");vm.preview(preview,20)}},enabled=source.isNotBlank() && !busy){Text("Ouvir normalizado")}
            }
            PlayerControls(vm)
            Toggle("Sobrescrever arquivo original",overwrite){if(!busy)overwrite=it}
            Text(if(overwrite) "O arquivo original será substituído, mantendo o nome e a pasta." else "O arquivo original será preservado. Uma cópia será salva na pasta de destino.",style=MaterialTheme.typography.bodySmall)
            if(busy)LinearProgressIndicator(Modifier.fillMaxWidth())
        Button(enabled=loaded && !busy,onClick={vm.operation("audio_edit",config(),dialog=false){if(overwrite)finish();vm.status.value=if(overwrite) "Arquivo original atualizado." else "Cópia editada salva na pasta de destino."}},modifier=Modifier.fillMaxWidth()){Text(if(overwrite) "Salvar no original" else "Salvar cópia editada")}
        Spacer(Modifier.height(16.dp))
    }
}
