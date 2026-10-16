package br.com.onda.mobile

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
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject
import java.io.File

@Composable fun AdvancedDownloadOptions(settings:JSONObject,put:(String,Any)->Unit) {
    UiText("Fila e agendamento",style=MaterialTheme.typography.titleMedium)
    SettingsDivider()
    Select("Downloads simultâneos (1 a 4)",settings.optString("concurrent_downloads","1"),listOf("1","2","3","4")){put("concurrent_downloads",it)}
    SettingsDivider()
    Toggle("Detectar duplicatas na fila e no histórico",settings.optBoolean("detect_duplicates",true)){put("detect_duplicates",it)}
    SettingsDivider()
    Toggle("Retomar arquivos interrompidos quando possível",settings.optBoolean("resume_downloads",true)){put("resume_downloads",it)}
    SettingsDivider()
    Toggle("Retomar fila ao abrir o ONDA",settings.optBoolean("resume_queue")){put("resume_queue",it)}
    SettingsDivider()
    Toggle("Normalizar volume dos próximos downloads",settings.optBoolean("normalize_volume")){put("normalize_volume",it)}
    SettingsDivider()
    Toggle("Agendar downloads",settings.optBoolean("schedule_enabled")){put("schedule_enabled",it)}
    SettingsDivider()
    Row(horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        OutlinedTextField(settings.optString("schedule_start","22:00"),{put("schedule_start",it)},label={UiText("Começar · HH:MM")},singleLine=true,modifier=Modifier.weight(1f))
        OutlinedTextField(settings.optString("schedule_stop","07:00"),{put("schedule_stop",it)},label={UiText("Parar · HH:MM")},singleLine=true,modifier=Modifier.weight(1f))
    }
    if(settings.optBoolean("schedule_enabled")) {
        val valid=runCatching {java.time.LocalTime.parse(settings.optString("schedule_start"))!=java.time.LocalTime.parse(settings.optString("schedule_stop"))}.getOrDefault(false)
        if(!valid)UiText("Informe horários diferentes no formato HH:MM.",color=MaterialTheme.colorScheme.error)
    }
    UiText("O Android pode atrasar o início para economizar bateria. A fila interrompida fica pendente para retomar.",style=MaterialTheme.typography.bodySmall)
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
    TextButton(onClick={export.launch("ONDA-configuracoes.json")}){UiText("Exportar configurações…")}
    SettingsDivider()
    TextButton(onClick={importFile.launch(arrayOf("application/json","text/plain"))}){UiText("Importar configurações…")}
    UiText("A transferência não inclui contas, cookies nem caminhos de pastas.",style=MaterialTheme.typography.bodySmall)
}

