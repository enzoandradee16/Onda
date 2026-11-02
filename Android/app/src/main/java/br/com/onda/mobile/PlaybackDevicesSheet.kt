package br.com.onda.mobile

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable internal fun PlaybackDeviceButton(onClick: () -> Unit, name: String = "Este telefone", remote: Boolean = false) {
    TextButton(onClick = onClick, modifier = Modifier.testTag("playback-devices")) {
        OndaIcon("devices", "Dispositivos", Modifier.size(20.dp), tint=if(remote)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.width(8.dp))
        Text(translateUi(name), maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

/** Device selection controls the destination; it never claims to transfer local-only files. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable internal fun PlaybackDevicesSheet(onDismiss: () -> Unit) {
    val remote by RemotePlaybackRuntime.presentationState.collectAsStateWithLifecycle()
    val context = OndaStore.context
    val juke = remember { JukeboxRuntime.get(context) }
    val local by juke.presentationState.collectAsStateWithLifecycle()
    val preferences = remember { context.getSharedPreferences("remote_control", 0) }
    var saved by remember { mutableStateOf(preferences.getString("address", "").orEmpty()) }
    var found by remember { mutableStateOf(emptyList<PlaybackDevice>()) }
    var searching by remember { mutableStateOf(true) }
    var pairing by remember { mutableStateOf<String?>(null) }
    var pairingTransfer by remember { mutableStateOf(false) }
    var connecting by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf("") }
    var volume by remember(remote.volume) { mutableFloatStateOf(remote.volume.toFloat()) }
    val scope = rememberCoroutineScope()
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    LaunchedEffect(lifecycle) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                searching = true
                try { found = discoverPlaybackDevices() }
                catch (cancelled: CancellationException) { throw cancelled }
                catch (_: Exception) { notice = "Não foi possível buscar dispositivos. Use o endereço do PC." }
                finally { searching = false }
                delay(5000)
            }
        }
    }
    fun select(address: String, transfer:Boolean?=null) {
        if (connecting) return
        connecting = true
        scope.launch {
            try {
                if (RemotePlaybackRuntime.selectDevice(context, address, transferPlayback=transfer)) { RemotePlaybackRuntime.expandedRequested.value = true; onDismiss() }
                else {pairingTransfer=transfer ?: (!remote.connected && local.model!=null && local.playing && !local.paused);pairing = address}
            } catch (cancelled: CancellationException) { throw cancelled
            } catch (error: Exception) { notice = error.message ?: "Não foi possível conectar. Confira o endereço, o código e a rede."
            } finally { connecting = false }
        }
    }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().fillMaxHeight(.86f).padding(horizontal = 24.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            UiText("Dispositivos", style = MaterialTheme.typography.headlineSmall)
            Surface(shape = RoundedCornerShape(20.dp), color = MaterialTheme.colorScheme.surfaceContainerHigh, modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(if (remote.connected) remote.deviceName else translateUi("Este telefone"), style = MaterialTheme.typography.titleLarge)
                        Text(if (remote.connected) listOf(remote.title, remote.artist).filter(String::isNotBlank).joinToString(" · ") else local.title,
                            maxLines = 2, overflow = TextOverflow.Ellipsis, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyMedium)
                        UiText(if (remote.connected && !remote.online) "Computador desconectado" else "Dispositivo atual", style = MaterialTheme.typography.labelSmall)
                    }
                    OndaIcon(if (remote.connected) "computer" else "phone", modifier = Modifier.size(36.dp), tint = MaterialTheme.colorScheme.primary)
                }
            }
            if(connecting)LinearProgressIndicator(Modifier.fillMaxWidth())
            if (notice.isNotBlank()) UiText(notice, style = MaterialTheme.typography.bodySmall)
            if (remote.connected) {
                Column {
                    UiText("Volume do computador", style = MaterialTheme.typography.labelLarge)
                    RoundSlider(volume, { volume = it }, valueRange = 0f..100f, enabled = remote.online,
                        onValueChangeFinished = { RemotePlaybackRuntime.setVolume(volume.toInt()) }, modifier = Modifier.fillMaxWidth().a11yLabel("Volume do computador"), slim = true)
                }
                DeviceRow(translateUi("Este telefone"), "Continuar neste telefone", "phone", !connecting && remote.online, onClick = {
                    connecting=true
                    scope.launch {
                        try {RemotePlaybackRuntime.transferToPhone(context);onDismiss()}
                        catch(cancelled:CancellationException){throw cancelled}
                        catch(error:Exception){notice=error.message ?: "Não foi possível transferir a reprodução."}
                        finally {connecting=false}
                    }
                })
                TextButton(onClick={RemotePlaybackRuntime.disconnect();onDismiss()},enabled=!connecting){UiText("Somente desconectar") }
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                UiText("Na mesma rede", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                if (searching || connecting) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
            }
            val devices = (found + if (saved.isNotBlank()) listOf(PlaybackDevice(saved, preferences.getString("name", "ONDA PC").orEmpty())) else emptyList()).distinctBy { it.address }.filter { it.address != remote.address }
            devices.forEach { device ->
                var menu by remember(device.address) { mutableStateOf(false) }
                DeviceRow(device.name, if (found.any { it.address == device.address }) "Disponível" else "Dispositivo salvo", "computer", !connecting,
                    onClick = { select(device.address) }, trailing = {
                        Box {
                            IconButton(onClick = { menu = true }) { OndaIcon("more", "Mais", Modifier.size(24.dp)) }
                            DropdownMenu(menu, { menu = false }) {
                                if(local.model!=null && !remote.connected)DropdownMenuItem(text={UiText("Transferir música para o computador")},onClick={menu=false;select(device.address,true)})
                                DropdownMenuItem(text = { UiText("Esquecer dispositivo") }, onClick = { menu = false; RemotePlaybackRuntime.forget(device.address); if (saved == device.address) saved = "" })
                            }
                        }
                    })
            }
            if (devices.isEmpty()) UiText("Ative Controle remoto em Reprodução no ONDA PC para encontrá-lo aqui.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = { pairingTransfer=false;pairing = "" }, enabled = !connecting, modifier = Modifier.fillMaxWidth()) {
                OndaIcon("add", modifier = Modifier.size(20.dp)); Spacer(Modifier.width(8.dp)); UiText("Conectar computador")
            }
            OutlinedButton(onClick = {
                runCatching { context.startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
                    .onFailure { notice = "Não foi possível abrir as configurações de Bluetooth." }
            }, modifier = Modifier.fillMaxWidth()) {
                OndaIcon("bluetooth", modifier = Modifier.size(20.dp)); Spacer(Modifier.width(8.dp)); UiText("Bluetooth deste telefone")
            }
            UiText("Transfira músicas pesquisadas no ONDA entre o telefone e o computador. Ao desconectar, o áudio permanece no dispositivo atual.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(16.dp))
        }
        if (pairing != null) RemoteControlWindow(initialAddress = pairing!!.ifBlank { saved }, forcePairing = true, transferPlayback=pairingTransfer, onDismiss = { pairing = null; if (RemotePlaybackRuntime.state.value.connected) onDismiss() })
    }
}

@Composable private fun DeviceRow(name: String, subtitle: String, icon: String, enabled: Boolean, onClick: () -> Unit, trailing: @Composable () -> Unit = {}) {
    Row(Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick).padding(vertical = 12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        OndaIcon(icon, modifier = Modifier.size(28.dp))
        Column(Modifier.weight(1f)) {
            Text(name, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            UiText(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        trailing()
    }
}
