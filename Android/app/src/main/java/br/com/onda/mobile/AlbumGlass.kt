package br.com.onda.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.graphics.drawable.toBitmap
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import coil.imageLoader
import coil.request.ImageRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

internal fun albumDominantColor(pixels: IntArray): Color? {
    val bins = mutableMapOf<Int, Double>()
    for (pixel in pixels) {
        if ((pixel ushr 24) < 128) continue
        val r = (pixel ushr 16) and 255
        val g = (pixel ushr 8) and 255
        val b = pixel and 255
        val chroma = (maxOf(r, g, b) - minOf(r, g, b)) / 255.0
        val key = ((r / 16) shl 8) or ((g / 16) shl 4) or (b / 16)
        bins[key] = (bins[key] ?: 0.0) + .25 + chroma
    }
    val key = bins.maxByOrNull { it.value }?.key ?: return null
    return Color(((key shr 8) and 15) * 16 + 8, ((key shr 4) and 15) * 16 + 8, (key and 15) * 16 + 8)
}

internal data class AlbumGlassColors(
    val base: Color,
    val top: Color,
    val bottom: Color,
    val ink: Color,
    val secondary: Color,
    val highContrast: Boolean
)

@Suppress("UNUSED_PARAMETER")
internal fun albumGlassColors(accent: Color, dark: Boolean, highContrast: Boolean): AlbumGlassColors {
    var base = lerp(accent.copy(alpha = 1f), Color.Black, if (highContrast) .90f else .22f)
    val lightCover = !highContrast && base.luminance() > .30f
    if (lightCover) while (base.luminance() < .32f)base = lerp(base, Color.White, .05f)
    else while (base.luminance() > .09f)base = lerp(base, Color.Black, .07f)
    val ink = if (lightCover) Color.Black else Color.White
    return AlbumGlassColors(
        base,
        lerp(base, Color.White, if (highContrast) .02f else .03f),
        lerp(base, Color.Black, .04f),
        ink,
        if (highContrast) ink else lerp(base, ink, .90f),
        highContrast
    )
}

@Composable internal fun rememberPlaybackBackgroundAccent(artwork: Any?, settings: org.json.JSONObject): Color? =
    if (settings.optBoolean("album_player_background", true)) {
        rememberAlbumAccent(artwork, keepPreviousWhileLoading = true)
    } else if (settings.optString("theme") != "Alto contraste") {
        normalizeAccent(settings.optString("theme_background"))?.let { hex ->
            Color(0xFF000000 or hex.removePrefix("#").toLong(16))
        }
    } else null

@Composable internal fun rememberAnimatedPlaybackTint(accent: Color?): Color {
    val target = accent ?: Color.Transparent
    return androidx.compose.animation.animateColorAsState(
        target, androidx.compose.animation.core.tween(durationMillis = 700), label = "playbackTint"
    ).value
}

internal fun playbackTintedScheme(
    base: androidx.compose.material3.ColorScheme,
    accent: Color,
    highContrast: Boolean,
    followAlbumAccent: Boolean = false
): androidx.compose.material3.ColorScheme {
    if (accent.alpha == 0f) return base
    val tint = accent.copy(alpha = 1f)
    val strength = if (highContrast) .25f else 1f
    fun readable(color: Color, amount: Float, ink: Color, secondary: Color = ink): Color {
        var weight = amount * strength * accent.alpha
        repeat(5) {
            val result = lerp(color, tint, weight)
            if (accentContrast(result, ink) >= 4.5f && accentContrast(result, secondary) >= 4.5f) return result
            weight *= .5f
        }
        return color
    }
    fun surface(color: Color, amount: Float) =
        readable(color, amount, base.onSurface, base.onSurfaceVariant)

    val surfaces = base.copy(
        background = readable(base.background, .36f, base.onBackground, base.onSurfaceVariant),
        surface = surface(base.surface, .25f),
        surfaceDim = surface(base.surfaceDim, .30f),
        surfaceBright = surface(base.surfaceBright, .22f),
        surfaceVariant = surface(base.surfaceVariant, .25f),
        surfaceContainerLowest = surface(base.surfaceContainerLowest, .25f),
        surfaceContainerLow = surface(base.surfaceContainerLow, .28f),
        surfaceContainer = surface(base.surfaceContainer, .30f),
        surfaceContainerHigh = surface(base.surfaceContainerHigh, .29f),
        surfaceContainerHighest = surface(base.surfaceContainerHighest, .25f),
        primaryContainer = readable(base.primaryContainer, .18f, base.onPrimaryContainer),
        secondary = readable(base.secondary, .08f, base.onSecondary),
        secondaryContainer = readable(base.secondaryContainer, .23f, base.onSecondaryContainer),
        tertiary = readable(base.tertiary, .08f, base.onTertiary),
        tertiaryContainer = readable(base.tertiaryContainer, .18f, base.onTertiaryContainer)
    )
    if (!followAlbumAccent || highContrast) return surfaces
    val dark = base.background.luminance() < .5f
    val endpoint = if (dark) Color.White else Color.Black
    var primary = lerp(base.primary, tint, accent.alpha)
    repeat(48) {
        if (accentContrast(primary, surfaces.background) >= 4.5f &&
            accentContrast(primary, surfaces.surface) >= 4.5f &&
            accentContrast(primary, surfaces.surfaceContainer) >= 4.5f
        ) return surfaces.copy(primary = primary, onPrimary = accentInk(primary))
        primary = lerp(primary, endpoint, .12f)
    }
    return surfaces.copy(primary = endpoint, onPrimary = accentInk(endpoint))
}

