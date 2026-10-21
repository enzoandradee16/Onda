package br.com.onda.mobile

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import android.net.Uri

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
