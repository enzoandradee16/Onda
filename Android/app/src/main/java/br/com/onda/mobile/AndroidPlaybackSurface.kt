package br.com.onda.mobile

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInRoot
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage

/** One compact player across navigation; expanding never transfers audio between tabs. */
@Composable internal fun AndroidPlaybackSurface(vm: OndaViewModel, queueIsVisible: Boolean = false) {
    val remote by RemotePlaybackRuntime.presentationState.collectAsStateWithLifecycle()
    if (remote.connected) {
        RemotePlaybackSurface(remote, vm, queueIsVisible)
        return
    }
    val mode by vm.playbackMode.collectAsStateWithLifecycle()
    val fxSource by vm.effectsSource.collectAsStateWithLifecycle()
    val infos by vm.effectsInfo.collectAsStateWithLifecycle()
    val fxMedia by EffectsPlaybackRuntime.state.collectAsStateWithLifecycle()
    val fxPosition by vm.effectsPosition.collectAsStateWithLifecycle()
    val fxPreparing by vm.effectsPreparing.collectAsStateWithLifecycle()
    val fxEnabled by vm.effectsPreviewEnabled.collectAsStateWithLifecycle()
    val fxQueue by vm.effectsPlaylist.collectAsStateWithLifecycle()
    val juke by vm.jukebox.presentationState.collectAsStateWithLifecycle()
    val jukeQueue by vm.jukebox.playbackQueue.collectAsStateWithLifecycle()
    val audioReady by vm.jukebox.audioReady.collectAsStateWithLifecycle()
    var expanded by rememberSaveable { mutableStateOf(false) }
    var expandedQueue by rememberSaveable { mutableStateOf(false) }
    var devices by remember { mutableStateOf(false) }
    LaunchedEffect(expanded) { if (!expanded) expandedQueue = false }
    var expandedJukebox by rememberSaveable { mutableStateOf(false) }
    var lastJukebox by rememberSaveable(mode, fxSource, juke.model?.optString("source")) {
        mutableStateOf(mode == 1 && juke.model != null)
    }
    LaunchedEffect(juke.playing, juke.paused, fxMedia?.playing, fxPreparing) {
        if (juke.playing && !juke.paused) lastJukebox = true
        else if (fxMedia?.playing == true || fxPreparing) lastJukebox = false
    }
    val useJukebox = true
    val currentId by vm.jukebox.currentQueueId.collectAsStateWithLifecycle()
    val restoredRow =
        remember(jukeQueue, currentId) { jukeQueue.firstOrNull { it.optString("_queue_id") == currentId } }
    val model = juke.model
    val source = if (useJukebox) model?.optString("source")?.takeIf { it.isNotBlank() }
        ?: restoredRow?.cleanString("_local_source")?.takeIf { it.isNotBlank() }
        ?: restoredRow?.cleanString("source_url").orEmpty() else fxSource
    SideEffect { vm.compactPlaybackMode.value = if (source.isBlank()) null else if (useJukebox) 1 else 0 }
    DisposableEffect(vm) { onDispose { vm.compactPlaybackMode.value = null } }
    if (source.isBlank()) return
    val localExpandedRequested by RemotePlaybackRuntime.localExpandedRequested.collectAsStateWithLifecycle()
    LaunchedEffect(localExpandedRequested) {
        if (localExpandedRequested) {
            expanded = true
            RemotePlaybackRuntime.localExpandedRequested.value = false
        }
    }
    val info = infos[fxSource]
    val record = info?.optJSONObject("record")
    val title = if (useJukebox) juke.title else record?.optString("title")?.ifBlank { importedAudioName(source) }
        ?: importedAudioName(source)
    val artist = if (useJukebox) model?.optString(
        "media_artist"
    ) ?: restoredRow?.stringList("artists").orEmpty() else record?.stringList("artists").orEmpty()
    val artwork = rememberArtworkForSource(vm, source, restoredRow.takeIf { useJukebox })
    val beats = model?.optJSONArray("beats")
    fun livePosition(): Double {
        val current = vm.jukebox.state.value
        return if (current.model ==
            null
        ) restoredRow?.optDouble(
            "_restore_seconds",
            0.0
        ) ?: 0.0 else vm.jukebox.sessionSeconds(current.model, current.index, current.phase.toDouble())
    }
    val duration = (
        if (useJukebox) model?.optDouble("duration", 0.0)
            ?: ((restoredRow?.optDouble("duration_ms", 0.0) ?: 0.0) / 1000.0) else info?.optDouble("duration", 0.0)
            ?: fxMedia?.duration
            ?: 0.0
        ).coerceAtLeast(0.0)
    val preparing = if (useJukebox) juke.busy ||
        (juke.playing && !juke.paused && model?.has("_stream") == true && !audioReady) else fxPreparing
    val playing = if (useJukebox) juke.playing && !juke.paused else fxEnabled
    val fxRepeat by vm.effectsRepeat.collectAsStateWithLifecycle()
    val fxShuffle by vm.effectsShuffle.collectAsStateWithLifecycle()
    val jukeRepeat by vm.jukebox.queueRepeat.collectAsStateWithLifecycle()
    val jukeShuffle by vm.jukebox.queueShuffle.collectAsStateWithLifecycle()
    val hasNext = if (useJukebox) (
        vm.jukebox.nextQueueIndex < jukeQueue.size ||
            jukeRepeat == "Todas" && jukeQueue.isNotEmpty()
        ) else (
        vm.effectsQueueIndex(source) +
            1 <
            fxQueue.size ||
            fxRepeat == "Todas" && fxQueue.isNotEmpty()
        )
    var menu by remember { mutableStateOf(false) }
    var pitchDialog by remember { mutableStateOf(false) }
    val effects by vm.jukebox.effects.collectAsStateWithLifecycle()
    val pitch = effects.optInt("pitch_shift", 0)
    var timer by remember { mutableStateOf(false) }
    var equalizer by remember { mutableStateOf(false) }
    fun toggle() {
        if (useJukebox) vm.jukebox.playPause() else vm.mediaToggleEffects()
    }
    fun previous() {
        if (useJukebox) vm.jukebox.previousTrack() else vm.mediaPreviousEffects()
    }
    fun next() {
        if (useJukebox) vm.jukebox.nextTrack() else vm.mediaNextEffects()
    }
    fun seek(seconds: Double) {
        if (useJukebox) vm.jukebox.seekSeconds(seconds)
        else vm.mediaSeekEffects(seconds)
    }
    fun openQueue() {
        if (useJukebox) {
            if (expanded) expandedQueue = !expandedQueue
            else if (queueIsVisible) vm.playbackQueueOpen.value = false
            else vm.openPlaybackQueue()
        } else vm.effectsQueueOpen.value = true
    }

    @Composable fun cover(modifier: Modifier, showBackdrop: Boolean = false) {
        val coverBackground = if (showBackdrop && artwork != null) {
            androidx.compose.ui.graphics.Color.Transparent
        } else MaterialTheme.colorScheme.surfaceContainerHighest
        Surface(modifier.clip(RoundedCornerShape(12.dp)), color = coverBackground) {
            if (artwork !=
                null
            ) AsyncImage(artwork, translateUi("Capa do álbum"), Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
            else Box(contentAlignment = Alignment.Center) { OndaIcon("album", modifier = Modifier.size(48.dp)) }
        }
    }
    AlbumGlass(
        artwork,
        Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp).testTag("android-compact-player")
    ) { glass ->
        Column {
            Row(
                Modifier.fillMaxWidth().clickable {
                    expandedJukebox = useJukebox
                    expanded = true
                }.testTag("compact-player-expand").padding(6.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                cover(Modifier.size(48.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        title,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.labelLarge
                    )
                    Text(
                        artist,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodySmall,
                        color = glass.secondary
                    )
                }
                LyricsButton(vm, source, {
                    livePosition()
                }, duration, ::seek, ::toggle, isPlaying = { playing }, title = title, artist = artist)
                IconButton(
                    onClick = ::openQueue,
                    modifier = Modifier.testTag("compact-player-queue"),
                    colors = IconButtonDefaults.iconButtonColors(
                        contentColor = if (queueIsVisible) MaterialTheme.colorScheme.primary else glass.ink
                    )
                ) {
                    OndaIcon("queue", if (queueIsVisible) "Fechar fila" else "Fila", Modifier.size(24.dp))
                }
                OutlinedIconButton(
                    onClick = ::toggle,
                    enabled = duration > 0,
                    modifier = Modifier.testTag("compact-player-toggle"),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary),
                    colors = IconButtonDefaults.outlinedIconButtonColors(
                        contentColor = glass.ink,
                        disabledContentColor = glass.ink.copy(alpha = if (glass.highContrast) 1f else .38f)
                    )
                ) {
                    if (preparing) CircularProgressIndicator(
                        Modifier.size(23.dp),
                        strokeWidth = 2.dp,
                        color = glass.ink
                    )
                    else OndaIcon(
                        if (playing) "pause" else "play",
                        if (playing) "Pausar" else "Reproduzir",
                        Modifier.size(26.dp)
                    )
                }
            }
            PlaybackClock(vm.jukebox) { position ->
                val buffered by vm.jukebox.streamBuffer.collectAsStateWithLifecycle()
                Row(
                    Modifier.fillMaxWidth().padding(
                        horizontal = 10.dp,
                        vertical = 3.dp
                    ).testTag("compact-player-times"),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        mediaClock(position.toLong()),
                        style = MaterialTheme.typography.labelSmall,
                        color = glass.secondary
                    )
                    Text(
                        mediaClock(duration.toLong()),
                        style = MaterialTheme.typography.labelSmall,
                        color = glass.secondary
                    )
                }
                Box(Modifier.fillMaxWidth().height(if (glass.highContrast) 3.dp else 2.dp)) {
                    LinearProgressIndicator(
                        progress = {
                            if (duration >
                                0
                            ) (
                                (
                                    if (model?.has("_stream") ==
                                        true
                                    ) buffered.second else duration
                                    ) / duration
                                ).toFloat().coerceIn(0f, 1f) else 0f
                        },
                        modifier = Modifier.fillMaxSize(),
                        color = MaterialTheme.colorScheme.primary.copy(
                            alpha = .35f
                        ),
                        trackColor = glass.ink.copy(alpha = if (glass.highContrast) .4f else .18f)
                    )
                    LinearProgressIndicator(
                        progress = {
                            if (duration >
                                0
                            ) (position / duration).toFloat().coerceIn(0f, 1f) else 0f
                        },
                        modifier = Modifier.fillMaxSize().testTag(
                            "compact-player-progress"
                        ),
                        color = MaterialTheme.colorScheme.primary,
                        trackColor = androidx.compose.ui.graphics.Color.Transparent
                    )
                }
            }
        }
    }
    val surface = MaterialTheme.colorScheme.surface
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val highContrast = settings.optString("theme") == "Alto contraste"
    val accent = rememberPlaybackBackgroundAccent(artwork, settings)
    val targetTop = remember(accent, surface, highContrast) {
        val dark = surface.luminance() < .5f
        val tint = accent ?: surface
        val source = if (accent != null && dark && !highContrast) {
            lerp(tint, androidx.compose.ui.graphics.Color.White, .24f)
        } else tint
        val strength = if (highContrast) .10f else if (dark) .85f else .34f
        val top = lerp(surface, source, strength)
        if (dark && top.luminance() > .16f) {
            var shade = top
            while (shade.luminance() > .16f) {
                shade = lerp(shade, androidx.compose.ui.graphics.Color.Black, .08f)
            }
            shade
        } else top
    }
    val readableTop by animateColorAsState(targetTop, tween(durationMillis = 700), label = "albumBackground")
    if (expanded) Dialog(onDismissRequest = {
        expanded = false
    }, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        ApplyPlayerSystemBars(readableTop, surface)
        val scroll = rememberScrollState()
        var viewportHeight by remember { mutableIntStateOf(0) }
        var viewportTop by remember { mutableFloatStateOf(0f) }
        var lyricsTop by remember(source) { mutableFloatStateOf(0f) }
        val lyricsStop = if (viewportHeight > 0 && lyricsTop > 0f) {
            ((lyricsTop - viewportTop) / viewportHeight).coerceIn(.10f, .99f)
        } else .80f
        val background = remember(readableTop, surface, lyricsStop) {
            Brush.verticalGradient(
                0f to readableTop,
                (lyricsStop * .90f) to lerp(surface, readableTop, .55f),
                lyricsStop to surface,
                1f to surface
            )
        }
        Surface(Modifier.fillMaxSize().testTag("android-expanded-player"), color = surface) {
            BoxWithConstraints(
                Modifier.fillMaxSize().background(background).onGloballyPositioned {
                    viewportHeight = it.size.height
                    viewportTop = it.positionInRoot().y
                }.windowInsetsPadding(WindowInsets.safeDrawing)
            ) {
                val artworkSize = (minOf(maxWidth * .89f, maxHeight * .46f) - 4.dp).coerceAtLeast(100.dp)
                Column(
                    Modifier.fillMaxSize().verticalScroll(scroll).padding(horizontal = 24.dp, vertical = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = {
                            expanded = false
                        }) { OndaIcon("down", "Recolher reprodução", Modifier.size(26.dp)) }
                        Spacer(Modifier.weight(1f))
                        ShufflePlaybackButton(if (useJukebox) jukeShuffle else fxShuffle, {
                            if (useJukebox) vm.jukebox.setQueueShuffle(it) else vm.effectsShuffle.value =
                                it
                        })
                        RepeatPlaybackButton(jukeRepeat, { vm.jukebox.queueRepeat.value = it })
                        Box {
                            IconButton(onClick = {
                                menu = true
                            }) { OndaIcon("more-vertical", "Mais", Modifier.size(24.dp)) }
                            DropdownMenu(menu, { menu = false }) {
                                DropdownMenuItem(text = { UiText("Parar") }, onClick = {
                                    menu = false
                                    if (useJukebox) vm.jukebox.stop() else vm.stopEffectsPlayback()
                                })
                                DropdownMenuItem(text = { UiText("Ajustes de reprodução") }, onClick = {
                                    menu = false
                                    expanded =
                                        false
                                    vm.playbackMode.value = if (useJukebox) 1 else 0
                                    vm.effectsNavigation.value = true
                                })
                                if (useJukebox) {
                                    DropdownMenuItem(text = { UiText("Ajustar tom") }, onClick = {
                                        menu = false
                                        pitchDialog = true
                                    })
                                    DropdownMenuItem(text = { UiText("Timer") }, onClick = {
                                        menu = false
                                        timer = true
                                    })
                                    DropdownMenuItem(text = { UiText("Equalizador") }, onClick = {
                                        menu = false
                                        equalizer = true
                                    })
                                }
                            }
                        }
                    }
                    cover(
                        Modifier.size(artworkSize).align(Alignment.CenterHorizontally).testTag("expanded-album-cover"),
                        showBackdrop = true
                    )
                    Column {
                        Text(title, style = MaterialTheme.typography.headlineSmall)
                        Text(
                            artist,
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    PlaybackClock(vm.jukebox) { position ->
                        val buffered by vm.jukebox.streamBuffer.collectAsStateWithLifecycle()
                        val marks by vm.jukebox.sectionMarks.collectAsStateWithLifecycle()
                        var dragged by remember(source) { mutableStateOf<Float?>(null) }
                        Column {
                            RoundSlider(
                                dragged ?: position.toFloat().coerceIn(0f, duration.toFloat().coerceAtLeast(1f)),
                                {
                                    dragged =
                                        it
                                },
                                valueRange = 0f..duration.toFloat().coerceAtLeast(1f),
                                enabled = duration > 0,
                                onValueChangeFinished = {
                                    dragged?.let { seek(it.toDouble()) }
                                    dragged =
                                        null
                                },
                                modifier = Modifier.fillMaxWidth().testTag(
                                    "expanded-player-timeline"
                                ).a11yLabel("Posição na música"),
                                slim = true,
                                markedPoints = marks,
                                onMarkedPointMoved = vm.jukebox::moveSectionPoint,
                                markedRange = if (marks.size == 2) {
                                    val end = marks[1].takeIf { it >= 0 } ?: duration
                                    val start = marks[0].coerceAtLeast(0.0)
                                    if (end - start >= .1) start.toFloat()..end.toFloat() else null
                                } else null,
                                bufferedRange = if (model?.has("_stream") ==
                                    true
                                ) buffered.first.toFloat()..buffered.second.toFloat() else 0f..duration.toFloat()
                            )
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                UiText(
                                    mediaClock(
                                        (
                                            dragged?.toDouble()
                                                ?: position
                                            ).toLong()
                                    ),
                                    style = MaterialTheme.typography.labelSmall
                                )
                                if (model != null) Row(verticalAlignment = Alignment.CenterVertically) {
                                    for (index in 0..1) {
                                        val marked = marks.getOrNull(index)?.let { it >= 0 } == true
                                        val label = if (index == 0) {
                                            if (marked) "Limpar início" else "Marcar início"
                                        } else if (marked) "Limpar fim" else "Marcar fim"
                                        IconButton(
                                            onClick = {
                                                if (index == 0) {
                                                    if (marked) vm.jukebox.clearSectionStart() else vm.jukebox.markSectionStart()
                                                } else {
                                                    if (marked) vm.jukebox.clearSectionEnd() else vm.jukebox.markSectionEnd()
                                                }
                                            },
                                            modifier = Modifier.size(40.dp).a11yLabel(label).testTag(
                                                if (index == 0) "expanded-player-mark-start" else "expanded-player-mark-end"
                                            )
                                        ) {
                                            Text(
                                                if (index == 0) "[" else "]",
                                                style = MaterialTheme.typography.titleLarge,
                                                color = if (marked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                                            )
                                        }
                                    }
                                    IconButton(
                                        enabled = marks.isNotEmpty(),
                                        onClick = vm.jukebox::clearSection,
                                        modifier = Modifier.size(40.dp)
                                    ) { OndaIcon("close", "Limpar trecho", Modifier.size(20.dp)) }
                                }
                                UiText(mediaClock(duration.toLong()), style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                    Row(
                        Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        LyricsButton(vm, source, {
                            livePosition()
                        }, duration, ::seek, ::toggle, isPlaying = { playing }, title = title, artist = artist)
                        IconButton(onClick = ::previous) { OndaIcon("previous", "Retroceder", Modifier.size(32.dp)) }
                        FilledIconButton(
                            onClick = ::toggle,
                            enabled = duration > 0,
                            modifier = Modifier.size(70.dp).testTag("expanded-player-toggle")
                        ) {
                            if (preparing) CircularProgressIndicator(
                                Modifier.size(30.dp),
                                strokeWidth = 3.dp,
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                            else OndaIcon(
                                if (playing) "pause" else "play",
                                if (playing) "Pausar" else "Reproduzir",
                                Modifier.size(36.dp)
                            )
                        }
                        IconButton(
                            onClick = ::next,
                            enabled = hasNext,
                            modifier = Modifier.testTag("expanded-player-next")
                        ) {
                            OndaIcon("next", "Avançar", Modifier.size(32.dp))
                        }
                        IconButton(onClick = ::openQueue, modifier = Modifier.testTag("expanded-player-queue")) {
                            OndaIcon("queue", "Fila", Modifier.size(26.dp))
                        }
                    }
                    FlowRow(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                        itemVerticalAlignment = Alignment.CenterVertically
                    ) {
                        PlaybackDeviceButton(onClick = { devices = true })
                        if (pitch != 0) TextButton(onClick = { pitchDialog = true }) {
                            val signed = if (pitch > 0) "+$pitch" else pitch.toString()
                            Text(translateUi("Tom") + " $signed st")
                        }
                    }
                    PlaybackClock(vm.jukebox) { position ->
                        LyricsPreviewCard(
                            vm, source, title, artist, position, duration, playing, ::seek, ::toggle,
                            modifier = Modifier.onGloballyPositioned { lyricsTop = it.positionInRoot().y }
                        )
                    }
                }
            }
        }
        // The sheet belongs to this dialog so it stays above the expanded player.
        if (useJukebox && expandedQueue) PlaybackQueueSheet(vm) { expandedQueue = false }
        if (devices) PlaybackDevicesSheet { devices = false }
        if (pitchDialog) AlertDialog(
            onDismissRequest = { pitchDialog = false },
            title = { UiText("Ajustar tom") },
            text = { PlaybackToneControl(pitch) { vm.jukebox.setEffects("pitch_shift", it) } },
            confirmButton = {
                TextButton(onClick = { pitchDialog = false }) { UiText("Pronto") }
            }
        )
        if (!useJukebox) EffectsQueueDrawer(vm)
    }
    if (!expanded || useJukebox) EffectsQueueDrawer(vm)
    if (timer) JukeboxTimerDialog(vm.jukebox) { timer = false }
    if (equalizer) JukeboxEqualizerDialog { equalizer = false }
}

@Composable internal fun PlaybackClock(controller: JukeboxController, content: @Composable (Double) -> Unit) {
    val clock by controller.state.collectAsStateWithLifecycle()
    content(controller.sessionSeconds(clock.model, clock.index, clock.phase.toDouble()))
}
