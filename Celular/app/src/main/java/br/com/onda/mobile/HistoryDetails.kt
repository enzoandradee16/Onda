package br.com.onda.mobile

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

internal data class HistoryDetails(val title:String="",val artist:String="",val lines:List<String> = emptyList(),val cover:Bitmap?=null)

internal fun readHistoryDetails(context:Context,uri:String):HistoryDetails {
    val reader=MediaMetadataRetriever()
    return try {
        reader.setDataSource(context,Uri.parse(uri))
        fun field(key:Int)=reader.extractMetadata(key).orEmpty().trim()
        val lines=mutableListOf<String>()
        for((key,label) in listOf(MediaMetadataRetriever.METADATA_KEY_ALBUM to "Álbum / single",
                MediaMetadataRetriever.METADATA_KEY_ALBUMARTIST to "Artista do álbum",
                MediaMetadataRetriever.METADATA_KEY_YEAR to "Lançamento",
                MediaMetadataRetriever.METADATA_KEY_GENRE to "Gênero",
                MediaMetadataRetriever.METADATA_KEY_CD_TRACK_NUMBER to "Faixa",
                MediaMetadataRetriever.METADATA_KEY_DISC_NUMBER to "Disco")) {
            field(key).takeIf {it.isNotBlank()}?.let {lines.add("$label: $it")}
        }
        field(MediaMetadataRetriever.METADATA_KEY_DURATION).toLongOrNull()?.let {ms->
            val seconds=ms/1000;lines.add("Duração: ${seconds/60}:${(seconds%60).toString().padStart(2,'0')}")
        }
        field(MediaMetadataRetriever.METADATA_KEY_BITRATE).toLongOrNull()?.let {lines.add("Qualidade: ${it/1000} kbps")}
        val cover=reader.embeddedPicture?.let {bytes->
            val options=BitmapFactory.Options().apply {inJustDecodeBounds=true}
            BitmapFactory.decodeByteArray(bytes,0,bytes.size,options)
            options.inSampleSize=1
            while(maxOf(options.outWidth,options.outHeight)/options.inSampleSize>320)options.inSampleSize*=2
            options.inJustDecodeBounds=false
            BitmapFactory.decodeByteArray(bytes,0,bytes.size,options)
        }
        HistoryDetails(field(MediaMetadataRetriever.METADATA_KEY_TITLE),field(MediaMetadataRetriever.METADATA_KEY_ARTIST),lines,cover)
    } catch(_:Exception) {
        HistoryDetails(lines=listOf("Metadados indisponíveis ou arquivo movido/removido."))
    } finally {runCatching {reader.release()}}
}

// Bounded previews avoid reopening audio files when scrolling back.
private val historyDetailsCache=android.util.LruCache<String,HistoryDetails>(24)
internal val historyDetailsRevision=kotlinx.coroutines.flow.MutableStateFlow(0L)
internal fun invalidateHistoryDetails() {
    historyDetailsCache.evictAll()
    historyDetailsRevision.value+=1
}
internal fun cachedHistoryDetails(context:Context,item:HistoryItem,revision:Long):HistoryDetails {
    val key="${item.uri}|${item.size}|$revision"
    return historyDetailsCache.get(key) ?: readHistoryDetails(context,item.uri).also {historyDetailsCache.put(key,it)}
}

@Composable internal fun CompleteHistoryInformation(item:HistoryItem,size:String="Grande") {
    val side=when(size) {"Pequeno"->56.dp;"Médio"->76.dp;else->96.dp}
    val small=size=="Pequeno"
    val context=LocalContext.current
    val revision by historyDetailsRevision.collectAsState()
    val details by produceState<HistoryDetails?>(null,item.uri,item.size,revision) {
        value=withContext(Dispatchers.IO) {cachedHistoryDetails(context,item,revision)}
    }
    Row(Modifier.fillMaxWidth().padding(bottom=if(small) 6.dp else 12.dp).testTag("history-complete-${item.id}"),horizontalArrangement=Arrangement.spacedBy(if(small) 8.dp else 12.dp)) {
        val cover=details?.cover
        if(cover!=null) Image(cover.asImageBitmap(),translateUi("Capa do álbum",LocalUiLanguage.current),Modifier.size(side),contentScale=ContentScale.Fit)
        else Surface(Modifier.size(side),color=MaterialTheme.colorScheme.surfaceVariant) {
            Box(contentAlignment=androidx.compose.ui.Alignment.Center) {UiText("♫",style=MaterialTheme.typography.headlineLarge)}
        }
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.details)) {
            Text(details?.title?.ifBlank {item.title} ?: item.title,style=if(small) MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold)
            Text(details?.artist?.takeIf {it.isNotBlank()} ?: translateUi(if(details==null) "Carregando informações…" else "Artista não informado",LocalUiLanguage.current),style=if(small) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyLarge)
            val translatedLines=details?.lines?.map {line->
                val split=line.indexOf(": ")
                if(split>=0) translateUi(line.substring(0,split),LocalUiLanguage.current)+line.substring(split) else translateUi(line,LocalUiLanguage.current)
            }
            if(small) translatedLines?.takeIf {it.isNotEmpty()}?.let {UiText(it.joinToString(" · "),style=MaterialTheme.typography.bodySmall)}
            else translatedLines?.forEach {UiText(it,style=MaterialTheme.typography.bodySmall)}
        }
    }
}
