package br.com.onda.mobile

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import org.json.JSONObject

internal fun metadataPlatform(record:JSONObject?):String = when(val name=record?.cleanString("platform")?.trim()?.lowercase().orEmpty()) {
    "apple / itunes","applemusic","itunes","apple","apple music"->"apple_music"
    "youtube music"->"youtube"
    else->name
}
@Composable internal fun MetadataPlatformBadge(record:JSONObject?,modifier:Modifier=Modifier) {
    val key=metadataPlatform(record)
    val entry=when(key) {
        "spotify"->R.drawable.metadata_spotify to "Spotify"
        "deezer"->R.drawable.metadata_deezer to "Deezer"
        "apple_music"->R.drawable.metadata_apple_music to "Apple Music"
        "musicbrainz"->R.drawable.metadata_musicbrainz to "MusicBrainz"
        "youtube"->R.drawable.metadata_youtube to "YouTube"
        "tidal"->R.drawable.metadata_tidal to "TIDAL"
        "qobuz"->R.drawable.metadata_qobuz to "Qobuz"
        "bandcamp"->R.drawable.metadata_bandcamp to "Bandcamp"
        else->null
    }
    if(entry!=null) Row(modifier,verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(5.dp)) {
        Image(painterResource(entry.first),translateUi("Origem dos metadados")+": "+entry.second,Modifier.size(18.dp),colorFilter=ColorFilter.tint(LocalContentColor.current))
        Text(entry.second,style=MaterialTheme.typography.labelSmall)
    }
}
