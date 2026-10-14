package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage

@Composable internal fun QueueTrackInformation(item:DownloadItem,size:String,modifier:Modifier=Modifier) {
    val info=item.config.optJSONObject("queue_info") ?: item.config.optJSONObject("catalog_record")
    val small=size=="Pequeno"
    val side=if(small)56.dp else if(size=="Médio")76.dp else 96.dp
    Row(modifier,horizontalArrangement=Arrangement.spacedBy(10.dp)) {
        val cover=info?.cleanString("cover_url").orEmpty()
        if(cover.isNotBlank()) AsyncImage(model=cover,contentDescription=translateUi("Capa do álbum"),modifier=Modifier.size(side).testTag("queue-cover-${item.id}"),contentScale=androidx.compose.ui.layout.ContentScale.Fit)
        else Box(Modifier.size(side)) {Text("♫",style=MaterialTheme.typography.headlineMedium)}
        Column(Modifier.weight(1f)) {
            Text(item.title,maxLines=if(small)2 else 3,overflow=TextOverflow.Ellipsis,fontWeight=FontWeight.Bold,style=if(small)MaterialTheme.typography.bodyMedium else MaterialTheme.typography.titleSmall)
            val artists=info?.optJSONArray("artists")
            val artist=if(artists==null)"" else (0 until artists.length()).map {artists.optString(it)}.filter {it.isNotBlank()}.joinToString(", ")
            if(artist.isNotBlank())Text(artist,style=MaterialTheme.typography.bodySmall,maxLines=if(small)1 else 2,overflow=TextOverflow.Ellipsis)
            val album=info?.cleanString("album").orEmpty()
            if(album.isNotBlank())Row {UiText("Álbum / single",style=MaterialTheme.typography.bodySmall);Text(": $album",style=MaterialTheme.typography.bodySmall,maxLines=2,overflow=TextOverflow.Ellipsis)}
            val duration=info?.optLong("duration_ms") ?: 0L
            if(duration>0)Text(mediaClock(duration/1000),style=MaterialTheme.typography.bodySmall)
            for((key,label) in listOf("release_date" to "Lançamento","genre" to "Gênero","track_number" to "Faixa","disc_number" to "Disco")) {
                val value=info?.cleanString(key).orEmpty()
                if(value.isNotBlank())Row {UiText(label,style=MaterialTheme.typography.bodySmall);Text(": $value",style=MaterialTheme.typography.bodySmall,maxLines=1,overflow=TextOverflow.Ellipsis)}
            }
        }
    }
}
