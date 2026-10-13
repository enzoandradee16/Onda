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
    Select("Downloads simultâneos (1 a 4)",settings.optString("concurrent_downloads","1"),listOf("1","2","3","4")){put("concurrent_downloads",it)}
    Toggle("Retomar arquivos interrompidos quando possível",settings.optBoolean("resume_downloads",true)){put("resume_downloads",it)}
    Toggle("Retomar fila ao abrir o ONDA",settings.optBoolean("resume_queue")){put("resume_queue",it)}
    Toggle("Normalizar volume dos próximos downloads",settings.optBoolean("normalize_volume")){put("normalize_volume",it)}
    Toggle("Agendar downloads",settings.optBoolean("schedule_enabled")){put("schedule_enabled",it)}
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
                .onSuccess {vm.dialogNotice.value="Configurações exportadas."}.onFailure {vm.dialogNotice.value=it.message ?: "Não foi possível salvar."}
        }
    }}
    val importFile=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) {
        vm.importLocal(uri,"preferences",dialog=true) {file->
            if(file.length()>131072)vm.dialogNotice.value="Arquivo muito grande." else vm.operation("settings_import",JSONObject().put("path",file.absolutePath),dialog=true){result->
                val updated=JSONObject(OndaStore.settings.value.toString());val changes=result.getJSONObject("settings");changes.keys().forEach {updated.put(it,changes.get(it))};OndaStore.saveSettings(updated);vm.dialogNotice.value="Configurações importadas.";file.delete()
            }
        }
    }}
    TextButton(onClick={export.launch("ONDA-configuracoes.json")}){Text("Exportar configurações…")}
    TextButton(onClick={importFile.launch(arrayOf("application/json","text/plain"))}){Text("Importar configurações…")}
    Text("A transferência não inclui contas, cookies nem caminhos de pastas.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun AppUpdateControls(vm:OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var update by remember {mutableStateOf<JSONObject?>(null)}
    Toggle("Verificar atualizações do ONDA ao abrir",settings.optBoolean("check_updates")){OndaStore.saveSettings(JSONObject(settings.toString()).put("check_updates",it))}
    OutlinedButton(onClick={vm.operation("app_update",JSONObject().put("version",BuildConfig.VERSION_NAME),dialog=true){update=it;vm.dialogNotice.value=it.optString("message")}}){Text("Verificar atualização do ONDA")}
    if(update?.optBoolean("available")==true)Button(onClick={
        runCatching {OndaStore.context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(update!!.getString("url"))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.dialogNotice.value="Não foi possível abrir o navegador."}
    }){Text("Baixar nova versão")}
    Text("O download usa a Release oficial. A instalação é confirmada pelo Android e preserva os dados quando o APK é compatível.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun AudioFileWindow(item:HistoryItem,vm:OndaViewModel,close:()->Unit) {
    var source by remember {mutableStateOf("")}
    var changes by remember {mutableStateOf(JSONObject())}
    var editing by remember {mutableStateOf(true)}
    var normalize by remember {mutableStateOf(false)}
    var lyrics by remember {mutableStateOf("")}
    var cover by remember {mutableStateOf("")}
    var preview by remember {mutableStateOf("")}
    val busy by vm.busy.collectAsStateWithLifecycle()
    val pickLyrics=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()){uri->if(uri!=null)vm.importLocal(uri,"lyrics",dialog=true){lyrics=it.absolutePath}}
    val pickCover=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()){uri->if(uri!=null)vm.importLocal(uri,"cover",dialog=true){cover=it.absolutePath}}
    LaunchedEffect(item.id) {vm.importLocal(Uri.parse(item.uri),"audio-editor",dialog=true){file->source=file.absolutePath;vm.operation("audio_read",JSONObject().put("source",source),dialog=true){changes=it.getJSONObject("record")}}}
    fun config()=OndaStore.config().put("source",source).put("output_name",item.title.substringBeforeLast('.'))
        .put("edit_metadata",editing).put("normalize_volume",normalize).put("changes",changes).put("lyrics_path",lyrics).put("cover_path",cover)
    fun finish() {vm.stopPreview();listOf(preview,source,cover,lyrics).filter {it.isNotBlank()}.forEach {File(it).delete()};close()}
    AlertDialog(onDismissRequest={if(!busy)finish()},title={Text("Editar áudio / letra")},text={
        Column(Modifier.fillMaxWidth().heightIn(max=540.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(6.dp)) {
            Text(item.title)
            Toggle("Editar metadados",editing){editing=it}
            for((key,label) in listOf("title" to "Música","artists" to "Artistas (separados por ;)","album" to "Álbum","genre" to "Gênero","release_date" to "Data")) {
                val text=if(key=="artists")changes.optJSONArray(key)?.let {a->(0 until a.length()).joinToString("; "){a.optString(it)}} ?: "" else changes.optString(key)
                OutlinedTextField(text,{value->changes=JSONObject(changes.toString()).put(key,if(key=="artists")org.json.JSONArray(value.split(';').map {it.trim()}.filter {it.isNotBlank()}) else value)},label={Text(label)},singleLine=true,enabled=editing && !busy,modifier=Modifier.fillMaxWidth())
            }
            TextButton(onClick={pickCover.launch(arrayOf("image/png","image/jpeg"))},enabled=editing && !busy){Text(if(cover.isBlank())"Escolher outra capa…" else "Capa selecionada")}
            TextButton(onClick={pickLyrics.launch(arrayOf("text/plain","application/x-lrc","application/octet-stream"))},enabled=!busy){Text(if(lyrics.isBlank())"Importar letra · TXT ou LRC" else "Letra selecionada")}
            Toggle("Normalizar volume (−16 LUFS)",normalize){normalize=it}
            Row {
                TextButton(onClick={vm.preview(source,20)},enabled=source.isNotBlank() && !busy){Text("Ouvir original")}
                TextButton(onClick={vm.stopPreview();vm.operation("normalize_preview",config(),dialog=true){preview=it.getString("path");vm.preview(preview,20)}},enabled=source.isNotBlank() && !busy){Text("Ouvir normalizado")}
            }
            PlayerControls(vm)
            Text("O arquivo original será preservado. Uma cópia será salva na pasta de destino.",style=MaterialTheme.typography.bodySmall)
            if(busy)LinearProgressIndicator(Modifier.fillMaxWidth())
        }
    },confirmButton={TextButton(enabled=source.isNotBlank() && !busy,onClick={vm.operation("audio_edit",config(),dialog=true){vm.dialogNotice.value="Cópia editada salva na pasta de destino."}}){Text("Salvar cópia editada")}},dismissButton={TextButton(enabled=!busy,onClick={finish()}){Text("Fechar")}})
}
