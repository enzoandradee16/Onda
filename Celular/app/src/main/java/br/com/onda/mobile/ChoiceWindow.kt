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
    var selected by remember(question) {mutableStateOf(setOf<String>())}
    var mediaModes by remember(question) {mutableStateOf(mapOf<String,String>())}
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
    val pickCover=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) vm.importLocal(uri,"cover",dialog=true) {coverPath=it.absolutePath}}
    val candidates=event.optJSONArray("candidates")?.objects() ?: emptyList()
    val cancel={OndaStore.answer(JSONObject().put("cancel",true))}
    AlertDialog(onDismissRequest=cancel,title={Text(when(kind) {"choose_version"->"Qual versão você prefere?";"choose_catalog"->"Confirme os metadados";"choose_media"->"O que você quer baixar?";"choose_duplicate"->"Arquivo já existe";else->"Sua música, do seu jeito."})},text={
        Column(Modifier.fillMaxWidth().heightIn(max=500.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            when(kind) {
                "review_metadata"->{
                    AsyncImage(if(coverPath.isNotBlank()) java.io.File(coverPath) else cover,"Capa",Modifier.size(140.dp))
                    OutlinedTextField(title,{title=it},label={Text("Música")},singleLine=true)
                    OutlinedTextField(artist,{artist=it},label={Text("Artistas (separados por ;)")},singleLine=true)
                    OutlinedTextField(album,{album=it},label={Text("Álbum")},singleLine=true)
                    OutlinedTextField(date,{date=it},label={Text("Data")},singleLine=true)
                    OutlinedTextField(genre,{genre=it},label={Text("Gênero")},singleLine=true)
                    Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                        OutlinedTextField(track,{track=it},label={Text("Faixa")},modifier=Modifier.weight(1f),singleLine=true)
                        OutlinedTextField(disc,{disc=it},label={Text("Disco")},modifier=Modifier.weight(1f),singleLine=true)
                    }
                    OutlinedTextField(cover,{cover=it},label={Text("Capa · imagem inteira, sem cortes")},singleLine=true)
                    TextButton(onClick={pickCover.launch(arrayOf("image/jpeg","image/png"))}){Text("Escolher JPEG/PNG")}
                }
                "choose_duplicate"->{Text(event.optString("path").substringAfterLast('/'));listOf("keep" to "Manter ambos","replace" to "Substituir","skip" to "Pular").forEach {(value,label)->Toggle(label,value in selected){selected=setOf(value)}}}
                else->{
                    if(kind=="choose_media") TextButton(onClick={selected=candidates.map {it.get("id").toString()}.toSet()}){Text("Selecionar todos")}
                    candidates.forEach {candidate->
                        val id=if(kind=="choose_catalog") candidate.optString("source_url") else candidate.opt("id")?.toString().orEmpty()
                        val video=candidate.optString("kind") in listOf("video","Vídeo") || candidate.optString("type")=="video"
                        ElevatedCard(Modifier.fillMaxWidth().clickable {selected=if(kind=="choose_media") if(id in selected) selected-id else selected+id else setOf(id)}) {
                            Column(Modifier.padding(10.dp)) {
                                Toggle(candidate.optString("title",candidate.optString("label","Mídia $id")),id in selected){selected=if(kind=="choose_media") if(it) selected+id else selected-id else setOf(id)}
                                Text(candidate.optString("channel",candidate.optString("uploader",candidate.stringList("artists"))),style=MaterialTheme.typography.bodySmall)
                                if(candidate.has("match_score")) Text("Similaridade: ${(candidate.optDouble("match_score")*100).toInt()}%",style=MaterialTheme.typography.bodySmall)
                                val thumbnail=candidate.optString("thumbnail",candidate.optString("preview_url"))
                                if(thumbnail.startsWith("https://")) AsyncImage(thumbnail,"Prévia da mídia",Modifier.height(110.dp))
                                if(kind=="choose_media" && video) Select("Baixar este vídeo como",mediaModes[id]?.uppercase() ?: "MP4",listOf("MP4","MP3","M4A","FLAC","ORIGINAL")){mediaModes=mediaModes+(id to it.lowercase())}
                                if(kind=="choose_version") TextButton(onClick={
                                    val url=candidate.optString("source_url","https://www.youtube.com/watch?v=$id")
                                    vm.previewYouTube(url)
                                }){Text("Ouvir prévia")}
                            }
                        }
                    }
                }
            }
            if(kind=="choose_version") PlayerControls(vm)
        }
    },confirmButton={TextButton(enabled=kind=="review_metadata" || selected.isNotEmpty(),onClick={
        val reply=when(kind) {
            "review_metadata"->{val changes=JSONObject().put("title",title).put("artists",JSONArray(artist.split(';').map {it.trim()}.filter {it.isNotBlank()})).put("album",album).put("cover_url",cover)
                .put("release_date",date).put("genre",genre).put("track_number",track.toIntOrNull() ?: JSONObject.NULL).put("disc_number",disc.toIntOrNull() ?: JSONObject.NULL)
                if(coverPath.isNotBlank()) changes.put("cover_path",coverPath);JSONObject().put("changes",changes)}
            "choose_duplicate"->JSONObject().put("choice",selected.first())
            "choose_media"->JSONObject().put("selected_ids",JSONArray(selected.toList())).put("media_modes",JSONObject(mediaModes.filterKeys {it in selected}))
            else->JSONObject().put("selected_id",selected.first())
        }
        OndaStore.answer(reply)
    }){Text(when(kind){"choose_version"->"Baixar esta versão";"choose_catalog"->"Usar estes metadados";"review_metadata"->"Confirmar e baixar";else->"Confirmar"})}},dismissButton={TextButton(onClick=cancel){Text(if(kind=="review_metadata") "Cancelar download" else "Cancelar")}})
}
