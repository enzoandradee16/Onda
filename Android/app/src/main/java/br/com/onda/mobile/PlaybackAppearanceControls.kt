package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt
import org.json.JSONObject

@Composable internal fun PlaybackMainCardSizeControl(settings: JSONObject) {
    var open by remember { mutableStateOf(false) }
    val size = settings.optString("playback_card_size", "Padrão")
    Box {
        TextButton(
            onClick = { open = true },
            modifier = Modifier.testTag("playback-main-card-size")
                .a11yLabel(translateUi("Tamanho do card principal") + ": " + translateUi(size))
        ) {
            OndaIcon("album", modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(4.dp))
            Text(translateUi(size) + " ▾", style = MaterialTheme.typography.labelSmall)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            listOf("Muito pequeno", "Pequeno", "Padrão", "Grande").forEach { choice ->
                DropdownMenuItem(text = { UiText(choice) }, onClick = {
                    OndaStore.saveSettings(JSONObject(settings.toString()).put("playback_card_size", choice))
                    open = false
                })
            }
        }
    }
}

@Composable internal fun PlaybackToneControl(value: Int, changed: (Int) -> Unit) {
    var draft by remember(value) { mutableFloatStateOf(value.toFloat()) }
    val number = draft.roundToInt()
    val label = translateUi("Tom") + " · " + (if (number > 0) "+" else "") + number + " st"
    Column {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(label, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
            TextButton(enabled = number != 0, onClick = { draft = 0f; changed(0) }) {
                UiText("Restaurar tom")
            }
        }
        RoundSlider(
            draft, { draft = it.roundToInt().toFloat() }, valueRange = -12f..12f,
            onValueChangeFinished = {
                val committed = draft.roundToInt()
                if (committed != value) changed(committed)
            }, slim = true,
            modifier = Modifier.fillMaxWidth().height(36.dp).testTag("unified-effects-pitch").a11yLabel(label)
        )
        UiText("Altera o tom sem mudar a velocidade.", style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
