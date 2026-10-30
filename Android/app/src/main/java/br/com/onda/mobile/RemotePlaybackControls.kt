package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject

@Composable internal fun RemotePlaybackPage(vm: OndaViewModel) {
    val state by RemotePlaybackRuntime.state.collectAsStateWithLifecycle()
    val effects = state.effects
    val jukebox = state.jukebox
    var devices by remember { mutableStateOf(false) }
    val presets = playbackEffectPresets
    val preset = presets.entries.firstOrNull { it.value.first == effects.speed && it.value.second == effects.reverb }?.key ?: "Personalizado"
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = LayoutSpacing.inset, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            UiText("Reprodução", modifier = Modifier.weight(1f), style = MaterialTheme.typography.headlineMedium)
            IconButton(onClick = vm::openPlaybackQueue) { OndaIcon("queue", "Fila", Modifier.size(24.dp)) }
        }
        PlaybackDeviceButton(onClick = { devices = true }, name = state.deviceName, remote = true)
        if (!state.online) UiText("Computador desconectado")
        RemoteQueueSearch(vm)
        if (state.trackId.isNotBlank()) PlaybackCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                RemoteCover(state, Modifier.size(88.dp))
                Column(Modifier.weight(1f)) {
                    Text(state.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Text(state.artist, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(state.album, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        PlaybackCard(Modifier.testTag("remote-effects-card")) {
            PlaybackSectionToggle("Efeitos", effects.enabled, enabled = state.online) { RemotePlaybackRuntime.effects("enabled", it) }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                UiText("Preset", style = MaterialTheme.typography.bodySmall)
                Box(Modifier.weight(1f)) {
                    Select("", preset, presets.keys.toList()) { name ->
                        if (state.online) {
                            val pair = presets.getValue(name)
                            RemotePlaybackRuntime.command("effects", JSONObject().put("speed", pair.first).put("reverb", pair.second))
                        }
                    }
                }
            }
            RemoteAdjustment("Velocidade", effects.speed.toFloat(), 50f..150f, state.online) { RemotePlaybackRuntime.effects("speed", it.toInt()) }
            RemoteAdjustment("Reverb", effects.reverb.toFloat(), 0f..100f, state.online) { RemotePlaybackRuntime.effects("reverb", it.toInt()) }
            PlaybackSectionToggle("Manter tom", effects.keepPitch, enabled = state.online) { RemotePlaybackRuntime.effects("keep_pitch", it) }
            if (state.effectsPending) LinearProgressIndicator(Modifier.fillMaxWidth())
        }
        PlaybackCard(Modifier.testTag("remote-jukebox-card")) {
            PlaybackSectionToggle("Jukebox infinito", !jukebox.normal, enabled = state.online) { RemotePlaybackRuntime.jukebox("normal", !it) }
            RemoteAdjustment("Variação", jukebox.variation, 0f..100f, state.online && !jukebox.normal) { RemotePlaybackRuntime.jukebox("variation", it) }
            RemoteAdjustment("Transição suave", jukebox.smooth, 0f..100f, state.online && !jukebox.normal) { RemotePlaybackRuntime.jukebox("smooth", it) }
        }
        if (state.notice.isNotBlank()) UiText(state.notice, style = MaterialTheme.typography.bodySmall)
    }
    if (devices) PlaybackDevicesSheet { devices = false }
}

/** Keep touch feedback local; commit once on release instead of rendering effects per pixel. */
@Composable private fun RemoteAdjustment(label: String, value: Float, range: ClosedFloatingPointRange<Float>, enabled: Boolean, commit: (Float) -> Unit) {
    var dragged by remember { mutableStateOf<Float?>(null) }
    Column {
        Text(translateUi(label) + " · ${(dragged ?: value).toInt()}%", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        RoundSlider(dragged ?: value.coerceIn(range), { dragged = it }, valueRange = range, enabled = enabled, slim = true,
            modifier = Modifier.fillMaxWidth().height(36.dp).a11yLabel(label), onValueChangeFinished = { dragged?.let(commit); dragged = null })
    }
}

/** Uses the PC resolver, and sends only result identities back to the PC. */
@Composable internal fun RemoteQueueSearch(vm: OndaViewModel) {
    val state by RemotePlaybackRuntime.state.collectAsStateWithLifecycle()
    var query by rememberSaveable { mutableStateOf("") }
    fun search() {
        if (state.searchBusy) RemotePlaybackRuntime.command("search_cancel")
        else if (query.isNotBlank()) RemotePlaybackRuntime.command("search", query.trim().take(500))
    }
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        OutlinedTextField(query, { query = it }, label = { UiText(PLAYBACK_INPUT_HINT) }, singleLine = true,
            enabled = state.online, keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search), keyboardActions = KeyboardActions(onSearch = { search() }),
            trailingIcon = {
                if (query.isNotEmpty() || state.searchRows.isNotEmpty() || state.searchBusy || state.searchMessage.isNotBlank() || state.searchBatch.isNotBlank()) {
                    IconButton(onClick = { query = ""; RemotePlaybackRuntime.clearSearch() }, modifier = Modifier.testTag("close-remote-queue-search")) {
                        OndaIcon("close", "Fechar pesquisa", Modifier.size(22.dp))
                    }
                }
            },
            modifier = Modifier.fillMaxWidth().testTag("remote-queue-search"))
        TextButton(onClick = ::search, enabled = state.online && (state.searchBusy || query.isNotBlank())) { UiText(if (state.searchBusy) "Cancelar" else "Pesquisar") }
        if (state.searchBusy) LinearProgressIndicator(Modifier.fillMaxWidth())
        if (state.searchMessage.isNotBlank()) UiText(state.searchMessage, style = MaterialTheme.typography.bodySmall)
        if (state.searchBatch.isNotBlank()) TextButton(onClick = { RemotePlaybackRuntime.command("search_add", state.searchBatch) }, enabled = state.online) { UiText("Adicionar todas à fila") }
        if (state.searchRows.isNotEmpty()) LazyColumn(Modifier.fillMaxWidth().heightIn(max = 230.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(state.searchRows, key = { it.id }) { row ->
                OutlinedButton(onClick = { RemotePlaybackRuntime.command("search_add", row.id) }, enabled = state.online, modifier = Modifier.fillMaxWidth(), shape = androidx.compose.foundation.shape.RoundedCornerShape(12.dp)) {
                    Column(Modifier.weight(1f)) { SearchTrackInformation(row.queueRecord(), vm) }
                    OndaIcon("add", "Adicionar à fila", Modifier.size(22.dp))
                }
            }
        }
    }
}
