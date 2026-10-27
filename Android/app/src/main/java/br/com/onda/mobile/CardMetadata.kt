package br.com.onda.mobile

import androidx.compose.runtime.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.text.style.TextOverflow
import org.json.JSONObject
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.*

internal fun Modifier.onSecondaryClick(key:Any,onClick:()->Unit):Modifier=pointerInput(key) {
    awaitPointerEventScope {while(true){val event=awaitPointerEvent();if(event.type==PointerEventType.Press && event.buttons.isSecondaryPressed){onClick();event.changes.forEach {it.consume()}}}}
}

internal const val PLAYBACK_INPUT_HINT="Música, artista ou link de música, álbum ou playlist"

@Composable internal fun rememberCardMetadata(record:JSONObject,vm:OndaViewModel?):JSONObject {
    val value by produceState(record,record,vm) {
        if(vm!=null && (!record.cleanString("cover_url").isNotBlank() || !record.cleanString("release_date").isNotBlank()))value=vm.completeCard(record)
    }
    return value
}
@Composable internal fun ReleaseDateLabel(record:JSONObject) {
    val date=record.cleanString("release_date")
    if(date.isNotBlank())UiText("${translateUi("Data de lançamento")}: ${displayReleaseDate(date)}",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1,overflow=TextOverflow.Ellipsis)
}

internal fun openRecordLink(record:JSONObject) {
    val uri=android.net.Uri.parse(record.cleanString("source_url"))
    if(uri.scheme in listOf("http","https"))runCatching {OndaStore.context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,uri).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))}
}
internal fun copyRecordLink(record:JSONObject) {
    val clipboard=OndaStore.context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
    clipboard.setPrimaryClip(android.content.ClipData.newPlainText("ONDA",record.cleanString("source_url")))
}
