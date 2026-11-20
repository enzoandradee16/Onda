package br.com.onda.mobile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject
import java.io.File

@Composable fun DownloadConcurrencyOptions(settings: JSONObject, put: (String, Any) -> Unit) {
    Select("Downloads simultâneos", settings.optString("concurrent_downloads", "1"), listOf("1", "2", "3", "4")) {
        put("concurrent_downloads", it)
    }
    SettingsDivider()
    UiText("No Android, escolha de 1 a 4 downloads simultâneos.", style = MaterialTheme.typography.bodySmall)
}

@Composable fun AdvancedDownloadOptions(settings: JSONObject, put: (String, Any) -> Unit) {
    UiText("Fila e agendamento", style = MaterialTheme.typography.titleMedium)
    SettingsDivider()
    Toggle("Detectar duplicatas na fila e no histórico", settings.optBoolean("detect_duplicates", true)) {
        put("detect_duplicates", it)
    }
    SettingsDivider()
    Toggle("Retomar arquivos interrompidos quando possível", settings.optBoolean("resume_downloads", true)) {
        put("resume_downloads", it)
    }
    SettingsDivider()
    Toggle("Retomar fila ao abrir o ONDA", settings.optBoolean("resume_queue")) { put("resume_queue", it) }
    SettingsDivider()
    Toggle("Normalizar volume dos próximos downloads", settings.optBoolean("normalize_volume")) {
        put("normalize_volume", it)
    }
    SettingsDivider()
    DailyDownloadControls(settings, put)
    SettingsDivider()
    Toggle("Agendar downloads", settings.optBoolean("schedule_enabled")) { put("schedule_enabled", it) }
    SettingsDivider()
    Row(horizontalArrangement = Arrangement.spacedBy(LayoutSpacing.controls)) {
        ScheduleTimeButton(
            "Começar · HH:MM",
            settings.optString("schedule_start", "22:00"),
            "22:00",
            Modifier.weight(1f)
        ) {
            put("schedule_start", it)
        }
        ScheduleTimeButton(
            "Parar · HH:MM",
            settings.optString("schedule_stop", "07:00"),
            "07:00",
            Modifier.weight(1f)
        ) {
            put("schedule_stop", it)
        }
    }
    if (settings.optBoolean("schedule_enabled")) {
        val valid = runCatching {
            java.time.LocalTime.parse(settings.optString("schedule_start")) !=
                java.time.LocalTime.parse(settings.optString("schedule_stop"))
        }.getOrDefault(false)
        if (!valid) UiText("Informe horários diferentes no formato HH:MM.", color = MaterialTheme.colorScheme.error)
    }
    UiText(
        "O Android pode atrasar o início para economizar bateria. A fila interrompida fica pendente para retomar.",
        style = MaterialTheme.typography.bodySmall
    )
}

@Composable fun PreferenceTransfer(vm: OndaViewModel) {
    val export =
        rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
            if (uri !=
                null
            ) {
                vm.operation(
                    "settings_export",
                    JSONObject().put("settings", OndaStore.settings.value),
                    dialog = true
                ) { result ->
                    runCatching {
                        OndaStore.context.contentResolver.openOutputStream(uri)!!.bufferedWriter().use {
                            it.write(result.getJSONObject("payload").toString(2))
                        }
                    }
                        .onSuccess {
                            vm.showNotice("Exportar configurações", "Configurações exportadas.")
                        }.onFailure {
                            vm.showNotice("Exportar configurações", uiExceptionMessage(it, "Não foi possível salvar."))
                        }
                }
            }
        }
    val importFile =
        rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            if (uri != null) {
                vm.importLocal(uri, "preferences", dialog = true) { file ->
                    if (file.length() >
                        131072
                    ) vm.showNotice(
                        "Importar configurações",
                        "Arquivo muito grande."
                    ) else vm.operation(
                        "settings_import",
                        JSONObject().put("path", file.absolutePath),
                        dialog = true
                    ) { result ->
                        val updated = JSONObject(OndaStore.settings.value.toString())
                        val changes = result.getJSONObject("settings")
                        changes.keys().forEach { updated.put(it, changes.get(it)) }
                        OndaStore.saveSettings(updated)
                        vm.showNotice("Importar configurações", "Configurações importadas.")
                        file.delete()
                    }
                }
            }
        }
    SettingsDivider()
    TextButton(onClick = { export.launch("ONDA-configuracoes.json") }) { UiText("Exportar configurações…") }
    SettingsDivider()
    TextButton(onClick = {
        importFile.launch(arrayOf("application/json", "text/plain"))
    }) { UiText("Importar configurações…") }
    UiText(
        "A transferência não inclui contas, cookies nem caminhos de pastas.",
        style = MaterialTheme.typography.bodySmall
    )
}

