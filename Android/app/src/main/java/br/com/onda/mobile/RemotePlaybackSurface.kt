package br.com.onda.mobile

import android.os.SystemClock
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.delay

@Composable internal fun RemoteCover(state: RemotePlaybackState, modifier: Modifier) {
    Surface(modifier.clip(RoundedCornerShape(12.dp)), color = MaterialTheme.colorScheme.surfaceContainerHighest) {
        if (state.artwork != null) AsyncImage(state.artwork, translateUi("Capa do álbum"), Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
        else Box(contentAlignment = Alignment.Center) { OndaIcon("album", modifier = Modifier.size(36.dp)) }
    }
}

@Composable internal fun remotePosition(state: RemotePlaybackState): Double {
    var now by remember { mutableLongStateOf(SystemClock.elapsedRealtime()) }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    LaunchedEffect(state.playing, state.online, lifecycle) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) { now = SystemClock.elapsedRealtime(); delay(if (state.online && state.playing) 250 else 1000) }
        }
    }
    return state.positionAt(now)
}

/** Replaces the same compact surface while its source is the paired computer. */
@Composable internal fun RemotePlaybackSurface(state: RemotePlaybackState, vm: OndaViewModel, queueIsVisible: Boolean) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    var queue by rememberSaveable { mutableStateOf(false) }
    var devices by remember { mutableStateOf(false) }
    LaunchedEffect(expanded) { if (!expanded) queue = false }
    val requested by RemotePlaybackRuntime.expandedRequested.collectAsStateWithLifecycle()
    LaunchedEffect(requested) { if (requested) { expanded = true; RemotePlaybackRuntime.expandedRequested.value = false } }
    val position = remotePosition(state)
    AlbumGlass(state.artwork, Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp).testTag("remote-compact-player")) { glass ->
        Column {
            Row(Modifier.fillMaxWidth().clickable { expanded = true }.padding(6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                RemoteCover(state, Modifier.size(48.dp))
                Column(Modifier.weight(1f)) {
                    Text(state.title.ifBlank { "ONDA PC" }, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelLarge)
                    Text(state.artist, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall, color = glass.secondary)
                    Row(Modifier.clickable { devices = true }, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        OndaIcon("computer", "Dispositivos", Modifier.size(12.dp), tint = MaterialTheme.colorScheme.primary)
                        Text(if (state.online) state.deviceName else translateUi("Computador desconectado"), maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                    }
                }
                IconButton(onClick = { vm.playbackQueueOpen.value = !queueIsVisible }) { OndaIcon("queue", "Fila", Modifier.size(24.dp)) }
                OutlinedIconButton(onClick = RemotePlaybackRuntime::toggle, enabled = state.online && state.ready, border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary)) {
                    if (state.busy) CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                    else OndaIcon(if (state.playing) "pause" else "play", if (state.playing) "Pausar" else "Reproduzir", Modifier.size(26.dp))
                }
            }
            Row(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 3.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(mediaClock(position.toLong()), style = MaterialTheme.typography.labelSmall, color = glass.secondary)
                Text(mediaClock(state.duration.toLong()), style = MaterialTheme.typography.labelSmall, color = glass.secondary)
            }
            LinearProgressIndicator(progress = { if (state.duration > 0) (position / state.duration).toFloat().coerceIn(0f, 1f) else 0f }, modifier = Modifier.fillMaxWidth().height(2.dp), trackColor = glass.ink.copy(alpha = .18f))
        }
    }
    if (expanded) Dialog(onDismissRequest = { expanded = false }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
            RemotePlayerContent(state, onCollapse = { expanded = false }, onQueue = { queue = true }, onAdjustments = { expanded = false; vm.effectsNavigation.value = true })
        }
        if (queue) PlaybackQueueSheet(vm) { queue = false }
    }
    if (devices) PlaybackDevicesSheet { devices = false }
}

