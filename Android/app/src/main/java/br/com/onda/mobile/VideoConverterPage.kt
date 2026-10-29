package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Alignment
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.foundation.horizontalScroll
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
    var batch by rememberSaveable {mutableStateOf(arrayListOf<String>())}
    var source by rememberSaveable {mutableStateOf("")}
    var format by rememberSaveable {mutableStateOf("MP4")}
    var quality by rememberSaveable {mutableStateOf("Equilibrada")}
    var resolution by rememberSaveable {mutableStateOf("Original")}
    var bitrate by rememberSaveable {mutableStateOf("Automático")}
    var audioBitrate by rememberSaveable {mutableStateOf("192k")}
    var fps by rememberSaveable {mutableStateOf("Original")}
    var audio by rememberSaveable {mutableStateOf("Manter áudio")}
    var advanced by rememberSaveable {mutableStateOf(false)}
    var trimSilence by rememberSaveable {mutableStateOf(false)}
    var info by rememberSaveable {mutableStateOf("")}
    val audioSource=(if(batch.isNotEmpty())batch else listOf(source)).any {File(it).extension.lowercase() in listOf("mp3","m4a","aac","flac","wav","ogg","opus")}
    val audioOnly=format in listOf("MP3","M4A","AAC")
    val busy by vm.busy.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var more by remember {mutableStateOf(false)}
    val folderPicker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) {uri->if(uri!=null) {
        runCatching {
            OndaStore.context.contentResolver.takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("output_uri",uri.toString()))
        }.onFailure {vm.showNotice("Pasta de destino",uiExceptionMessage(it,"Não foi possível abrir este arquivo."),true)}
    }}
    val destination=remember(settings.optString("output_uri")) {
        val selected=settings.optString("output_uri")
        if(selected.isBlank()) {if(android.os.Build.VERSION.SDK_INT>=29) "Downloads/ONDA/Conversor" else File(OndaStore.config().getString("folder"),"Conversor").absolutePath}
        else runCatching {android.provider.DocumentsContract.getTreeDocumentId(Uri.parse(selected)).let {id->if(id.startsWith("primary:"))"/storage/emulated/0/"+id.substringAfter(":") else id}.trimEnd('/')+"/Conversor"}.getOrDefault(selected)
    }
    val batchPicker=rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) {uris->
        if(uris.isNotEmpty())vm.importConversionBatch(uris) {paths->
            val previous=if(batch.isNotEmpty())batch.toList() else listOf(source).filter {it.isNotBlank()}
            batch=ArrayList((previous+paths).distinct());source=batch.firstOrNull() ?: "";info=""
            if(paths.any {File(it).extension.lowercase() in listOf("mp3","m4a","aac","flac","wav","ogg","opus")})format="MP3"
        }
    }
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) {
        vm.importLocal(uri,"video-converter",dialog=true) {file->
            batch.forEach {File(it).delete()};batch=arrayListOf()
            val previous=source
            source=file.absolutePath;info=""
            val isAudio=file.extension.lowercase() in listOf("mp3","m4a","aac","flac","wav","ogg","opus")
            format=if(isAudio) "MP3" else "MP4"
            val imports=File(OndaStore.context.filesDir,"imports").canonicalFile
            if(previous.isNotBlank())runCatching {File(previous).takeIf {it.canonicalFile.parentFile==imports && it.name.startsWith("video-converter-")}?.delete()}
            vm.operation("video_probe",JSONObject().put("source",source).put("audio_only",isAudio),dialog=false) {result->
                info=if(isAudio) mediaClock(result.optDouble("duration").toLong()) else "${result.optInt("width")} × ${result.optInt("height")} · ${mediaClock(result.optDouble("duration").toLong())}"
            }
        }
    }}
    Column(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        ToolHeading("Conversor") {
            Box {
                IconButton(onClick={more=true},modifier=Modifier.testTag("converter-more-actions")){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                DropdownMenu(more,{more=false}) {
                    DropdownMenuItem(text={UiText("Adicionar arquivos")},enabled=!busy,onClick={more=false;batchPicker.launch(arrayOf("audio/*","video/*"))})
                    DropdownMenuItem(text={UiText(if(advanced)"Ocultar opções avançadas" else "Opções avançadas")},onClick={more=false;advanced=!advanced})
                }
            }
        }
        ConverterCard {
            UiText("Arquivo de origem",style=MaterialTheme.typography.titleSmall)
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                Surface(shape=RoundedCornerShape(10.dp),border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant),color=MaterialTheme.colorScheme.surface,modifier=Modifier.size(48.dp,64.dp)) {
                    Box(contentAlignment=Alignment.Center){OndaIcon("file",modifier=Modifier.size(26.dp))}
                }
                Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                    OutlinedButton(onClick={picker.launch(arrayOf("audio/*","video/*"))},enabled=!busy,shape=RoundedCornerShape(10.dp),modifier=Modifier.fillMaxWidth().testTag("converter-choose")){UiText("Abrir arquivo")}
                    if(source.isNotBlank()) {
                        Text(File(source).name.replaceFirst(Regex("^(?:video-converter|audio-batch|conversion-batch)-[0-9a-f-]{36}-"),""),style=MaterialTheme.typography.bodyMedium,maxLines=2,overflow=TextOverflow.Ellipsis)
                        if(info.isNotBlank())Text(info,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                        if(batch.size>1)Text("${batch.size} · "+translateUi("Arquivos selecionados"),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    } else UiText("Escolha áudios ou vídeos do aparelho para começar.",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        ConverterCard {
            UiText("Configurações",style=MaterialTheme.typography.titleSmall)
            ConverterChoice("Formato",format,if(audioSource)listOf("MP3","M4A","AAC") else listOf("MP4","MKV","MOV","MP3","M4A","AAC")){if(!busy)format=it}
            if(audioOnly)ConverterChoice("Qualidade",audioBitrate.removeSuffix("k")+" kbps",listOf("96 kbps","128 kbps","192 kbps","256 kbps","320 kbps")){if(!busy)audioBitrate=it.substringBefore(' ')+"k"}
            else ConverterChoice("Qualidade",quality,listOf("Equilibrada","Alta qualidade","Arquivo menor")){if(!busy)quality=it}
            if(advanced) {
                if(!audioOnly) {
                    Select("Resolução máxima",resolution,listOf("Original","1080p","720p","480p")){if(!busy)resolution=it}
                    Select("Bitrate de vídeo",bitrate,listOf("Automático","1000k","2500k","5000k","8000k","12000k","20000k")){if(!busy)bitrate=it}
                    Select("Bitrate de áudio",audioBitrate,listOf("96k","128k","192k","256k","320k")){if(!busy)audioBitrate=it}
                    Select("Quadros por segundo (FPS)",fps,listOf("Original","24","25","30","50","60")){if(!busy)fps=it}
                    Select("Áudio",audio,listOf("Manter áudio","Sem áudio")){if(!busy)audio=it}
                    UiText("H.264 e AAC. Preserva a proporção e não amplia o vídeo.",style=MaterialTheme.typography.bodySmall)
                    UiText("Exporta o vídeo e a primeira faixa de áudio; legendas e outras faixas não são incluídas.",style=MaterialTheme.typography.bodySmall)
                }
                ToolSwitch("Remover silêncio",trimSilence,"No início e no fim",enabled=!busy){trimSilence=it}
            }
        }
        ConverterCard {
            UiText("Pasta de destino",style=MaterialTheme.typography.titleSmall)
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                OndaIcon("folder",modifier=Modifier.size(22.dp))
                Text(destination,Modifier.weight(1f),style=MaterialTheme.typography.bodySmall,maxLines=2,overflow=TextOverflow.Ellipsis,color=MaterialTheme.colorScheme.onSurfaceVariant)
                TextButton(onClick={folderPicker.launch(null)},enabled=!busy,modifier=Modifier.testTag("converter-destination")){UiText("Alterar destino",style=MaterialTheme.typography.labelSmall)}
            }
        }
        Button(enabled=!busy && source.isNotBlank(),shape=RoundedCornerShape(12.dp),modifier=Modifier.fillMaxWidth().heightIn(min=48.dp).testTag("converter-start"),onClick={
            val options=OndaStore.config(includeSecrets=false).put("source",source).put("video_format",format).put("video_quality",quality).put("video_resolution",resolution).put("video_bitrate",bitrate).put("audio_bitrate",audioBitrate).put("video_fps",fps).put("video_audio",audio).put("mode",format.lowercase()).put("duplicate_policy","keep").put("trim_silence",trimSilence)
            val base=File(options.getString("folder"),"Conversor");base.mkdirs()
            val name=File(source).name.replaceFirst(Regex("^video-converter-[0-9a-f-]{36}-"),"").substringBeforeLast('.')
            options.put("output",File(base,name.take(100)+" - "+UUID.randomUUID().toString().take(8)+"."+format.lowercase()).absolutePath)
            if(batch.isNotEmpty())vm.operation("convert_batch",options.put("sources",org.json.JSONArray(batch)).put("output_folder",base.absolutePath),dialog=false)
            else vm.operation("video_convert",options,dialog=false)
        }){OndaIcon("convert",modifier=Modifier.size(20.dp));Spacer(Modifier.width(8.dp));UiText("Converter")}
        if(busy) {TextButton(onClick={vm.cancel()}){UiText("Cancelar")}}
        if(status.isNotBlank())UiText(status,style=MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(8.dp))
        UiText("A cópia convertida é salva no destino de downloads e aparece no Histórico.",style=MaterialTheme.typography.bodySmall)
    }
}


@Composable private fun ConverterCard(content:@Composable ColumnScope.()->Unit) {
    Surface(Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp),color=MaterialTheme.colorScheme.surfaceContainerLow,border=BorderStroke(1.dp,MaterialTheme.colorScheme.outlineVariant)) {
        Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(10.dp),content=content)
    }
}

@Composable private fun ConverterChoice(label:String,value:String,choices:List<String>,changed:(String)->Unit) {
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)) {
        UiText(label,Modifier.weight(.6f),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        Select("",value,choices,Modifier.weight(1.2f),changed)
    }
}
