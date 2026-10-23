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
    val cover=remember(encoded){if(encoded.isBlank())null else runCatching {Base64.decode(encoded,Base64.DEFAULT)}.getOrNull()}
    Surface(modifier.clip(RoundedCornerShape(12.dp)),color=MaterialTheme.colorScheme.surfaceVariant,shape=RoundedCornerShape(12.dp)) {
        if(cover!=null)AsyncImage(cover,translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Fit)
        else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(32.dp))}
    }
}

@Composable internal fun EffectsTrackInformation(info:JSONObject,source:String) {
    val record=info.optJSONObject("record") ?: JSONObject()
    ToolCard(Modifier.testTag("effects-track-information")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
            EffectsArtwork(info,Modifier.size(96.dp))
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
                Text(record.optString("title").ifBlank {importedAudioName(source)},style=MaterialTheme.typography.titleMedium,maxLines=2)
                Text(record.stringList("artists"),style=MaterialTheme.typography.bodyMedium)
                Text(record.optString("album"),style=MaterialTheme.typography.bodySmall)
                Text(mediaClock(info.optDouble("duration").toLong()),style=MaterialTheme.typography.labelMedium)
            }
        }
    }
}

@Composable internal fun EffectsQueuePanel(vm:OndaViewModel,source:String,onPlay:(Int)->Unit) {
    val queue by vm.effectsPlaylist.collectAsStateWithLifecycle()
    val infos by vm.effectsInfo.collectAsStateWithLifecycle()
    ToolCard(Modifier.fillMaxHeight().testTag("effects-queue-panel")) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){UiText("Fila de reprodução",Modifier.weight(1f));TextButton(onClick=vm::clearEffectsQueue,enabled=queue.isNotEmpty()){UiText("Limpar")}}
            LazyColumn(Modifier.fillMaxWidth().weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
                if(queue.isEmpty())item {UiText("Adicione arquivos ou músicas dos resultados.")}
                itemsIndexed(queue,key={_,path->path}) {index,path->
                    val info=infos[path]
                    val record=info?.optJSONObject("record")
                    Column(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                            EffectsArtwork(info ?: JSONObject(),Modifier.size(56.dp))
                            Column(Modifier.weight(1f)) {
                                Text(record?.optString("title")?.ifBlank {importedAudioName(path)} ?: importedAudioName(path),maxLines=2,color=if(path==source)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)
                                Text(record?.stringList("artists").orEmpty(),style=MaterialTheme.typography.bodySmall)
                                Text(mediaClock((info?.optDouble("duration",0.0) ?: 0.0).toLong()),style=MaterialTheme.typography.labelSmall)
                                if(info?.has("error")==true)Text(info.optString("error"),color=MaterialTheme.colorScheme.error,style=MaterialTheme.typography.bodySmall)
                            }
                        }
                        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(LayoutSpacing.details),verticalAlignment=Alignment.CenterVertically) {
                            TextButton(onClick={onPlay(index)},enabled=info!=null&&!info.has("error")){UiText("Tocar")}
                            IconButton(onClick={vm.moveEffectsTrack(index,-1)},enabled=index>0){OndaIcon("up","Mover para cima",Modifier.size(22.dp))}
                            IconButton(onClick={vm.moveEffectsTrack(index,1)},enabled=index+1<queue.size){OndaIcon("down","Mover para baixo",Modifier.size(22.dp))}
                            IconButton(onClick={vm.removeEffectsTrack(index)}){OndaIcon("close","Remover da fila",Modifier.size(22.dp))}
                        }
                    }
                }
            }
        }
}

@Composable internal fun EffectsQueueDrawer(vm:OndaViewModel) {
    val open by vm.effectsQueueOpen.collectAsStateWithLifecycle()
    val source by vm.effectsSource.collectAsStateWithLifecycle()
    if(open)Dialog(onDismissRequest={vm.effectsQueueOpen.value=false},properties=DialogProperties(usePlatformDefaultWidth=false)) {
        Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.scrim.copy(alpha=.35f))) {
            Box(Modifier.fillMaxSize().clickable {vm.effectsQueueOpen.value=false})
            Surface(Modifier.align(Alignment.CenterEnd).fillMaxHeight().fillMaxWidth(.94f).widthIn(max=480.dp),color=MaterialTheme.colorScheme.surface) {
                Column {
                    TextButton(onClick={vm.effectsQueueOpen.value=false},modifier=Modifier.align(Alignment.End)){UiText("Fechar fila")}
                    Box(Modifier.weight(1f)){EffectsQueuePanel(vm,source,vm::playEffectsQueueTrack)}
                }
            }
        }
    }
}