@Composable private fun RemotePlayerContent(state: RemotePlaybackState, onCollapse: (() -> Unit)? = null, onQueue: () -> Unit, onAdjustments: () -> Unit) {
    val position = remotePosition(state)
    var dragged by remember(state.trackId) { mutableStateOf<Float?>(null) }
    var devices by remember { mutableStateOf(false) }
    var menu by remember { mutableStateOf(false) }
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val coverSize = minOf(maxWidth - 48.dp, maxHeight * .46f).coerceAtLeast(100.dp)
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                if (onCollapse != null) IconButton(onClick = onCollapse) { OndaIcon("down", "Recolher reprodução", Modifier.size(26.dp)) }
                Spacer(Modifier.weight(1f))
                ShufflePlaybackButton(state.shuffle, { RemotePlaybackRuntime.command("shuffle", it) })
                RepeatPlaybackButton(state.repeat, { RemotePlaybackRuntime.command("repeat", it) })
                Box {
                    IconButton(onClick = { menu = true }) { OndaIcon("more-vertical", "Mais", Modifier.size(24.dp)) }
                    DropdownMenu(menu, { menu = false }) {
                        DropdownMenuItem(text = { UiText("Ajustes de reprodução") }, onClick = { menu = false; onAdjustments() })
                        DropdownMenuItem(text = { UiText("Dispositivos") }, onClick = { menu = false; devices = true })
                        DropdownMenuItem(text = { UiText("Desconectar") }, onClick = { menu = false; RemotePlaybackRuntime.disconnect() })
                    }
                }
            }
            RemoteCover(state, Modifier.size(coverSize).align(Alignment.CenterHorizontally))
            Column {
                Text(state.title.ifBlank { "ONDA PC" }, style = MaterialTheme.typography.headlineSmall)
                Text(state.artist, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column {
                RoundSlider(dragged ?: position.toFloat().coerceIn(0f, state.duration.toFloat().coerceAtLeast(1f)), { dragged = it },
                    valueRange = 0f..state.duration.toFloat().coerceAtLeast(1f), enabled = state.online && state.ready && state.duration > 0,
                    onValueChangeFinished = { dragged?.let { RemotePlaybackRuntime.seek(it.toDouble()) }; dragged = null },
                    modifier = Modifier.fillMaxWidth().testTag("remote-player-timeline").a11yLabel("Posição na música"), slim = true)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    UiText(mediaClock((dragged?.toDouble() ?: position).toLong()), style = MaterialTheme.typography.labelSmall)
                    UiText(mediaClock(state.duration.toLong()), style = MaterialTheme.typography.labelSmall)
                }
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceEvenly) {
                IconButton(onClick = { devices = true }) { OndaIcon("volume", "Volume do computador", Modifier.size(24.dp)) }
                IconButton(onClick = { RemotePlaybackRuntime.command("previous") }, enabled = state.online) { OndaIcon("previous", "Retroceder", Modifier.size(32.dp)) }
                FilledIconButton(onClick = RemotePlaybackRuntime::toggle, enabled = state.online && state.ready, modifier = Modifier.size(72.dp)) {
                    if (state.busy) CircularProgressIndicator(Modifier.size(30.dp), strokeWidth = 3.dp, color = MaterialTheme.colorScheme.onPrimary)
                    else OndaIcon(if (state.playing) "pause" else "play", if (state.playing) "Pausar" else "Reproduzir", Modifier.size(36.dp))
                }
                IconButton(onClick = { RemotePlaybackRuntime.command("next") }, enabled = state.online) { OndaIcon("next", "Avançar", Modifier.size(32.dp)) }
                IconButton(onClick = onQueue) { OndaIcon("queue", "Fila do computador", Modifier.size(26.dp)) }
            }
            PlaybackDeviceButton(onClick = { devices = true }, name = state.deviceName, remote = true)
            if (state.notice.isNotBlank()) UiText(state.notice, style = MaterialTheme.typography.bodySmall)
        }
    }
    if (devices) PlaybackDevicesSheet { devices = false }
}