/** Album-tinted glass: blurred artwork under a translucent lens and a specular rim. */
@Composable internal fun AlbumGlass(artwork: Any?, modifier: Modifier = Modifier, content: @Composable (AlbumGlassColors) -> Unit) {
    val context = LocalContext.current
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val scheme = MaterialTheme.colorScheme
    val dark = scheme.surface.luminance() < .5f
    val highContrast = settings.optString("theme") == "Alto contraste"
    val fallback = Color(0xFF34404D)
    val accent = rememberPlaybackBackgroundAccent(artwork, settings)
    val tint = rememberAnimatedPlaybackTint(accent ?: fallback)
    val colors = remember(tint, dark, highContrast) { albumGlassColors(tint, dark, highContrast) }
    val shape = RoundedCornerShape(16.dp)
    Surface(
        modifier,
        shape = shape,
        color = Color.Transparent,
        contentColor = colors.ink,
        shadowElevation = if (highContrast) 0.dp else 5.dp
    ) {
        Box(
            Modifier.clip(
                shape
            ).background(
                colors.base
            ).border(
                BorderStroke(
                    if (highContrast) 2.dp else 1.dp,
                    Brush.verticalGradient(
                        listOf(
                            colors.ink.copy(alpha = if (highContrast) .9f else .38f),
                            colors.ink.copy(alpha = if (highContrast) .7f else .08f),
                            colors.ink.copy(alpha = if (highContrast) .9f else .22f)
                        )
                    )
                ),
                shape
            )
        ) {
            if (artwork !=
                null
            ) AsyncImage(
                artwork,
                null,
                Modifier.matchParentSize().blur(28.dp),
                contentScale = ContentScale.Crop,
                alpha = if (highContrast) .02f else .10f
            )
            Box(
                Modifier.matchParentSize().background(
                    Brush.linearGradient(
                        listOf(
                            colors.top.copy(alpha = .9f),
                            colors.base.copy(alpha = .96f),
                            colors.bottom.copy(alpha = .9f)
                        )
                    )
                )
            )
            Box(
                Modifier.matchParentSize().drawWithCache {
                    val sheen = Brush.verticalGradient(
                        listOf(Color.White.copy(alpha = if (highContrast) .01f else .045f), Color.Transparent),
                        endY =
                        size.height * .55f
                    )
                    onDrawBehind { drawRect(sheen) }
                }
            )
            MaterialTheme(
                colorScheme = scheme.copy(
                    primary = colors.ink,
                    onPrimary = colors.base,
                    onSurface = colors.ink,
                    onSurfaceVariant = colors.secondary
                )
            ) {
                content(colors)
            }
        }
    }
}

@Composable internal fun rememberAlbumAccent(artwork: Any?, keepPreviousWhileLoading: Boolean = false): Color? {
    val context = LocalContext.current
    val tint by produceState<Color?>(null, artwork, keepPreviousWhileLoading) {
        if (artwork == null || !keepPreviousWhileLoading) value = null
        if (artwork != null) {
            value = withContext(Dispatchers.IO) {
                runCatching {
                    val result = context.imageLoader.execute(
                        ImageRequest.Builder(context).data(artwork).size(64).allowHardware(false).build()
                    )
                    val bitmap = result.drawable?.toBitmap(64, 64) ?: return@runCatching null
                    val pixels = IntArray(bitmap.width * bitmap.height)
                    bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
                    // Coil may own this bitmap: let its memory cache manage the lifetime.
                    albumDominantColor(pixels)
                }.getOrNull()
            }
        }
    }
    return tint
}

internal fun albumLyricsColors(accent: Color, highContrast: Boolean): Pair<Color, Color> {
    var background = lerp(accent.copy(alpha = 1f), Color.Black, .18f)
    if (highContrast) while (background.luminance() > .1f)background = lerp(background, Color.Black, .1f)
    val ink = if (background.luminance() > .179f) Color.Black else Color.White
    return background to ink
}

@Composable internal fun rememberArtworkForSource(vm: OndaViewModel, source: String, restored: org.json.JSONObject? = null): Any? {
    val info by vm.effectsInfo.collectAsStateWithLifecycle()
    val juke by vm.jukebox.presentationState.collectAsStateWithLifecycle()
    val model = juke.model?.takeIf { it.optString("source") == source }
    val details = info[source]
    val encoded = model?.optString("media_cover").orEmpty().ifBlank { details?.optString("cover").orEmpty() }.ifBlank { restored?.optString("_cover").orEmpty() }
    val url = model?.optString("cover_url").orEmpty()
        .ifBlank { details?.optJSONObject("record")?.optString("cover_url").orEmpty() }
        .ifBlank { restored?.optString("cover_url").orEmpty() }
    return remember(encoded, url) {
        encoded.takeIf { it.isNotBlank() }?.let {
            runCatching { android.util.Base64.decode(it, android.util.Base64.DEFAULT) }.getOrNull()
        } ?: url.takeIf { it.isNotBlank() }
    }
}

@Composable internal fun rememberLyricsColors(vm: OndaViewModel, source: String): Pair<Color, Color> {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val accent = rememberPlaybackBackgroundAccent(rememberArtworkForSource(vm, source), settings)
    val scheme = MaterialTheme.colorScheme
    return if (accent ==
        null
    ) scheme.primaryContainer to scheme.onPrimaryContainer else albumLyricsColors(
        accent,
        settings.optString("theme") == "Alto contraste"
    )
}
