package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import org.json.JSONObject
import java.util.Locale

@Composable fun TrackDownloadDialog(record:JSONObject,baseOptions:JSONObject,onDismiss:()->Unit,onSubmit:(JSONObject,Boolean)->Unit) {
    val simple=baseOptions.optBoolean("simple_download_ui",false)
    var preset by rememberSaveable {mutableStateOf("MP3 320")}
    var format by rememberSaveable {mutableStateOf("M4A")}
    var quality by rememberSaveable {mutableStateOf("256 kbps")}
    val qualities=if(format=="MP3")listOf("320 kbps","256 kbps","192 kbps","128 kbps","96 kbps") else listOf("256 kbps","192 kbps","128 kbps","96 kbps")
    val mode=if(simple) "mp3" else when(preset) {"FLAC"->"flac";"Personalizar"->format.lowercase(Locale.ROOT);else->"mp3"}
    val bitrate=if(simple) "320 kbps" else when(preset) {"MP3 320"->"320 kbps";"MP3 128"->"128 kbps";else->quality}
    fun submit(now:Boolean) {
        val options=JSONObject(baseOptions.toString()).put("mode",mode)
        if(mode!="flac")options.put("audio_quality",bitrate)
        onSubmit(options,now)
    }
    AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest=onDismiss,title={UiText("Escolha o formato")},text={
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
            Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
                AsyncImage(record.cleanString("cover_url"),translateUi("Capa do álbum",LocalUiLanguage.current),Modifier.size(64.dp))
                Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.text)) {
                    Text(record.cleanString("title"),style=MaterialTheme.typography.titleMedium)
                    Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall)
                    Text(record.cleanString("album").ifBlank {translateUi("Álbum não informado",LocalUiLanguage.current)},style=MaterialTheme.typography.bodySmall)
                }
            }
            if(!simple) {
            Select("Formato",preset,listOf("MP3 320","MP3 128","FLAC","Personalizar")){preset=it}
            UiText(when(preset) {
                "MP3 320"->"Alta qualidade · maior compatibilidade"
                "MP3 128"->"Arquivo menor · economiza espaço"
                "FLAC"->"Monochrome · FLAC direto quando disponível"
                else->"Escolher MP3 ou M4A e outro bitrate"
            },style=MaterialTheme.typography.bodySmall)
            if(preset=="Personalizar") {
                Select("Formato de áudio",format,listOf("MP3","M4A")) {
                    format=it
                    if(it=="M4A" && quality=="320 kbps")quality="256 kbps"
                }
                Select("Qualidade de áudio",quality,qualities){quality=it}
            }
            }
            val duration=record.optLong("duration_ms")
            UiText(if(mode!="flac" && duration>0) {
                val megabytes=duration*bitrate.substringBefore(' ').toDouble()/8/1024/1024
                "Tamanho estimado: ≈ "+String.format(Locale.getDefault(),"%.1f MB",megabytes)
            } else "Tamanho variável · valor real mostrado ao concluir",style=MaterialTheme.typography.bodySmall)
            UiText("Inclui capa e metadados disponíveis. MP3/M4A usam YouTube; FLAC usa Monochrome.",style=MaterialTheme.typography.bodySmall)
        }
    },confirmButton={Column(Modifier.fillMaxWidth(),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
        Button(onClick={submit(true)},enabled=record.optString("source_url").isNotBlank(),modifier=Modifier.fillMaxWidth()){UiText("Baixar agora")}
        TextButton(onClick={submit(false)},enabled=record.optString("source_url").isNotBlank(),modifier=Modifier.fillMaxWidth()){UiText("Adicionar à fila")}
        TextButton(onClick=onDismiss,modifier=Modifier.fillMaxWidth()){UiText("Voltar")}
    }})
}