@Composable fun AppUpdateControls(vm: OndaViewModel) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val update by vm.appUpdate.collectAsStateWithLifecycle()
    SettingsDivider()
    Toggle("Verificar atualizações do ONDA ao abrir", settings.optBoolean("check_updates")) {
        OndaStore.saveSettings(JSONObject(settings.toString()).put("check_updates", it))
    }
    SettingsDivider()
    OutlinedButton(onClick = {
        vm.operation("app_update", JSONObject().put("version", BuildConfig.VERSION_NAME), dialog = true) {
            vm.appUpdate.value =
                it
            vm.showNotice("Verificar atualização do ONDA", it.optString("message"))
        }
    }) { UiText("Verificar atualização do ONDA") }
    update?.takeIf { it.optBoolean("available") }?.let { info ->
        Text(info.optString("asset"), style = MaterialTheme.typography.labelMedium)
        if (info.optLong("size") >
            0
        ) Text("%.1f MB".format(info.optLong("size") / 1048576.0), style = MaterialTheme.typography.labelSmall)
        if (info.optString(
                "notes"
            ).isNotBlank()
        ) Text(
            info.optString("notes"),
            maxLines = 8,
            overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
            style = MaterialTheme.typography.bodySmall
        )
    }
    val updater = remember { InAppUpdate(OndaStore.context) }
    var download by remember { mutableStateOf(UpdateDownload()) }
    val language = LocalUiLanguage.current
    val lifecycleOwner = LocalLifecycleOwner.current
    LaunchedEffect(updater, lifecycleOwner, download.status) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            pollUpdateDownload(updater::state, { download = it })
        }
    }
    val downloading = download.inProgress
    if (downloading) {
        UiText("Baixando atualização do ONDA")
        if (download.total > 0) {
            val progress = (download.bytes.toFloat() / download.total).coerceIn(0f, 1f)
            LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
            Text("${(progress*100).toInt()}%")
        } else LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        TextButton(onClick = {
            updater.cancel()
            download = UpdateDownload()
        }) { UiText("Cancelar download da atualização") }
    } else if (download.status == android.app.DownloadManager.STATUS_SUCCESSFUL) {
        Button(onClick = {
            runCatching { updater.install() }.onSuccess { opened ->
                if (!opened) vm.showNotice(
                    "Instalar atualização",
                    "Permita a instalação pelo ONDA e volte para tocar em Instalar atualização."
                )
            }.onFailure {
                vm.showNotice("Instalar atualização", uiExceptionMessage(it, "Não foi possível iniciar a instalação."))
            }
        }) { UiText("Instalar atualização") }
        TextButton(onClick = {
            updater.cancel()
            download = UpdateDownload()
        }) { UiText("Descartar atualização baixada") }
    } else {
        if (download.status ==
            android.app.DownloadManager.STATUS_FAILED
        ) UiText("Não foi possível baixar a atualização. Tente novamente.")
        if (update?.optBoolean("available") == true) Button(onClick = {
            runCatching {
                updater.start(update!!.getString("url"), language)
                download = updater.state()
            }
                .onFailure {
                    vm.showNotice(
                        "Baixar nova versão",
                        uiExceptionMessage(it, "Não foi possível baixar a atualização. Tente novamente.")
                    )
                }
        }) { UiText("Baixar nova versão") }
    }
    UiText(
        "A atualização é baixada dentro do ONDA e continua em segundo plano. Ao terminar, toque em Instalar atualização e confirme no Android. Seus dados são preservados.",
        style = MaterialTheme.typography.bodySmall
    )
}

