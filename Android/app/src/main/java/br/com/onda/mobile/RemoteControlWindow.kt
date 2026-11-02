package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.activity.compose.rememberLauncherForActivityResult
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/** Pairing UI only; closing it does not own or stop the connection. */
@Composable internal fun RemoteControlWindow(initialAddress: String? = null, forcePairing: Boolean = false, transferPlayback:Boolean=false, onDismiss: () -> Unit) {
    val remote by RemotePlaybackRuntime.presentationState.collectAsStateWithLifecycle()
    val preferences = remember { OndaStore.context.getSharedPreferences("remote_control", 0) }
    var address by rememberSaveable(initialAddress) { mutableStateOf(initialAddress ?: preferences.getString("address", "").orEmpty()) }
    var code by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    fun pairNow() {
        busy=true
        scope.launch {
            try {
                RemotePlaybackRuntime.connect(OndaStore.context,address,code,transferPlayback)
                code="";RemotePlaybackRuntime.expandedRequested.value=true;onDismiss()
            } catch(cancelled:CancellationException){throw cancelled}
            catch(error:Exception){notice=error.message ?: "Não foi possível conectar."}
            finally {busy=false}
        }
    }
    val scanner=rememberLauncherForActivityResult(ScanContract()) {result->
        result.contents?.let {contents->
            runCatching {parseRemotePairing(contents)}.onSuccess {pair->
                address=pair.address;code=pair.code;pairNow()
            }.onFailure {notice=it.message ?: "QR Code inválido."}
        }
    }
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(Modifier.fillMaxWidth().padding(16.dp), shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.padding(20.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                UiText("Controlar ONDA no PC", style = MaterialTheme.typography.titleLarge)
                if (remote.connected && !forcePairing) {
                    UiText("Reproduzindo no computador")
                    UiText(remote.title)
                    Button(onClick = { RemotePlaybackRuntime.expandedRequested.value = true; onDismiss() }) { UiText("Abrir reprodução") }
                    OutlinedButton(onClick = { RemotePlaybackRuntime.disconnect(); onDismiss() }) { UiText("Desconectar") }
                } else {
                    UiText(if(transferPlayback) "Na mesma rede Wi-Fi, ative o controle remoto no PC e informe o código. A música continua no telefone enquanto o computador prepara o áudio." else "Teste na mesma rede Wi-Fi confiável. No PC, abra Reprodução → Controle remoto. O áudio continua no computador.")
                    OutlinedTextField(value = address, onValueChange = { address = it }, label = { UiText("Endereço exibido no PC") }, singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
                    OutlinedTextField(value = code, onValueChange = { code = it.filter(Char::isDigit).take(6) }, label = { UiText("Código de conexão") }, singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(), enabled = !busy)
                    OutlinedButton(enabled=!busy,onClick={
                        scanner.launch(ScanOptions().setDesiredBarcodeFormats(ScanOptions.QR_CODE).setPrompt(translateUi("Aponte para o QR Code do ONDA PC")).setBeepEnabled(false).setOrientationLocked(true))
                    }) {UiText("Ler QR Code")}
                    Button(enabled = !busy && code.length == 6 && address.isNotBlank(), onClick = {pairNow()}) {UiText(if(busy) "Conectando…" else "Conectar")}
                }
                val message = notice.ifBlank { remote.notice }
                if (message.isNotBlank()) UiText(message, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = onDismiss) { UiText("Fechar") }
            }
        }
    }
}
