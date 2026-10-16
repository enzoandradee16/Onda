package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.unit.dp
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject
import java.io.File
import java.util.UUID

@OptIn(ExperimentalLayoutApi::class)
@Composable internal fun VideoConverterPage(vm:OndaViewModel) {
    var source by rememberSaveable {mutableStateOf("")}
    var format by rememberSaveable {mutableStateOf("MP4")}
    var quality by rememberSaveable {mutableStateOf("Equilibrada")}
    var resolution by rememberSaveable {mutableStateOf("Original")}
    var bitrate by rememberSaveable {mutableStateOf("Automático")}
    var audioBitrate by rememberSaveable {mutableStateOf("192k")}
    var fps by rememberSaveable {mutableStateOf("Original")}
    var audio by rememberSaveable {mutableStateOf("Manter áudio")}
    var info by rememberSaveable {mutableStateOf("")}
    val audioOnly=format in listOf("MP3","M4A","AAC")
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) {
        vm.importLocal(uri,"video-converter",dialog=true) {file->
            val previous=source
            source=file.absolutePath;info=""
            val imports=File(OndaStore.context.filesDir,"imports").canonicalFile
            if(previous.isNotBlank())runCatching {File(previous).takeIf {it.canonicalFile.parentFile==imports && it.name.startsWith("video-converter-")}?.delete()}
            vm.operation("video_probe",JSONObject().put("source",source),dialog=false) {result->
                info="${result.optInt("width")} × ${result.optInt("height")} · ${mediaClock(result.optDouble("duration").toLong())}"
            }
        }
    }}
    Column(Modifier.fillMaxSize().padding(LayoutSpacing.inset).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
        PageTitle("Conversor de vídeos","Converta vídeos locais sem alterar o arquivo original.")
        OutlinedButton(onClick={picker.launch(arrayOf("video/*"))},enabled=!busy,modifier=Modifier.fillMaxWidth().testTag("converter-choose")){UiText("Escolher vídeo")}
        if(source.isNotBlank()) {
            Text(File(source).name.replaceFirst(Regex("^video-converter-[0-9a-f-]{36}-"),""))
            if(info.isNotBlank())Text(info)
        }
        if(source.isNotBlank())TextButton(enabled=!busy,onClick={
            runCatching {
                val context=OndaStore.context
                val file=File(source)
                val uri=androidx.core.content.FileProvider.getUriForFile(context,"${context.packageName}.files",file)
                val mime=android.webkit.MimeTypeMap.getSingleton().getMimeTypeFromExtension(file.extension.lowercase()) ?: "video/*"
                context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW).setDataAndType(uri,mime)
                    .addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
            }.onFailure {vm.showNotice("Prévia do original","Não foi possível abrir o vídeo no aplicativo padrão.")}
        }){UiText("Prévia do original")}
        BoxWithConstraints(Modifier.fillMaxWidth()) {
            val columns=if(maxWidth>=600.dp) 3 else if(maxWidth>=340.dp) 2 else 1
            val cellWidth=(maxWidth-LayoutSpacing.controls*(columns-1))/columns
            FlowRow(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                Box(Modifier.width(cellWidth)) { Select("Formato",format,listOf("MP4","MKV","MOV","MP3","M4A","AAC")){if(!busy)format=it} }
                if(!audioOnly)Box(Modifier.width(cellWidth)) { Select("Qualidade",quality,listOf("Equilibrada","Alta qualidade","Arquivo menor")){if(!busy)quality=it} }
                if(!audioOnly)Box(Modifier.width(cellWidth)) { Select("Resolução máxima",resolution,listOf("Original","1080p","720p","480p")){if(!busy)resolution=it} }
                if(!audioOnly)Box(Modifier.width(cellWidth)) { Select("Bitrate de vídeo",bitrate,listOf("Automático","1000k","2500k","5000k","8000k","12000k","20000k")){if(!busy)bitrate=it} }
                Box(Modifier.width(cellWidth)) { Select(if(audioOnly) "Qualidade do áudio (kbps)" else "Bitrate de áudio",audioBitrate,listOf("96k","128k","192k","256k","320k")){if(!busy)audioBitrate=it} }
                if(!audioOnly)Box(Modifier.width(cellWidth)) { Select("Quadros por segundo (FPS)",fps,listOf("Original","24","25","30","50","60")){if(!busy)fps=it} }
                if(!audioOnly)Box(Modifier.width(cellWidth)) { Select("Áudio",audio,listOf("Manter áudio","Sem áudio")){if(!busy)audio=it} }
            }
        }
        if(!audioOnly)UiText("Bitrate automático usa a qualidade escolhida; bitrate fixo usa a taxa selecionada.",style=MaterialTheme.typography.bodySmall)
        if(!audioOnly)UiText("H.264 e AAC. Preserva a proporção e não amplia o vídeo.",style=MaterialTheme.typography.bodySmall)
        if(!audioOnly)UiText("Exporta o vídeo e a primeira faixa de áudio; legendas e outras faixas não são incluídas.",style=MaterialTheme.typography.bodySmall)
        Button(enabled=!busy && source.isNotBlank(),modifier=Modifier.fillMaxWidth().testTag("converter-start"),onClick={
            val options=OndaStore.config(includeSecrets=false).put("source",source).put("video_format",format).put("video_quality",quality).put("video_resolution",resolution).put("video_bitrate",bitrate).put("audio_bitrate",audioBitrate).put("video_fps",fps).put("video_audio",audio).put("mode",format.lowercase()).put("duplicate_policy","keep")
            val base=File(options.getString("folder"),"Conversor");base.mkdirs()
            val name=File(source).name.replaceFirst(Regex("^video-converter-[0-9a-f-]{36}-"),"").substringBeforeLast('.')
            options.put("output",File(base,name.take(100)+" - "+UUID.randomUUID().toString().take(8)+"."+format.lowercase()).absolutePath)
            vm.operation("video_convert",options,dialog=false)
        }){UiText("Converter vídeo")}
        if(busy) {LinearProgressIndicator(Modifier.fillMaxWidth());TextButton(onClick={vm.cancel()}){UiText("Cancelar")}}
        if(status.isNotBlank())UiText(status,style=MaterialTheme.typography.bodySmall)
        UiText("A cópia convertida é salva no destino de downloads e aparece no Histórico.",style=MaterialTheme.typography.bodySmall)
    }
}