@Composable fun AudioFileEditor(item: HistoryItem, vm: OndaViewModel, close: () -> Unit) {
    val canUndo by MetadataUndo.available.collectAsState()
    var source by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var changes by androidx.compose.runtime.saveable.rememberSaveable(
        stateSaver = androidx.compose.runtime.saveable.Saver<JSONObject, String>(save = {
            it.toString()
        }, restore = { JSONObject(it) })
    ) { mutableStateOf(JSONObject()) }
    val pasteAvailable = rememberMetadataPasteAvailable()
    var transferPath by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var transferCover by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var originalTags by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("{}") }
    var moreTags by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(false) }
    var loaded by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(false) }
    var editing by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(true) }
    var overwrite by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(false) }
    var normalize by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(false) }
    var lyrics by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var cover by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var cropCandidate by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var identifiedCoverUrl by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var originalCover by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    var preview by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf("") }
    val busy by vm.busy.collectAsStateWithLifecycle()
    val pickLyrics = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri !=
            null
        ) vm.importLocal(uri, "lyrics", dialog = true) { lyrics = it.absolutePath }
    }
    val pickCover =
        rememberImageSourcePicker { uri ->
            vm.importLocal(uri, "cover", dialog = false) {
                if (cover.isNotBlank()) File(cover).delete()
                cover =
                    it.absolutePath
            }
        }
    LaunchedEffect(item.uri) {
        if (!loaded) vm.importLocal(Uri.parse(item.uri), "audio-editor", dialog = false) { file ->
            source =
                file.absolutePath
            vm.operation("audio_read", JSONObject().put("source", source), dialog = false) {
                changes =
                    it.getJSONObject("record").apply {
                        if (optString("title") ==
                            file.nameWithoutExtension
                        ) put("title", item.title.substringBeforeLast('.'))
                    }
                originalTags =
                    changes.toString()
                originalCover = it.optString("cover_preview")
                loaded = true
            }
        }
    }
    fun saveChanges() = JSONObject(changes.toString()).apply {
        val original = JSONObject(originalTags)
        for (key in listOf(
            "album_artist",
            "composer",
            "comment"
        ))if (optString(key) == original.optString(key)) remove(key)
    }
    fun config() = OndaStore.config().put("source", source).put("output_name", item.title.substringBeforeLast('.'))
        .put(
            "overwrite_original",
            overwrite
        ).put(
            "original_uri",
            item.uri
        ).put(
            "edit_metadata",
            editing
        ).put("normalize_volume", normalize).put("changes", saveChanges()).put("lyrics_path", lyrics).put(
            "cover_path",
            if (transferCover.isNotBlank() &&
                cover == transferCover
            ) "" else cover
        ).put("cover_url", identifiedCoverUrl).put("tag_transfer_path", transferPath).put(
            "tag_transfer_cover",
            transferCover.isNotBlank() && cover == transferCover
        )
    fun copyTags() {
        val output = MetadataClipboard.newCopyFile()
        val request = JSONObject().put(
            "source",
            source
        ).put("record", changes).put("clipboard_path", output.absolutePath)
            .put("base_transfer_path", transferPath).put(
                "cover_path",
                if (cover ==
                    transferCover
                ) "" else cover
            ).put("cover_url", identifiedCoverUrl).put("lyrics_path", lyrics)
        vm.operation("audio_tags_copy", request, dialog = false) { result ->
            MetadataClipboard.publish(result.getString("clipboard_path"))
        }
    }
    fun pasteTags() {
        runCatching {
            val draft = MetadataClipboard.draft()
            vm.operation(
                "audio_tags_paste",
                JSONObject().put("clipboard_path", draft.absolutePath),
                dialog = false
            ) { result ->
                if (result.optBoolean("cancelled")) return@operation
                val tags = result.getJSONObject("record")
                changes = JSONObject(changes.toString()).apply { tags.keys().forEach { put(it, tags.get(it)) } }
                if (transferPath.isNotBlank()) File(transferPath).delete()
                transferPath = result.getString("tag_transfer_path")
                if (result.optString("cover_path").isNotBlank()) {
                    if (cover.isNotBlank()) File(cover).delete()
                    cover = result.getString("cover_path")
                    transferCover = cover
                    identifiedCoverUrl = ""
                } else transferCover = ""
                lyrics = ""
            }
        }.onFailure {
            vm.showNotice("Colar tags", uiExceptionMessage(it, "Copie as tags de uma música no ONDA primeiro."))
        }
    }
    fun recognizeName(audio: Boolean = false) {
        val requestedSource = source
        val request = JSONObject().put("source", source).put("filename", item.title).put("record", changes)
        vm.operation(
            if (audio) "audio_fingerprint_lookup" else "audio_name_lookup",
            request,
            dialog = false
        ) nameResult@{ result ->
            if (source != requestedSource || result.optBoolean("cancelled")) return@nameResult
            val match = result.optJSONArray("matches")?.optJSONObject(0)
            if (match ==
                null
            ) vm.showNotice(
                if (audio) "Identificar pelo áudio" else "Identificar pelo nome",
                result.optJSONArray("errors")?.optJSONObject(0)?.optString("error").orEmpty().ifBlank {
                    "Nenhuma gravação correspondente foi encontrada."
                }
            )
            else {
                val tags = match.getJSONObject("changes")
                changes = JSONObject(changes.toString()).apply { tags.keys().forEach { put(it, tags.get(it)) } }
                if (match.optString("cover_url").isNotBlank()) {
                    if (cover.isNotBlank()) File(cover).delete()
                    cover = ""
                    identifiedCoverUrl = match.getString("cover_url")
                }
                vm.status.value = "Metadados prontos para revisar e salvar."
            }
        }
    }
    fun finish() {
        vm.stopPreview()
        listOf(preview, source, cover, lyrics, cropCandidate, transferPath, transferCover).filter {
            it.isNotBlank()
        }.forEach { File(it).delete() }
        close()
    }
    if (cropCandidate.isNotBlank()) CoverCropper(
        cropCandidate,
        onCancel = { cropCandidate = "" },
        onApply = { cropped ->
            if (cover.isNotBlank()) File(cover).delete()
            cover = cropped
            File(cropCandidate).delete()
            cropCandidate =
                ""
        }
    )
    Column(
        Modifier.fillMaxSize().padding(horizontal = 20.dp).verticalScroll(rememberScrollState()).imePadding(),
        verticalArrangement = Arrangement.spacedBy(LayoutSpacing.controls)
    ) {
        ToolHeading("Editar metadados") {
            var fileMenu by remember { mutableStateOf(false) }
            Box {
                IconButton(onClick = {
                    fileMenu = true
                }) { OndaIcon("more-vertical", "Mais ações", Modifier.size(22.dp)) }
                DropdownMenu(fileMenu, { fileMenu = false }) {
                    DropdownMenuItem(text = {
                        UiText("Identificar pelo nome")
                    }, enabled = loaded && editing && !busy, onClick = {
                        fileMenu =
                            false
                        recognizeName()
                    })
                    DropdownMenuItem(text = {
                        UiText("Identificar pelo áudio")
                    }, enabled = loaded && editing && !busy, onClick = {
                        fileMenu =
                            false
                        recognizeName(true)
                    })
                    DropdownMenuItem(text = {
                        UiText("Desfazer última edição")
                    }, enabled = canUndo && !busy, onClick = {
                        fileMenu =
                            false
                        vm.undoMetadata()
                    })
                    DropdownMenuItem(text = { UiText("Copiar tags") }, enabled = loaded && !busy, onClick = {
                        fileMenu = false
                        copyTags()
                    })
                    DropdownMenuItem(text = {
                        UiText("Colar tags")
                    }, enabled = loaded && editing && !busy && pasteAvailable, onClick = {
                        fileMenu =
                            false
                        pasteTags()
                    })
                    DropdownMenuItem(text = { UiText("Escolher outro arquivo") }, enabled = !busy, onClick = {
                        fileMenu = false
                        finish()
                    })
                }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = {
                recognizeName()
            }, enabled = loaded && editing && !busy, modifier = Modifier.weight(1f)) { UiText("Identificar pelo nome") }
            OutlinedButton(onClick = {
                recognizeName(true)
            }, enabled = loaded && editing && !busy, modifier = Modifier.weight(1f)) {
                UiText("Identificar pelo áudio")
            }
        }
        ToolCard {
            Row(
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                val originalBitmap =
                    remember(originalCover) {
                        runCatching {
                            val bytes = android.util.Base64.decode(originalCover, android.util.Base64.DEFAULT)
                            android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        }.getOrNull()
                    }
                val identifiedArtwork =
                    remember(identifiedCoverUrl) {
                        if (identifiedCoverUrl.startsWith("data:image/")) runCatching {
                            android.util.Base64.decode(
                                identifiedCoverUrl.substringAfter(','),
                                android.util.Base64.DEFAULT
                            )
                        }.getOrNull() else identifiedCoverUrl
                    }
                Surface(
                    Modifier.size(124.dp),
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    if (cover.isNotBlank() || identifiedCoverUrl.isNotBlank() ||
                        originalBitmap != null
                    ) coil.compose.AsyncImage(
                        model = if (cover.isNotBlank()) File(
                            cover
                        ) else if (identifiedCoverUrl.isNotBlank()) identifiedArtwork else originalBitmap,
                        contentDescription = translateUi("Capa do álbum", LocalUiLanguage.current),
                        modifier = Modifier.fillMaxSize(),
                        contentScale = androidx.compose.ui.layout.ContentScale.Crop
                    )
                    else Box(contentAlignment = androidx.compose.ui.Alignment.Center) {
                        OndaIcon("album", modifier = Modifier.size(40.dp))
                    }
                }
                Column(Modifier.weight(1f)) {
                    TextButton(onClick = { pickCover() }, enabled = editing && !busy) { UiText("Alterar capa") }
                    TextButton(onClick = {
                        cropCandidate = cover
                    }, enabled = cover.isNotBlank() && editing && !busy) { UiText("Ajustar capa") }
                    TextButton(
                        onClick = {
                            if (cover.isNotBlank()) File(cover).delete()
                            cover = ""
                            identifiedCoverUrl = ""
                        },
                        enabled =
                        (cover.isNotBlank() || identifiedCoverUrl.isNotBlank()) && !busy
                    ) { UiText("Desfazer capa") }
                }
            }
        }
        ToolCard {
            ToolSwitch("Editar metadados", editing, enabled = !busy) { editing = it }
            for ((key, label) in listOf(
                "title" to "Música",
                "artists" to "Artistas (separados por ;)",
                "album" to "Álbum"
            )) {
                val text = if (key ==
                    "artists"
                ) changes.optJSONArray(key)?.let { a ->
                    (0 until a.length()).joinToString("; ") { a.optString(it) }
                }
                    ?: "" else changes.optString(key)
                OutlinedTextField(
                    text,
                    { value ->
                        changes =
                            JSONObject(changes.toString()).put(
                                key,
                                if (key ==
                                    "artists"
                                ) org.json.JSONArray(
                                    value.split(';').map {
                                        it.trim()
                                    }.filter { it.isNotBlank() }
                                ) else value
                            )
                    },
                    label = { UiText(label) },
                    singleLine = true,
                    enabled =
                    editing && !busy,
                    modifier = Modifier.fillMaxWidth()
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                for ((key, label) in listOf("release_date" to "Data", "track_number" to "Faixa"))OutlinedTextField(
                    changes.optString(key),
                    {
                        changes =
                            JSONObject(changes.toString()).put(key, it)
                    },
                    label = { UiText(label) },
                    singleLine = true,
                    enabled =
                    editing && !busy,
                    modifier = Modifier.weight(1f)
                )
            }
            TextButton(onClick = {
                moreTags = !moreTags
            }) { UiText(if (moreTags) "Menos informações" else "Mais informações") }
            if (moreTags) {
                for ((key, label) in listOf("album_artist" to "Artista do álbum", "composer" to "Compositor")) {
                    OutlinedTextField(
                        changes.optString(key),
                        {
                            changes = JSONObject(changes.toString()).put(key, it)
                        },
                        label = { UiText(label) },
                        enabled =
                        editing && !busy,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                OutlinedTextField(
                    changes.optString("genre"),
                    {
                        changes = JSONObject(changes.toString()).put("genre", it)
                    },
                    label = { UiText("Gênero") },
                    singleLine = true,
                    enabled =
                    editing && !busy,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    changes.optString("disc_number"),
                    {
                        changes =
                            JSONObject(changes.toString()).put("disc_number", it)
                    },
                    label = { UiText("Disco") },
                    singleLine = true,
                    enabled =
                    editing && !busy,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
        ToolCard {
            TextButton(onClick = {
                pickLyrics.launch(arrayOf("*/*"))
            }, enabled = !busy) { UiText(if (lyrics.isBlank()) "Importar letra · TXT ou LRC" else "Letra selecionada") }
            ToolSwitch("Normalizar volume (−16 LUFS)", normalize, enabled = !busy) { normalize = it }
            Row {
                TextButton(onClick = {
                    vm.preview(source, 20)
                }, enabled = source.isNotBlank() && !busy) { UiText("Ouvir original") }
                TextButton(onClick = {
                    vm.stopPreview()
                    vm.operation("normalize_preview", config(), dialog = false) {
                        preview =
                            it.getString("path")
                        vm.preview(preview, 20)
                    }
                }, enabled = source.isNotBlank() && !busy) { UiText("Ouvir normalizado") }
            }
            PlayerControls(vm)
        }
        ToolCard {
            ToolSwitch("Substituir original", overwrite, enabled = !busy) { overwrite = it }
            UiText(
                if (overwrite) "O arquivo original será substituído, mantendo o nome e a pasta." else "O arquivo original será preservado. Uma cópia será salva na pasta de destino.",
                style = MaterialTheme.typography.bodySmall
            )
        }
        Button(enabled = loaded && !busy, onClick = {
            vm.operation("audio_edit", config(), dialog = false) {
                if (!it.optBoolean("cancelled")) {
                    if (overwrite) finish()
                    vm.status.value =
                        if (overwrite) "Arquivo original atualizado." else "Cópia editada salva na pasta de destino."
                }
            }
        }, modifier = Modifier.fillMaxWidth()) { UiText("Revisar e salvar") }
        Spacer(Modifier.height(LayoutSpacing.section))
    }
}

@Composable private fun ScheduleTimeButton(
    label: String,
    value: String,
    fallback: String,
    modifier: Modifier = Modifier,
    onChange: (String) -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val time = runCatching { java.time.LocalTime.parse(value) }.getOrElse { java.time.LocalTime.parse(fallback) }
    var open by remember { mutableStateOf(false) }
    Column(modifier) {
        UiText(label, style = MaterialTheme.typography.labelMedium)
        OutlinedButton(onClick = {
            open = true
        }, modifier = Modifier.fillMaxWidth()) {
            Text(time.format(java.time.format.DateTimeFormatter.ofPattern("HH:mm")))
        }
    }
    if (open) DisposableEffect(context) {
        val dialog = android.app.TimePickerDialog(context, { _, hour, minute ->
            onChange(String.format(java.util.Locale.ROOT, "%02d:%02d", hour, minute))
            open = false
        }, time.hour, time.minute, true)
        dialog.setOnDismissListener { open = false }
        dialog.show()
        onDispose {
            dialog.setOnDismissListener(null)
            dialog.dismiss()
        }
    }
}
