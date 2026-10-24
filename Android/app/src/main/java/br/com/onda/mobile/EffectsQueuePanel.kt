package br.com.onda.mobile

import android.util.Base64
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import org.json.JSONObject

@Composable internal fun EffectsArtwork(info:JSONObject,modifier:Modifier=Modifier) {
    val encoded=info.optString("cover")
    val coverUrl=info.optJSONObject("record")?.optString("cover_url").orEmpty()
    val cover=remember(encoded,coverUrl){if(encoded.isBlank())coverUrl.takeIf {it.isNotBlank()} else runCatching {Base64.decode(encoded,Base64.DEFAULT)}.getOrNull()}
    Surface(modifier.clip(RoundedCornerShape(12.dp)),color=MaterialTheme.colorScheme.surfaceVariant,shape=RoundedCornerShape(12.dp)) {
        if(cover!=null)AsyncImage(cover,translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Fit)
        else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(32.dp))}
    }
}

@Composable internal fun EffectsTrackInformation(info:JSONObject,source:String,action:@Composable ()->Unit={}) {
    val record=info.optJSONObject("record") ?: JSONObject()
    ToolCard(Modifier.testTag("effects-track-information")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
            EffectsArtwork(info,Modifier.size(96.dp))
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
                Text(record.optString("title").ifBlank {importedAudioName(source)},style=MaterialTheme.typography.titleMedium,maxLines=2)
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodyMedium)
                Text(record.optString("album"),style=MaterialTheme.typography.bodySmall)
                Text(mediaClock(info.optDouble("duration").toLong()),style=MaterialTheme.typography.labelMedium)
                action()
            }
        }
    }
}


@Composable internal fun PlaybackQueueRow(record:JSONObject,cover:String,duration:Long,current:Boolean,editing:Boolean,play:()->Unit,up:()->Unit,down:()->Unit,remove:()->Unit,canUp:Boolean,canDown:Boolean) {
    Column(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().clickable(onClick=play).padding(vertical=10.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            EffectsArtwork(JSONObject().put("record",record).put("cover",cover),Modifier.size(48.dp))
            Column(Modifier.weight(1f)) {
                Text(record.optString("title"),maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis,color=if(current)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            }
            if(duration>0)Text(mediaClock(duration),style=MaterialTheme.typography.labelSmall)
            IconButton(onClick=play){OndaIcon("play",if(current)"Reproduzir novamente" else "Reproduzir",Modifier.size(22.dp))}
        }
        if(editing)Row {
            IconButton(onClick=up,enabled=canUp){OndaIcon("up","Mover para cima",Modifier.size(22.dp))}
            IconButton(onClick=down,enabled=canDown){OndaIcon("down","Mover para baixo",Modifier.size(22.dp))}
            IconButton(onClick=remove){OndaIcon("close","Remover da fila",Modifier.size(22.dp))}
        }
    }
}
@Composable internal fun EffectsQueuePanel(vm:OndaViewModel,source:String,onPlay:(Int)->Unit) {
    val queue by vm.effectsPlaylist.collectAsStateWithLifecycle()
    val infos by vm.effectsInfo.collectAsStateWithLifecycle()
    var editing by remember {mutableStateOf(false)}
    Column(Modifier.fillMaxSize().padding(horizontal=LayoutSpacing.inset).testTag("effects-queue-panel")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText("Fila",Modifier.weight(1f),style=MaterialTheme.typography.titleLarge);TextButton(onClick={editing=!editing}){UiText(if(editing)"Pronto" else "Editar")}}
        if(editing)TextButton(onClick=vm::clearEffectsQueue){UiText("Limpar fila")}
        val active=queue.indexOf(source)
        LazyColumn(Modifier.weight(1f)) {
            if(queue.isEmpty())item {UiText("Adicione arquivos ou músicas dos resultados.")}
            itemsIndexed(queue,key={_,path->path}) {index,path->
                if(index==0&&active>0)UiText("Já tocadas",style=MaterialTheme.typography.labelLarge)
                if(index==active)UiText("Tocando agora",style=MaterialTheme.typography.labelLarge)
                if(index==active+1)UiText("A seguir",style=MaterialTheme.typography.labelLarge)
                val info=infos[path] ?: JSONObject()
                val record=info.optJSONObject("record") ?: JSONObject().put("title",importedAudioName(path))
                PlaybackQueueRow(record,info.optString("cover"),info.optDouble("duration",0.0).toLong(),path==source,editing,{onPlay(index)},{vm.moveEffectsTrack(index,-1)},{vm.moveEffectsTrack(index,1)},{vm.removeEffectsTrack(index)},index>0,index+1<queue.size)
                if(info.has("error"))TextButton(onClick={vm.loadEffectsInfo(listOf(path),retryErrors=true)}){UiText("Tentar novamente")}
            }
        }
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun EffectsQueueDrawer(vm:OndaViewModel) {
    val open by vm.effectsQueueOpen.collectAsStateWithLifecycle()
    val source by vm.effectsSource.collectAsStateWithLifecycle()
    if(open)ModalBottomSheet(onDismissRequest={vm.effectsQueueOpen.value=false},sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true)) {
        Box(Modifier.fillMaxWidth().fillMaxHeight(.85f)){EffectsQueuePanel(vm,source,vm::playEffectsQueueTrack)}
    }
}

@Composable internal fun SearchTrackInformation(record:JSONObject) {
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        EffectsArtwork(JSONObject().put("record",record),Modifier.size(56.dp))
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
            Text(record.optString("title"),maxLines=2,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            Text(record.stringList("artists"),style=MaterialTheme.typography.bodySmall,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
            Text(record.optString("album"),style=MaterialTheme.typography.bodySmall,maxLines=1,overflow=androidx.compose.ui.text.style.TextOverflow.Ellipsis)
        }
    }
}
