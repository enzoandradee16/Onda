package br.com.onda.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import org.json.JSONObject

/** Compact single-choice metadata preview; the full card is the touch target. */
@Composable internal fun MetadataChoiceCard(candidate:JSONObject,selected:Boolean,onSelect:()->Unit) {
    val colors=MaterialTheme.colorScheme
    val artwork=candidate.cleanString("cover_url").ifBlank {candidate.cleanString("cover")}
    val image=remember(artwork) {
        if(artwork.startsWith("data:image/"))runCatching {android.util.Base64.decode(artwork.substringAfter(','),android.util.Base64.DEFAULT)}.getOrNull() else artwork
    }
    val duration=if(candidate.optLong("duration_ms")>0)candidate.optLong("duration_ms")/1000 else candidate.optDouble("duration",0.0).toLong()
    val details=listOf(
        candidate.cleanString("release_date").takeIf {it.isNotBlank()}?.let(::displayReleaseDate).orEmpty(),
        candidate.cleanString("genre"),
        candidate.cleanString("track_number").takeIf {it.isNotBlank()}?.let {translateUi("Faixa",LocalUiLanguage.current)+" "+it}.orEmpty(),
        candidate.cleanString("disc_number").takeIf {it.isNotBlank()}?.let {translateUi("Disco",LocalUiLanguage.current)+" "+it}.orEmpty()
    ).filter {it.isNotBlank()}.joinToString(" · ")
    Surface(modifier=Modifier.fillMaxWidth().selectable(selected=selected,role=Role.RadioButton,onClick=onSelect),
        shape=RoundedCornerShape(14.dp),
        color=if(selected)colors.primary.copy(alpha=.08f) else colors.surfaceContainerLow,
        border=BorderStroke(1.dp,if(selected)colors.primary else colors.outlineVariant)) {
        Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Row(horizontalArrangement=Arrangement.spacedBy(12.dp),verticalAlignment=Alignment.Top) {
                Surface(Modifier.size(64.dp),shape=RoundedCornerShape(8.dp),color=colors.surfaceVariant) {
                    if(artwork.isNotBlank())AsyncImage(image,translateUi("Capa do álbum",LocalUiLanguage.current),Modifier.fillMaxSize(),contentScale=androidx.compose.ui.layout.ContentScale.Fit)
                    else Box(contentAlignment=Alignment.Center){OndaIcon("album",modifier=Modifier.size(28.dp))}
                }
                Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(3.dp)) {
                    Text(candidate.cleanString("title"),style=MaterialTheme.typography.bodyLarge,fontWeight=FontWeight.SemiBold)
                    Text(candidate.stringList("artists"),style=MaterialTheme.typography.bodyMedium,color=colors.onSurfaceVariant)
                    if(candidate.cleanString("album").isNotBlank())Text(candidate.cleanString("album"),style=MaterialTheme.typography.bodySmall,color=colors.onSurfaceVariant)
                }
                RadioButton(selected=selected,onClick=null,modifier=Modifier.size(24.dp))
            }
            if(details.isNotBlank())Text(details,style=MaterialTheme.typography.bodySmall,color=colors.onSurfaceVariant)
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
                Text(candidate.cleanString("platform"),modifier=Modifier.weight(1f),style=MaterialTheme.typography.labelSmall,color=colors.primary)
                if(duration>0)Text(mediaClock(duration),style=MaterialTheme.typography.labelSmall,color=colors.onSurfaceVariant)
            }
            if(candidate.cleanString("isrc").isNotBlank())Text("ISRC · "+candidate.cleanString("isrc"),style=MaterialTheme.typography.labelSmall,color=colors.onSurfaceVariant)
            if(candidate.optBoolean("manual_review"))Text(candidate.optJSONArray("match_reasons")?.let {a->(0 until a.length()).joinToString(" "){a.optString(it)}}.orEmpty(),style=MaterialTheme.typography.bodySmall,color=colors.onSurfaceVariant)
        }
    }
}
