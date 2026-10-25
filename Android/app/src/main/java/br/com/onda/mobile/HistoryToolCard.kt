package br.com.onda.mobile

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.input.pointer.*
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

internal fun historyKind(mode:String,name:String=""):String {
    val audio=setOf("mp3","m4a","aac","flac","wav","ogg","oga","opus","wma","aiff","aif","alac","m4b")
    val images=setOf("jpg","jpeg","png","webp","svg","gif","avif","heic","heif","bmp","tif","tiff")
    val video=setOf("mp4","mkv","webm","mov","m4v","avi","flv","wmv","mpg","mpeg","3gp","ts")
    val extension=name.substringAfterLast('.',"").lowercase(java.util.Locale.ROOT)
    val kind=if(extension in audio+images+video)extension else mode.lowercase(java.util.Locale.ROOT).removePrefix(".")
    return when(kind){in audio+setOf("original","audio")->"Áudio";in images+setOf("photos","image","images")->"Imagens";else->"Vídeo"}
}
internal fun historyDay(time:Long,now:Long=System.currentTimeMillis()):String {
    if(time<=0)return "Anteriores"
    val zone=java.time.ZoneId.systemDefault()
    val date=java.time.Instant.ofEpochMilli(time).atZone(zone).toLocalDate()
    val today=java.time.Instant.ofEpochMilli(now).atZone(zone).toLocalDate()
    return when(date){today->"Hoje";today.minusDays(1)->"Ontem";else->date.format(java.time.format.DateTimeFormatter.ofPattern("dd/MM/yyyy"))}
}

@Composable internal fun HistoryToolCard(item:HistoryItem,settings:JSONObject,vm:OndaViewModel,selectionMode:Boolean,selected:Boolean,onSelect:(Boolean)->Unit,onEdit:(HistoryItem)->Unit) {
    val context=LocalContext.current
    val revision by historyDetailsRevision.collectAsState()
    val details by produceState<HistoryDetails?>(null,item.uri,item.size,revision){value=withContext(Dispatchers.IO){cachedHistoryDetails(context,item,revision)}}
    var menu by remember {mutableStateOf(false)}
    val side=when(settings.optString("history_card_size","Grande")){"Pequeno"->56.dp;"Médio"->76.dp;else->96.dp}
    ToolCard(Modifier.testTag("history-card-${item.id}").pointerInput(item.id) {
        awaitPointerEventScope {while(true){val event=awaitPointerEvent();if(event.type==PointerEventType.Press && event.buttons.isSecondaryPressed){menu=true;event.changes.forEach {it.consume()}}}}
    }.then(if(selectionMode && historyKind(item.mode,item.title)=="Áudio")Modifier.toggleable(selected,role=androidx.compose.ui.semantics.Role.Checkbox,onValueChange=onSelect) else Modifier)) {
        Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            if(selectionMode && historyKind(item.mode,item.title)=="Áudio")Checkbox(selected,onSelect)
            Surface(Modifier.size(side),shape=RoundedCornerShape(12.dp),color=MaterialTheme.colorScheme.surfaceVariant) {
                if(details?.cover!=null)Image(details!!.cover!!.asImageBitmap(),translateUi("Capa do álbum"),Modifier.fillMaxSize(),contentScale=ContentScale.Crop)
                else if(historyKind(item.mode,item.title)=="Imagens")coil.compose.AsyncImage(item.uri,translateUi("Prévia da imagem"),Modifier.fillMaxSize(),contentScale=ContentScale.Crop)
                else Box(contentAlignment=Alignment.Center){OndaIcon(if(historyKind(item.mode,item.title)=="Áudio")"album" else "play",modifier=Modifier.size(30.dp))}
            }
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                Text(songCardTitle(details?.title?.ifBlank {item.title} ?: item.title,details?.artist.orEmpty()),style=MaterialTheme.typography.titleSmall,fontWeight=FontWeight.SemiBold,maxLines=2,overflow=TextOverflow.Ellipsis)
                details?.artist?.takeIf {it.isNotBlank()}?.let {Text(it,style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=2,overflow=TextOverflow.Ellipsis)}
                MetadataPlatformBadge(JSONObject().put("platform",item.metadataPlatform),source=item.source,imageMedia=historyKind(item.mode,item.title)=="Imagens")
                UiText("${item.mode.uppercase()} · Concluído",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Box {
                IconButton(onClick={menu=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
                DropdownMenu(menu,{menu=false}) {
                    fun action(block:()->Unit){menu=false;block()}
                    DropdownMenuItem(text={UiText("Abrir arquivo")},onClick={action {runCatching {OndaStore.open(item.uri,item.mode)}.onFailure {vm.showNotice("Abrir arquivo","Não foi possível abrir este arquivo.")}}})
                    DropdownMenuItem(text={UiText("Abrir pasta")},modifier=Modifier.testTag("open-history-folder-${item.id}"),onClick={action {vm.openHistoryFolder(item.uri)}})
                    DropdownMenuItem(text={UiText("Compartilhar")},onClick={action {OndaStore.share(item.uri,item.title)}})
                    if(historyKind(item.mode,item.title)=="Áudio")DropdownMenuItem(text={UiText("Editar metadados")},onClick={action {onEdit(item)}})
                    if(historySupportsEffects(item))DropdownMenuItem(text={UiText("Usar nos efeitos")},onClick={action {vm.useInEffects(item.uri)}})
                    if(historyOrigin(item.source).isNotBlank())DropdownMenuItem(text={UiText("Abrir origem")},onClick={action {runCatching {context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(historyOrigin(item.source))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}.onFailure {vm.showNotice("Abrir origem","Não foi possível abrir a origem.")}}})
                    HorizontalDivider()
                    DropdownMenuItem(text={UiText("Remover")},modifier=Modifier.testTag("remove-history-${item.id}"),onClick={action {OndaStore.removeHistory(item.id)}})
                }
            }
        }
        TextButton(onClick={OndaStore.removeHistory(item.id)},modifier=Modifier.align(Alignment.End).testTag("remove-history-button-${item.id}")){UiText("Remover")}
        if(settings.optString("history_view")=="Completa") {
            UiText("%.1f MB".format(item.size/1048576.0),style=MaterialTheme.typography.bodySmall)
            details?.lines?.forEach {line->val split=line.indexOf(": ");UiText(if(split>=0)translateUi(line.substring(0,split))+line.substring(split) else line,style=MaterialTheme.typography.bodySmall)}
        }
    }
}
