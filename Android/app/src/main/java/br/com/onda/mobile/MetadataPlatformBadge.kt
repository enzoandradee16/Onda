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
@Composable internal fun MetadataPlatformBadge(record:JSONObject?,modifier:Modifier=Modifier,source:String="",imageMedia:Boolean=false) {
    val identity=identifyPlatform(source.ifBlank {record?.cleanString("source_url").orEmpty()},metadataPlatform(record))
    val key=identity.key
    val entry=when(key) {
        "spotify"->R.drawable.metadata_spotify to "Spotify"
        "deezer"->R.drawable.metadata_deezer to "Deezer"
        "apple_music"->R.drawable.metadata_apple_music to "Apple Music"
        "musicbrainz"->R.drawable.metadata_musicbrainz to "MusicBrainz"
        "youtube"->R.drawable.metadata_youtube to "YouTube"
        "tidal"->R.drawable.metadata_tidal to "TIDAL"
        "qobuz"->R.drawable.metadata_qobuz to "Qobuz"
        "bandcamp"->R.drawable.metadata_bandcamp to "Bandcamp"
        "instagram"->R.drawable.metadata_instagram to identity.label
        "tiktok"->R.drawable.metadata_tiktok to identity.label
        "kwai"->R.drawable.metadata_kwai to identity.label
        "twitter"->R.drawable.metadata_twitter to identity.label
        "facebook"->R.drawable.metadata_facebook to identity.label
        "soundcloud"->R.drawable.metadata_soundcloud to identity.label
        "vimeo"->R.drawable.metadata_vimeo to identity.label
        "dailymotion"->R.drawable.metadata_dailymotion to identity.label
        "twitch"->R.drawable.metadata_twitch to identity.label
        "reddit"->R.drawable.metadata_reddit to identity.label
        "pinterest"->R.drawable.metadata_pinterest to identity.label
        "telegram"->R.drawable.metadata_telegram to identity.label
        "link"->R.drawable.metadata_link to identity.label
        else->null
    }
    if(entry!=null || imageMedia) Row(modifier,verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(5.dp)) {
        if(imageMedia)OndaIcon("image","Imagens",Modifier.size(18.dp))
        if(entry!=null) {
            if(!imageMedia || key!="link")Image(painterResource(entry.first),translateUi("Plataforma")+": "+entry.second,Modifier.size(18.dp),colorFilter=ColorFilter.tint(LocalContentColor.current))
            Text(identity.label,style=MaterialTheme.typography.labelSmall)
        }
    }
}
