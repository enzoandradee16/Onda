package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.animation.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.delay
import org.json.JSONObject

@Composable internal fun LyricsButton(vm:OndaViewModel,source:String,position:()->Double,duration:Double,seek:(Double)->Unit,toggle:()->Unit) {
    val latestPosition by rememberUpdatedState(position)
    var open by remember {mutableStateOf(false)}
    var lines by remember(source) {mutableStateOf<List<Pair<Double,String>>>(emptyList())}
    var seconds by remember {mutableDoubleStateOf(0.0)}
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var alternatives by remember(source) {mutableStateOf<List<JSONObject>>(emptyList())}
    val latestSource by rememberUpdatedState(source)
    val latestLines by rememberUpdatedState(lines)
    fun applyLyrics(result:JSONObject) {
        lines=result.optJSONArray("lines")?.let {array->(0 until array.length()).map {i->val row=array.getJSONArray(i);row.getDouble(0) to row.getString(1)}} ?: emptyList()
    }
    LaunchedEffect(source) {
        if(source.isNotBlank())vm.operation("lyrics_online",JSONObject().put("source",source)) {result->
            if(latestSource==source && latestLines.isEmpty())applyLyrics(result)
        }
    }
    if(alternatives.isNotEmpty())AlertDialog(onDismissRequest={alternatives=emptyList()},title={UiText("Buscar letra online")},text={
        androidx.compose.foundation.lazy.LazyColumn {items(alternatives.size){index->
            val item=alternatives[index]
            TextButton(onClick={applyLyrics(item);alternatives=emptyList()}){Text(item.optString("title"))}
        }}
    },confirmButton={TextButton(onClick={alternatives=emptyList()}){UiText("Cancelar")}})

    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null)vm.importLocal(uri,"lyrics",dialog=true) {file->
        vm.operation("lyrics_read",JSONObject().put("source",file.absolutePath),dialog=true) {result->
            lines=result.optJSONArray("lines")?.let {array->(0 until array.length()).map {i->val row=array.getJSONArray(i);row.getDouble(0) to row.getString(1)}} ?: emptyList()
            file.delete()
        }
    }}
    TextButton(onClick={open=true}){UiText("Letra")}
    if(open)Dialog(onDismissRequest={open=false}) {
        LaunchedEffect(Unit) {while(true){seconds=latestPosition();delay(80)}}
        Surface(shape=MaterialTheme.shapes.large) {
            Column(Modifier.fillMaxWidth().padding(20.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
                UiText("Letra",style=MaterialTheme.typography.titleLarge)
                val busy by vm.busy.collectAsStateWithLifecycle()
                TextButton(enabled=!busy,onClick={
                    if(source.isBlank())vm.showNotice("Buscar letra online","Selecione uma música antes de buscar a letra online.")
                    else {
                    val requestedSource=source
                    vm.operation("lyrics_online",JSONObject().put("source",source).put("alternatives",true),dialog=true) {result->
                        if(requestedSource==latestSource)alternatives=result.optJSONArray("candidates")?.let {array->(0 until array.length()).map {array.getJSONObject(it)}} ?: emptyList()
                        vm.status.value="LRCLIB"
                    }
                    }
                }){UiText("Buscar letra online")}

                TextButton(onClick={picker.launch(arrayOf("*/*"))}){UiText("Escolher letra")}
                val raw=lines.lastOrNull {it.first<=seconds}?.second.orEmpty()
                val stamps=Regex("<([0-9]{1,3}):([0-5][0-9])(?:[.:]([0-9]{1,3}))?>").findAll(raw).toList()
                val activeColor=MaterialTheme.colorScheme.primary
                val normalColor=MaterialTheme.colorScheme.onSurface
                val text=buildAnnotatedString {
                    if(stamps.isEmpty())append(raw)
                    else {
                        withStyle(SpanStyle(fontWeight=FontWeight.Bold,color=activeColor)){append(raw.substring(0,stamps.first().range.first))}
                        stamps.forEachIndexed {index,stamp->
                            val fraction=stamp.groupValues[3]
                            val time=stamp.groupValues[1].toInt()*60+stamp.groupValues[2].toInt()+if(fraction.isEmpty())0.0 else fraction.toDouble()/Math.pow(10.0,fraction.length.toDouble())
                            withStyle(SpanStyle(fontWeight=if(seconds>=time)FontWeight.Bold else FontWeight.Normal,color=if(seconds>=time)activeColor else normalColor)) {
                                append(raw.substring(stamp.range.last+1,stamps.getOrNull(index+1)?.range?.first ?: raw.length))
                            }
                        }
                    }
                }
                if(settings.optString("lyrics_animation","Suave")=="Desativada")Text(text,style=MaterialTheme.typography.headlineSmall)
                else AnimatedContent(targetState=raw,transitionSpec={
                    val style=settings.optString("lyrics_animation","Suave")
                    val enter=when(style){"Deslizar"->slideInVertically {it/3}+fadeIn();"Zoom"->scaleIn(initialScale=0.92f)+fadeIn();else->fadeIn()}
                    enter togetherWith fadeOut()
                },label="lyrics") {_->Text(text,style=MaterialTheme.typography.headlineSmall)}
                Slider(value=seconds.coerceIn(0.0,duration.coerceAtLeast(1.0)).toFloat(),onValueChange={seconds=it.toDouble()},onValueChangeFinished={seek(seconds)},valueRange=0f..duration.coerceAtLeast(1.0).toFloat())
                Row {TextButton(onClick=toggle){UiText("Reproduzir")};TextButton(onClick={open=false}){UiText("Pronto")}}
            }
        }
    }
}
