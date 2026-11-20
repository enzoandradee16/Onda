package br.com.onda.mobile
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.imageLoader
import org.json.JSONObject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@OptIn(coil.annotation.ExperimentalCoilApi::class)
@Composable
internal fun CacheControls(vm: OndaViewModel) {
    val busy by vm.busy.collectAsStateWithLifecycle()
    val active by OndaStore.active.collectAsStateWithLifecycle()
    var bytes by remember { mutableStateOf<Long?>(null) }
    var cleaned by remember { mutableStateOf(false) }
    var freed by remember { mutableStateOf(0L) }
    val scope = rememberCoroutineScope()
    var cleaning by remember { mutableStateOf(false) }
    var reading by remember { mutableStateOf(false) }
    var readError by remember { mutableStateOf("") }
    var details by remember { mutableStateOf(JSONObject()) }
    var showTracks by remember { mutableStateOf(false) }
    var confirm by remember { mutableStateOf(false) }
    var nativeBytes by remember { mutableStateOf(0L) }
    var imageBytes by remember { mutableStateOf(0L) }
    var nativeProtected by remember { mutableStateOf(0L) }
    val loader = OndaStore.context.imageLoader
    fun protection() = StreamAudioCache.protectedPaths() + vm.jukebox.protectedCachePaths()
    fun size(value: Long) = if (value <=
        0
    ) "0 B" else if (value < 1048576) "${(value+1023)/1024} KB" else "%.1f MB".format(value / 1048576.0)
    suspend fun readSize() {
        if (reading) return
        reading = true
        readError = ""
        try {
            val protected = protection()
            val models = org.json.JSONArray(vm.jukebox.cacheLabels())
            val result = withContext(Dispatchers.IO) {
                MobileEngine.call(
                    OndaStore.context,
                    "cache-info-" + java.util.UUID.randomUUID(),
                    "cache_report",
                    JSONObject().put(
                        "_stream_cache_protected",
                        org.json.JSONArray(protected)
                    ).put(
                        "_cache_models",
                        models
                    ).put("playback_cache_limit_mb", OndaStore.settings.value.optInt("playback_cache_limit_mb", 384)),
                    EventCallback {
                    }
                )
            }
            if (result.has("error")) readError = result.optString("error")
            else {
                details = result
                imageBytes = loader.diskCache?.size ?: 0L
                nativeBytes = withContext(Dispatchers.IO) { StreamAudioCache.size(OndaStore.context) }
                nativeProtected =
                    withContext(Dispatchers.IO) {
                        if (vm.jukebox.state.value.model?.has("_stream") ==
                            true
                        ) nativeBytes else StreamAudioCache.recentSize(OndaStore.context)
                    }
                bytes = result.optLong("bytes") + imageBytes + nativeBytes
            }
        } catch (
            cancelled: CancellationException
        ) {
            throw cancelled
        } catch (
            error: Exception
        ) {
            readError = uiExceptionMessage(error, "Erro na operação")
        } finally {
            reading = false
        }
    }
    fun clear() {
        if (busy || cleaning || reading || active.isNotBlank()) return
        readError = ""
        vm.stopPreview()
        vm.operation(
            "cache_clear",
            JSONObject().put("_stream_cache_protected", org.json.JSONArray(protection())),
            dialog = false
        ) { result ->
            cleaning = true
            freed = result.optLong("removed") + (loader.diskCache?.size ?: 0L)
            if (result.optInt("failed") >
                0
            ) readError =
                "Alguns arquivos não puderam ser removidos. Tente novamente depois de fechar as operações em andamento."
            scope.launch {
                try {
                    val playingStream = vm.jukebox.state.value.let { it.model?.has("_stream") == true }
                    val streamFreed =
                        withContext(Dispatchers.IO) {
                            loader.memoryCache?.clear()
                            loader.diskCache?.clear()
                            if (playingStream) 0L else StreamAudioCache.clear(OndaStore.context)
                        }
                    freed += streamFreed
                    invalidateHistoryDetails()
                    cleaned = true
                    readSize()
                } finally {
                    cleaning = false
                }
            }
        }
    }
    LaunchedEffect(Unit) { readSize() }
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    Toggle("Limpar temporários automaticamente", settings.optBoolean("automatic_cache_cleanup", true)) {
        OndaStore.saveSettings(JSONObject(settings.toString()).put("automatic_cache_cleanup", it))
    }
    UiText(
        "A música atual, as próximas preparadas e as últimas músicas ouvidas são preservadas para voltar.",
        style = MaterialTheme.typography.bodySmall
    )
    Select(
        "Limite do cache de áudio (MB)",
        settings.optInt("playback_cache_limit_mb", 384).toString(),
        listOf("256", "384", "512", "1024", "2048", "4096"),
        enabled =
        !busy && !cleaning
    ) {
        OndaStore.saveSettings(JSONObject(settings.toString()).put("playback_cache_limit_mb", it.toInt()))
        scope.launch { readSize() }
    }
    UiText(
        "O limite pode ser ultrapassado enquanto houver músicas protegidas. O streaming do Android usa até 128 MB adicionais.",
        style = MaterialTheme.typography.bodySmall
    )
    UiText("Cache", style = MaterialTheme.typography.titleMedium)
    UiText(
        "Limpa capas, buscas e caches temporários. Downloads, fila, histórico, contas e escolhas salvas são preservados.",
        style = MaterialTheme.typography.bodySmall
    )
    bytes?.let {
        UiText(
            (if (cleaned) "Cache limpo. Restante em disco: {size} MB." else "Cache em disco: {size} MB.").replace(
                "{size}",
                "%.2f".format(it / 1048576.0)
            )
        )
    }
    details.optJSONArray("categories")?.objects()?.forEach { row ->
        val amount = row.optLong("bytes") + if (row.optString("name") == "Capas e imagens") imageBytes else 0L
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            UiText(row.getString("name"), style = MaterialTheme.typography.bodySmall)
            Text(size(amount), style = MaterialTheme.typography.bodySmall)
        }
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        UiText("Áudio em streaming", style = MaterialTheme.typography.bodySmall)
        Text(size(nativeBytes), style = MaterialTheme.typography.bodySmall)
    }
    UiText(
        "Protegido da limpeza: " + size(details.optLong("protected_bytes") + nativeProtected),
        style = MaterialTheme.typography.bodySmall
    )
    TextButton(onClick = {
        showTracks = !showTracks
    }) { UiText(if (showTracks) "Ocultar músicas armazenadas" else "Ver músicas armazenadas") }
    if (showTracks) details.optJSONArray("tracks")?.objects()?.forEach { row ->
        Row(Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) {
                Text(row.getString("name"), style = MaterialTheme.typography.bodyMedium)
                UiText(
                    size(row.getLong("bytes")) + " · " + translateUi(row.getString("reason"), LocalUiLanguage.current),
                    style = MaterialTheme.typography.bodySmall
                )
            }
            TextButton(enabled = !row.optBoolean("protected") && !busy && !cleaning, onClick = {
                vm.operation(
                    "cache_remove",
                    JSONObject().put(
                        "cache_id",
                        row.getString("id")
                    ).put("_stream_cache_protected", org.json.JSONArray(protection())),
                    dialog = false
                ) {
                    scope.launch { readSize() }
                }
            }) { UiText("Remover") }
        }
    }
    if (confirm) AlertDialog(onDismissRequest = {
        confirm = false
    }, title = { UiText("Limpar arquivos dispensáveis") }, text = {
        UiText(
            "Até " + size((bytes ?: 0L) - details.optLong("protected_bytes") - nativeProtected) +
                " podem ser liberados. A música atual, as próximas preparadas e as recentes serão preservadas. Os áudios removidos precisarão ser preparados novamente."
        )
    }, confirmButton = {
        TextButton(onClick = {
            confirm =
                false
            clear()
        }) { UiText("Limpar") }
    }, dismissButton = { TextButton(onClick = { confirm = false }) { UiText("Cancelar") } })
    if (cleaned) UiText("Cache limpo. Espaço liberado: {size} MB.".replace("{size}", "%.2f".format(freed / 1048576.0)))
    if (readError.isNotBlank()) UiErrorText(
        readError,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.error
    )
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        TextButton(modifier = Modifier.weight(1f), enabled = !busy && !cleaning && !reading, onClick = {
            scope.launch { readSize() }
        }) { UiText("Atualizar tamanho", textAlign = androidx.compose.ui.text.style.TextAlign.Center) }
        OutlinedButton(
            modifier = Modifier.weight(
                1f
            ),
            enabled = !busy && !cleaning && !reading && active.isBlank(),
            onClick = {
                confirm =
                    true
            }
        ) { UiText("Limpar arquivos dispensáveis", textAlign = androidx.compose.ui.text.style.TextAlign.Center) }
    }
    if (active.isNotBlank()) UiText(
        "Aguarde as operações em andamento antes de limpar o cache.",
        style = MaterialTheme.typography.bodySmall
    )
}
