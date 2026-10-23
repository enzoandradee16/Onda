package br.com.onda.mobile

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private data class LicenseNotice(val title: String, val text: String)

@Composable fun LicensesWindow(onDismiss: () -> Unit) {
    val context = LocalContext.current
    var summary by remember { mutableStateOf("Carregando licenças…") }
    var notices by remember { mutableStateOf(emptyList<LicenseNotice>()) }
    var selected by remember { mutableStateOf<Int?>(null) }
    LaunchedEffect(context) {
        val parsed = withContext(Dispatchers.IO) {
            val text = context.assets.open("open-source-notices.txt").bufferedReader().use { it.readText() }
            val headers = Regex("(?m)^===== (.+) =====$").findAll(text).toList()
            text.substring(0, headers.firstOrNull()?.range?.first ?: text.length) to
                headers.mapIndexed { index, match ->
                    val end = headers.getOrNull(index + 1)?.range?.first ?: text.length
                    LicenseNotice(match.groupValues[1], text.substring(match.range.last + 1, end).trim())
                }
        }
        summary = parsed.first
        notices = parsed.second
    }
    val notice = selected?.let { notices.getOrNull(it) }
    fun closePage() { if (selected != null) selected = null else onDismiss() }
    AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={closePage()}, title={UiText(notice?.title ?: "Licenças e fontes")},
        text={
            if (notice == null) LazyColumn(Modifier.heightIn(max=420.dp)) {
                item {UiText(summary, style=MaterialTheme.typography.bodySmall)}
                itemsIndexed(notices) { index, entry ->
                    TextButton(onClick={selected=index}, modifier=Modifier.fillMaxWidth()) {
                        UiText(entry.title, style=MaterialTheme.typography.bodySmall)
                    }
                }
            } else key(selected) {
                val paragraphs = remember(notice) { notice.text.split(Regex("\\n\\s*\\n")) }
                LazyColumn(Modifier.heightIn(max=420.dp).testTag("license-details")) {
                    items(paragraphs) { paragraph -> UiText(paragraph, style=MaterialTheme.typography.bodySmall) }
                }
            }
        },
        confirmButton={TextButton(onClick=onDismiss) {UiText("Fechar")}},
        dismissButton={
            if (notice != null) TextButton(onClick={selected=null}) {UiText("Voltar")}
            else TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse("https://github.com/enzoandradee16/Onda/releases")))}) {UiText("Abrir fontes")}
        })
}
