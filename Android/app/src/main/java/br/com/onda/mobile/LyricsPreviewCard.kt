package br.com.onda.mobile

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable internal fun LyricsPreviewCard(vm:OndaViewModel,source:String,title:String,artist:String,position:Double,duration:Double,
    playing:Boolean,seek:(Double)->Unit,toggle:()->Unit) {
    val (lyricsBackground,lyricsInk)=rememberLyricsColors(vm,source)
    val cache by vm.lyricsCache.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val lines=cache[source].orEmpty()
    val active=lyricActiveIndex(lines,position)
    var openRequest by remember(source) {mutableIntStateOf(0)}
    LaunchedEffect(source){vm.lookupLyrics(source)}
    Surface(Modifier.fillMaxWidth().testTag("lyrics-preview-card").clickable {openRequest++},shape=RoundedCornerShape(20.dp),color=lyricsBackground,contentColor=lyricsInk) {
        Column(Modifier.padding(20.dp),verticalArrangement=Arrangement.spacedBy(20.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                UiText("Letra",Modifier.weight(1f),style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
                IconButton(onClick={openRequest++}){OndaIcon("expand","Expandir letra",Modifier.size(24.dp))}
            }
            if(lines.isEmpty())UiText("Letra não encontrada para esta gravação. Toque para buscar ou escolher uma letra.",style=MaterialTheme.typography.bodyLarge)
            else lines.drop(active.coerceAtLeast(0)).take(4).forEachIndexed {offset,line->
                Text(lyricPlainText(line.second),Modifier.fillMaxWidth().lyricAnimation(active to offset,settings.optString("lyrics_animation","Suave")),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold,color=lyricsInk.copy(alpha=if(active>=0&&offset==0)1f else .74f))
            }
        }
    }
    LyricsButton(vm,source,{position},duration,seek,toggle,isPlaying={playing},title=title,artist=artist,showButton=false,openRequest=openRequest)
}
