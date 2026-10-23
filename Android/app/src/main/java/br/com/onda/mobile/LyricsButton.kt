package br.com.onda.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.platform.LocalContext
import android.content.Intent
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.delay
import org.json.JSONObject

internal fun lyricActiveIndex(lines:List<Pair<Double,String>>,seconds:Double):Int =
    if(lines.none {it.first>0}) -1 else lines.indexOfLast {it.first<=seconds}
internal fun lyricPlainText(text:String)=text.replace(Regex("<\\d{1,3}:[0-5]\\d(?:[.:]\\d{1,3})?>"),"")

@Composable internal fun LyricsButton(vm:OndaViewModel,source:String,position:()->Double,duration:Double,seek:(Double)->Unit,toggle:()->Unit,
    isPlaying:()->Boolean={vm.previewActive.value},previous:()->Unit={seek(0.0)},next:(()->Unit)?=null,
    title:String="",artist:String="",showButton:Boolean=true,openRequest:Int=0) {
    val latestSource by rememberUpdatedState(source)
    val latestPosition by rememberUpdatedState(position)
    var open by remember {mutableStateOf(false)}
    var menu by remember {mutableStateOf(false)}
    val context=LocalContext.current
    LaunchedEffect(openRequest){if(openRequest>0)open=true}
    var seconds by remember(source) {mutableDoubleStateOf(0.0)}
    var dragged by remember(source) {mutableStateOf<Float?>(null)}
    val (lyricsBackground,lyricsInk)=rememberLyricsColors(vm,source)
    val cache by vm.lyricsCache.collectAsStateWithLifecycle()
    val lines=cache[source].orEmpty()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    var alternatives by remember(source) {mutableStateOf<List<JSONObject>>(emptyList())}
    var searching by remember(source) {mutableStateOf(false)}
    fun applyLyrics(result:JSONObject) {
        result.optJSONArray("lines")?.let {rows->vm.storeLyrics(source,(0 until rows.length()).map {i->rows.getJSONArray(i).let {it.getDouble(0) to it.getString(1)}})}
    }
    LaunchedEffect(source) {vm.lookupLyrics(source)}
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri->if(uri!=null) {
        val requestedSource=source
        vm.importLocal(uri,"lyrics",dialog=true) {file->vm.operation("lyrics_read",JSONObject().put("source",file.absolutePath),dialog=true) {result->
            if(requestedSource==latestSource)applyLyrics(result)
            file.delete()
        }}
    }}
    if(showButton)IconButton(onClick={open=true},modifier=Modifier.testTag("lyrics-button")){OndaIcon("microphone","Letra",Modifier.size(24.dp))}
    if(open)Dialog(onDismissRequest={open=false},properties=DialogProperties(usePlatformDefaultWidth=false)) {
        val listState=rememberLazyListState()
        val active=lyricActiveIndex(lines,seconds)
        val animation=settings.optString("lyrics_animation","Suave")
        LaunchedEffect(source) {listState.scrollToItem(0);while(true){if(dragged==null)seconds=latestPosition();delay(80)}}
        LaunchedEffect(active) {if(active>=0) {if(animation=="Desativada")listState.scrollToItem(active) else listState.animateScrollToItem(active)}}
        Surface(Modifier.fillMaxSize().testTag("lyrics-fullscreen"),color=lyricsBackground,contentColor=lyricsInk) {
            Column(Modifier.fillMaxSize().padding(24.dp),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                    IconButton(onClick={open=false}){OndaIcon("down","Recolher letra",Modifier.size(26.dp))}
                    Column(Modifier.weight(1f),horizontalAlignment=Alignment.CenterHorizontally) {
                        Text(title.ifBlank {importedAudioName(source)},maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.titleSmall,fontWeight=FontWeight.Bold)
                        Text(artist,maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall)
                    }
                    Spacer(Modifier.width(48.dp))
                }
                LazyColumn(Modifier.weight(1f).fillMaxWidth().testTag("lyrics-lines"),state=listState,verticalArrangement=Arrangement.spacedBy(LayoutSpacing.section),contentPadding=PaddingValues(vertical=24.dp)) {
                    if(lines.isEmpty())item {UiText("Letra não encontrada para esta gravação.",Modifier.fillMaxWidth(),style=MaterialTheme.typography.bodyMedium)}
                    itemsIndexed(lines) {index,line->
                        val selected=index==active
                        val ink=lyricsInk
                        val normal=lyricsInk.copy(alpha=.72f)
                        val stamps=Regex("<([0-9]{1,3}):([0-5][0-9])(?:[.:]([0-9]{1,3}))?>").findAll(line.second).toList()
                        val text=buildAnnotatedString {
                            if(!selected||stamps.isEmpty())append(lyricPlainText(line.second))
                            else {
                                append(line.second.substring(0,stamps.first().range.first))
                                stamps.forEachIndexed {i,stamp->
                                    val fraction=stamp.groupValues[3]
                                    val time=stamp.groupValues[1].toInt()*60+stamp.groupValues[2].toInt()+if(fraction.isEmpty())0.0 else fraction.toDouble()/Math.pow(10.0,fraction.length.toDouble())
                                    withStyle(SpanStyle(color=if(seconds>=time)ink else normal,fontWeight=if(seconds>=time)FontWeight.Bold else FontWeight.Normal)){append(line.second.substring(stamp.range.last+1,stamps.getOrNull(i+1)?.range?.first ?: line.second.length))}
                                }
                            }
                        }
                        Text(text,Modifier.fillMaxWidth().lyricAnimation(index to selected,animation,emphasized=selected,muted=active>=0&&!selected).clickable(enabled=lines.any {it.first>0}){seconds=line.first;seek(line.first)}.testTag("lyric-line-$index"),color=if(selected)ink else normal,style=MaterialTheme.typography.headlineSmall,textAlign=TextAlign.Start,fontWeight=FontWeight.Bold)
                    }
                }
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    IconButton(onClick={
                        val text=listOf(title,artist,lines.joinToString("\n"){lyricPlainText(it.second)}).filter {it.isNotBlank()}.joinToString("\n\n")
                        context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,text),translateUi("Compartilhar letra")))
                    },enabled=lines.isNotEmpty()){OndaIcon("share","Compartilhar letra",Modifier.size(25.dp))}
                    Box {
                        IconButton(onClick={menu=true}){OndaIcon("more-vertical","Mais",Modifier.size(25.dp))}
                        DropdownMenu(menu,{menu=false}) {
                            DropdownMenuItem(text={UiText(if(searching)"Pesquisando…" else "Buscar letra online")},enabled=!searching&&source.isNotBlank(),onClick={
                                menu=false;searching=true;val requestedSource=source
                                vm.lookupLyrics(source,refresh=true){result->if(latestSource==requestedSource){searching=false;if(result.has("error"))vm.showNotice("Buscar letra online",result.optString("error"));alternatives=result.optJSONArray("candidates")?.let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}}.orEmpty();if(alternatives.isEmpty())applyLyrics(result)}}
                            })
                            DropdownMenuItem(text={UiText("Escolher letra")},enabled=source.isNotBlank(),onClick={menu=false;picker.launch(arrayOf("*/*"))})
                        }
                    }
                }
                Column(Modifier.fillMaxWidth()) {
                    RoundSlider(dragged ?: seconds.toFloat().coerceIn(0f,duration.toFloat().coerceAtLeast(1f)),{dragged=it},valueRange=0f..duration.toFloat().coerceAtLeast(1f),onValueChangeFinished={dragged?.let {seconds=it.toDouble();seek(seconds)};dragged=null},enabled=duration>0,slim=true,modifier=Modifier.fillMaxWidth().a11yLabel("Posição na música"))
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                        UiText(mediaClock((dragged?.toDouble() ?: seconds).toLong()),style=MaterialTheme.typography.labelSmall)
                        UiText(mediaClock(duration.toLong()),style=MaterialTheme.typography.labelSmall)
                    }
                }
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.Center) {
                    FilledIconButton(onClick=toggle,enabled=source.isNotBlank(),modifier=Modifier.size(80.dp).testTag("lyrics-play-pause"),shape=CircleShape) {
                        OndaIcon(if(isPlaying())"pause" else "play",if(isPlaying())"Pausar" else "Reproduzir",Modifier.size(38.dp))
                    }
                }
            }
        }
    }
    if(alternatives.isNotEmpty())AlertDialog(onDismissRequest={alternatives=emptyList()},title={UiText("Buscar letra online")},text={
        LazyColumn {items(alternatives.size) {i->val item=alternatives[i];TextButton(onClick={applyLyrics(item);alternatives=emptyList()}){Text(listOf(item.optString("title"),item.optString("artist"),item.optString("album")).filter {it.isNotBlank()}.joinToString(" · "))}}}
    },confirmButton={TextButton(onClick={alternatives=emptyList()}){UiText("Cancelar")}})

}
