package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import org.json.JSONArray
import org.json.JSONObject

@Composable fun ChoiceWindow(question: Question, vm: OndaViewModel) {
    val event=question.event
    val kind=event.optString("type")
    var selected by remember(question) {mutableStateOf(
        if(kind=="choose_media") {
            val rows=event.optJSONArray("candidates")?.objects() ?: emptyList()
            rows.filter {it.optBoolean("auto_select_media",rows.size==1)}.map {it.get("id").toString()}.toSet()
        } else setOf<String>()
    )}
    var mediaModes by remember(question) {mutableStateOf(mapOf<String,String>())}
    var rememberChoice by remember(question) {mutableStateOf(false)}
    var clearChoices by remember(question) {mutableStateOf(false)}
    var rejectedIds by remember(question) {mutableStateOf(setOf<String>())}
    val record=event.optJSONObject("record") ?: JSONObject()
    var title by remember(question) {mutableStateOf(record.cleanString("title"))}
    var artist by remember(question) {mutableStateOf(record.optJSONArray("artists")?.let {a->(0 until a.length()).joinToString("; "){a.optString(it)}} ?: "")}
    var album by remember(question) {mutableStateOf(record.cleanString("album"))}
    var date by remember(question) {mutableStateOf(record.cleanString("release_date"))}
    var genre by remember(question) {mutableStateOf(record.cleanString("genre"))}
    var track by remember(question) {mutableStateOf(record.optInt("track_number").takeIf {it>0}?.toString() ?: "")}
    var disc by remember(question) {mutableStateOf(record.optInt("disc_number").takeIf {it>0}?.toString() ?: "")}
    var cover by remember(question) {mutableStateOf(record.cleanString("cover_url"))}
    var coverPath by remember(question) {mutableStateOf("")}
    val pickCover=rememberImageSourcePicker {uri->vm.importLocal(uri,"cover",dialog=true) {coverPath=it.absolutePath}}
    val context=androidx.compose.ui.platform.LocalContext.current
    val pickFlac=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->
        if(uri!=null) vm.importLocal(uri,"flac-browser",dialog=true) {file->
            if(OndaStore.question.value==question) OndaStore.answer(JSONObject().put("path",file.absolutePath))
            else file.delete()
        }
    }
    val candidates=event.optJSONArray("candidates")?.objects() ?: emptyList()
    val cancel={OndaStore.answer(JSONObject().put("cancel",true))}
    AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest=cancel,title={UiText(when(kind) {"choose_queue_space"->"Espaço possivelmente insuficiente";"choose_flac"->"FLAC pelo navegador";"choose_version"->"Qual versão você prefere?";"choose_catalog"->"Confirme os metadados";"choose_media"->"O que você quer baixar?";"choose_queue_duplicate"->"Duplicatas detectadas";"choose_duplicate"->"Arquivo já existe";else->"Sua música, do seu jeito."})},text={
        Column(Modifier.fillMaxWidth().heightIn(max=500.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            when(kind) {
                "choose_queue_space"->{UiText(event.optString("message"));UiText("Continuar mesmo assim?")}
                "choose_flac"->{
                    Text(record.stringList("artists") + " — " + record.optString("title"))
                    UiText(event.optString("message"))
                    UiText("O arquivo original será preservado. A fila aguarda sua seleção.",style=MaterialTheme.typography.bodySmall)
                    TextButton(onClick={
                        val uri=android.net.Uri.parse(event.getString("url"))
                        if(uri.scheme=="https" && uri.host=="flacdownloader.com") {
                            try { context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,uri)) }
                            catch(_:android.content.ActivityNotFoundException){vm.showNotice("Abrir serviço","Nenhum navegador disponível.")}
                        }
                    }){UiText("Abrir serviço")}
                }
                "review_metadata"->{
                    AsyncImage(if(coverPath.isNotBlank()) java.io.File(coverPath) else cover,translateUi("Capa",LocalUiLanguage.current),Modifier.size(140.dp))
                    OutlinedTextField(title,{title=it},label={UiText("Música")},singleLine=true)
                    OutlinedTextField(artist,{artist=it},label={UiText("Artistas (separados por ;)")},singleLine=true)
                    OutlinedTextField(album,{album=it},label={UiText("Álbum")},singleLine=true)
                    OutlinedTextField(date,{date=it},label={UiText("Data")},singleLine=true)
                    OutlinedTextField(genre,{genre=it},label={UiText("Gênero")},singleLine=true)
                    Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                        OutlinedTextField(track,{track=it},label={UiText("Faixa")},modifier=Modifier.weight(1f),singleLine=true)
                        OutlinedTextField(disc,{disc=it},label={UiText("Disco")},modifier=Modifier.weight(1f),singleLine=true)
                    }
                    OutlinedTextField(cover,{cover=it},label={UiText("Capa · imagem inteira, sem cortes")},singleLine=true)
                    TextButton(onClick={pickCover()}){UiText("Escolher JPEG/PNG")}
                }
                "choose_queue_duplicate"->{
                    Text(event.optString("path"))
                    UiText("Este item já está na fila ou no histórico neste formato. Adicionar novamente?")
                }
                "choose_duplicate"->{UiText(event.optString("path").substringAfterLast('/'));listOf("keep" to "Manter ambos","replace" to "Substituir","skip" to "Pular").forEach {(value,label)->Toggle(label,value in selected){selected=setOf(value)}}}
                else->{
                    if(kind=="choose_media") {
                        val allIds=candidates.map {it.get("id").toString()}.toSet()
                        val allSelected=allIds.isNotEmpty() && selected.containsAll(allIds)
                        TextButton(onClick={selected=if(allSelected) emptySet() else allIds}){UiText(if(allSelected) "Desmarcar todas" else "Selecionar todas")}
                    }
                    candidates.filterNot {kind=="choose_version" && it.opt("id")?.toString() in rejectedIds}.forEach {candidate->
                        val id=if(kind=="choose_catalog") candidate.optString("source_url") else candidate.opt("id")?.toString().orEmpty()
                        val video=candidate.optString("kind") in listOf("video","Vídeo") || candidate.optString("type")=="video"
                        ElevatedCard(Modifier.fillMaxWidth().clickable {selected=if(kind=="choose_media") if(id in selected) selected-id else selected+id else setOf(id)}) {
                            Column(Modifier.padding(10.dp)) {
                                Toggle(candidate.optString("title",candidate.optString("label","Mídia $id")),id in selected){selected=if(kind=="choose_media") if(it) selected+id else selected-id else setOf(id)}
                                Text(candidate.optString("channel",candidate.optString("uploader",candidate.stringList("artists"))),style=MaterialTheme.typography.bodySmall)
                                if(candidate.optBoolean("manual_review")) UiText("Conferir",style=MaterialTheme.typography.bodySmall)
                                else if(candidate.has("match_score")) UiText("Similaridade: ${(candidate.optDouble("match_score")*100).toInt()}%",style=MaterialTheme.typography.bodySmall)
                                val seconds=if(candidate.optLong("duration_ms")>0) candidate.optLong("duration_ms")/1000 else candidate.optDouble("duration",0.0).toLong()
                                Text(listOf(candidate.cleanString("album"),candidate.cleanString("release_date"),candidate.cleanString("platform"),if(seconds>0)mediaClock(seconds) else "").filter {it.isNotBlank()}.joinToString(" · "),style=MaterialTheme.typography.bodySmall)
                                candidate.optJSONArray("match_reasons")?.let {reasons->Text((0 until reasons.length()).joinToString("; "){translateUi(reasons.optString(it))},style=MaterialTheme.typography.bodySmall)}
                                val thumbnail=candidate.optString("thumbnail",candidate.optString("preview_url"))
                                if(thumbnail.startsWith("https://")) AsyncImage(thumbnail,translateUi("Prévia da mídia",LocalUiLanguage.current),Modifier.height(110.dp))
                                if(kind=="choose_media" && video && !candidate.optBoolean("automatic_quality")) {
                                    val outputs=linkedMapOf("Vídeo · MP4" to "mp4", "Vídeo · MKV" to "video", "Só áudio · MP3" to "mp3", "Só áudio · M4A" to "m4a", "Só áudio · FLAC" to "flac", "Só áudio · original" to "original")
                                    val mode=mediaModes[id] ?: candidate.optString("default_mode", "mp4")
                                    Select("Baixar este vídeo como",outputs.entries.firstOrNull {it.value==mode}?.key ?: "Vídeo · MP4",outputs.keys.toList()){mediaModes=mediaModes+(id to outputs.getValue(it))}
                                }
                                if(kind=="choose_media" && candidate.optBoolean("photo_choice") && !candidate.optBoolean("automatic_quality")) {
                                    val outputs=if(candidate.optBoolean("has_audio")) linkedMapOf("Só foto" to "photos", "Foto com música · MP4" to "photo_video") else linkedMapOf("Só foto" to "photos")
                                    Select("Baixar esta foto como",outputs.entries.firstOrNull {it.value==mediaModes[id]}?.key ?: "Só foto",outputs.keys.toList()){mediaModes=mediaModes+(id to outputs.getValue(it))}
                                    if(!candidate.optBoolean("has_audio")) UiText("A plataforma não disponibilizou a música desta foto.",style=MaterialTheme.typography.bodySmall)
                                }
                                if(kind=="choose_version") TextButton(onClick={
                                    selected=setOf(id)
                                    val url=candidate.optString("source_url","https://www.youtube.com/watch?v=$id")
                                    if(record.optString("_audio_provider")=="Monochrome" || event.optString("audio_provider")=="Monochrome") vm.preview(url) else vm.previewYouTube(url)
                                }){UiText("Ouvir prévia")}
                            }
                        }
                    }
                }
            }
            if(kind=="choose_version") {
                PlayerControls(vm)
                Toggle("Lembrar esta escolha após verificar novamente",rememberChoice){rememberChoice=it}
                TextButton(enabled=selected.isNotEmpty(),onClick={
                    vm.stopPreview()
                    rejectedIds=rejectedIds+selected;selected=emptySet()
                }){UiText("Versão errada")}
                if(selected.isEmpty()) UiText("Selecione uma versão da lista antes de marcar como errada.",style=MaterialTheme.typography.bodySmall)
                if(candidates.isNotEmpty() && candidates.all {it.opt("id")?.toString() in rejectedIds})
                    UiText("Todas as versões foram rejeitadas. Use Desfazer para restaurar a lista.",style=MaterialTheme.typography.bodySmall)
                TextButton(onClick={clearChoices=true;rejectedIds=emptySet()}){UiText("Desfazer escolhas e rejeições salvas")}
                if(rejectedIds.isNotEmpty()) UiText("Versões marcadas como erradas: ${rejectedIds.size}",style=MaterialTheme.typography.bodySmall)
            }
        }
    },confirmButton={TextButton(enabled=kind in setOf("choose_flac","review_metadata","choose_queue_duplicate","choose_queue_space") || selected.isNotEmpty(),onClick={
        if(kind=="choose_flac") {
            pickFlac.launch(arrayOf("audio/flac","audio/x-flac","application/octet-stream"))
            return@TextButton
        }
        val reply=when(kind) {
            "choose_queue_space"->JSONObject()
            "review_metadata"->{val changes=JSONObject().put("title",title).put("artists",JSONArray(artist.split(';').map {it.trim()}.filter {it.isNotBlank()})).put("album",album).put("cover_url",cover)
                .put("release_date",date).put("genre",genre).put("track_number",track.toIntOrNull() ?: JSONObject.NULL).put("disc_number",disc.toIntOrNull() ?: JSONObject.NULL)
                if(coverPath.isNotBlank()) changes.put("cover_path",coverPath);JSONObject().put("changes",changes)}
            "choose_queue_duplicate"->JSONObject().put("add",true)
            "choose_duplicate"->JSONObject().put("choice",selected.first())
            "choose_media"->JSONObject().put("selected_ids",JSONArray(selected.toList())).put("media_modes",JSONObject(mediaModes.filterKeys {it in selected}))
            else->JSONObject().put("selected_id",selected.first()).put("remember_choice",rememberChoice).put("clear_choices",clearChoices).put("rejected_ids",JSONArray((rejectedIds-selected).toList()))
        }
        OndaStore.answer(reply)
    }){UiText(when(kind){"choose_queue_duplicate"->"Adicionar novamente";"choose_flac"->"Selecionar FLAC baixado";"choose_version"->"Baixar esta versão";"choose_catalog"->"Usar estes metadados";"review_metadata"->"Confirmar e baixar";else->"Confirmar"})}},dismissButton={Row {
        if(kind=="choose_queue_duplicate") TextButton(onClick={OndaStore.cancelAllDuplicates()}){UiText("Cancelar todas")}
        TextButton(onClick=cancel){UiText(if(kind=="review_metadata") "Cancelar download" else "Cancelar")}
    }})
}