@Composable fun AppUpdateControls(vm:OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var update by remember {mutableStateOf<JSONObject?>(null)}
    SettingsDivider()
    Toggle("Verificar atualizações do ONDA ao abrir",settings.optBoolean("check_updates")){OndaStore.saveSettings(JSONObject(settings.toString()).put("check_updates",it))}
    SettingsDivider()
    OutlinedButton(onClick={vm.operation("app_update",JSONObject().put("version",BuildConfig.VERSION_NAME),dialog=true){update=it;vm.showNotice("Verificar atualização do ONDA",it.optString("message"))}}){UiText("Verificar atualização do ONDA")}
    val updater=remember {InAppUpdate(OndaStore.context)}
    var download by remember {mutableStateOf(UpdateDownload())}
    val language=LocalUiLanguage.current
    val lifecycleOwner=LocalLifecycleOwner.current
    LaunchedEffect(updater,lifecycleOwner,download.status) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            pollUpdateDownload(updater::state,{download=it})
        }
    }
    val downloading=download.inProgress
    if(downloading) {
        UiText("Baixando atualização do ONDA")
        if(download.total>0) {
            val progress=(download.bytes.toFloat()/download.total).coerceIn(0f,1f)
            LinearProgressIndicator(progress={progress},modifier=Modifier.fillMaxWidth())
            Text("${(progress*100).toInt()}%")
        } else LinearProgressIndicator(modifier=Modifier.fillMaxWidth())
        TextButton(onClick={updater.cancel();download=UpdateDownload()}) {UiText("Cancelar download da atualização")}
    } else if(download.status==android.app.DownloadManager.STATUS_SUCCESSFUL) {
        Button(onClick={runCatching {updater.install()}.onSuccess {opened->
            if(!opened)vm.showNotice("Instalar atualização","Permita a instalação pelo ONDA e volte para tocar em Instalar atualização.")
        }.onFailure {vm.showNotice("Instalar atualização",it.message ?: "Não foi possível iniciar a instalação.")}}) {UiText("Instalar atualização")}
        TextButton(onClick={updater.cancel();download=UpdateDownload()}) {UiText("Descartar atualização baixada")}
    } else {
        if(download.status==android.app.DownloadManager.STATUS_FAILED)UiText("Não foi possível baixar a atualização. Tente novamente.")
        if(update?.optBoolean("available")==true)Button(onClick={
            runCatching {updater.start(update!!.getString("url"),language);download=updater.state()}
                .onFailure {vm.showNotice("Baixar nova versão",it.message ?: "Não foi possível baixar a atualização. Tente novamente.")}
        }){UiText("Baixar nova versão")}
    }
    UiText("A atualização é baixada dentro do ONDA e continua em segundo plano. Ao terminar, toque em Instalar atualização e confirme no Android. Seus dados são preservados.",style=MaterialTheme.typography.bodySmall)
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
    Column(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
            Text(item.title,modifier=Modifier.weight(1f),maxLines=2,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            Button(enabled=!busy,onClick={finish()},contentPadding=PaddingValues(horizontal=16.dp)){UiText("Escolher outro arquivo",maxLines=1,softWrap=false)}
        }
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(LayoutSpacing.inset),horizontalAlignment=androidx.compose.ui.Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                    UiText("Capa do álbum",style=MaterialTheme.typography.titleMedium)
            val originalBitmap=remember(originalCover) {runCatching {val bytes=android.util.Base64.decode(originalCover,android.util.Base64.DEFAULT);android.graphics.BitmapFactory.decodeByteArray(bytes,0,bytes.size)}.getOrNull()}
            if(cover.isNotBlank() || originalBitmap!=null) coil.compose.AsyncImage(model=if(cover.isNotBlank())File(cover) else originalBitmap,contentDescription=translateUi("Capa do álbum",LocalUiLanguage.current),modifier=Modifier.size(208.dp))
            else UiText("Sem capa",style=MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement=Arrangement.Center) {
                TextButton(onClick={pickCover()},enabled=editing && !busy){UiText("Escolher outra capa…")}
                TextButton(onClick={File(cover).delete();cover=""},enabled=cover.isNotBlank() && !busy){UiText("Desfazer capa")}
            }
            OutlinedButton(onClick={cropCandidate=cover},enabled=cover.isNotBlank() && editing && !busy){UiText("Ajustar capa")}
                }
            }
            Toggle("Editar metadados",editing){editing=it}
            for((key,label) in listOf("title" to "Música","artists" to "Artistas (separados por ;)","album" to "Álbum","genre" to "Gênero","release_date" to "Data")) {
                val text=if(key=="artists")changes.optJSONArray(key)?.let {a->(0 until a.length()).joinToString("; "){a.optString(it)}} ?: "" else changes.optString(key)
                OutlinedTextField(text,{value->changes=JSONObject(changes.toString()).put(key,if(key=="artists")org.json.JSONArray(value.split(';').map {it.trim()}.filter {it.isNotBlank()}) else value)},label={UiText(label)},singleLine=true,enabled=editing && !busy,modifier=Modifier.fillMaxWidth())
            }
            TextButton(onClick={pickLyrics.launch(arrayOf("text/plain","application/x-lrc","application/octet-stream"))},enabled=!busy){UiText(if(lyrics.isBlank())"Importar letra · TXT ou LRC" else "Letra selecionada")}
            Toggle("Normalizar volume (−16 LUFS)",normalize){normalize=it}
            Row {
                TextButton(onClick={vm.preview(source,20)},enabled=source.isNotBlank() && !busy){UiText("Ouvir original")}
                TextButton(onClick={vm.stopPreview();vm.operation("normalize_preview",config(),dialog=false){preview=it.getString("path");vm.preview(preview,20)}},enabled=source.isNotBlank() && !busy){UiText("Ouvir normalizado")}
            }
            PlayerControls(vm)
            Toggle("Sobrescrever arquivo original",overwrite){if(!busy)overwrite=it}
            UiText(if(overwrite) "O arquivo original será substituído, mantendo o nome e a pasta." else "O arquivo original será preservado. Uma cópia será salva na pasta de destino.",style=MaterialTheme.typography.bodySmall)
            if(busy)LinearProgressIndicator(Modifier.fillMaxWidth())
        Button(enabled=loaded && !busy,onClick={vm.operation("audio_edit",config(),dialog=false){if(overwrite)finish();vm.status.value=if(overwrite) "Arquivo original atualizado." else "Cópia editada salva na pasta de destino."}},modifier=Modifier.fillMaxWidth()){UiText(if(overwrite) "Salvar no original" else "Salvar cópia editada")}
        Spacer(Modifier.height(LayoutSpacing.section))
    }
}
