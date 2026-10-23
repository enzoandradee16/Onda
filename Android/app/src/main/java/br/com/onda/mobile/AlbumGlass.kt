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

internal fun albumDominantColor(pixels:IntArray):Color? {
    val bins=mutableMapOf<Int,Double>()
    for(pixel in pixels) {
        if((pixel ushr 24)<128)continue
        val r=(pixel ushr 16)and 255;val g=(pixel ushr 8)and 255;val b=pixel and 255
        val chroma=(maxOf(r,g,b)-minOf(r,g,b))/255.0
        val key=((r/16)shl 8) or ((g/16)shl 4) or (b/16)
        bins[key]=(bins[key] ?: 0.0)+.25+chroma
    }
    val key=bins.maxByOrNull {it.value}?.key ?: return null
    return Color(((key shr 8)and 15)*16+8,((key shr 4)and 15)*16+8,(key and 15)*16+8)
}

internal data class AlbumGlassColors(val base:Color,val top:Color,val bottom:Color,val ink:Color,val secondary:Color,val highContrast:Boolean)
internal fun albumGlassColors(accent:Color,dark:Boolean,highContrast:Boolean):AlbumGlassColors {
    val anchor=if(dark)Color.Black else Color.White
    val base=lerp(accent.copy(alpha=1f),anchor,if(highContrast).90f else if(dark).76f else .86f)
    val ink=if(dark)Color.White else Color.Black
    return AlbumGlassColors(base,lerp(base,Color.White,if(highContrast).02f else .08f),lerp(base,anchor,.05f),ink,if(highContrast)ink else lerp(base,ink,.86f),highContrast)
}

/** Album-tinted glass: blurred artwork under a translucent lens and a specular rim. */
@Composable internal fun AlbumGlass(artwork:Any?,modifier:Modifier=Modifier,content:@Composable (AlbumGlassColors)->Unit) {
    val context=LocalContext.current
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val scheme=MaterialTheme.colorScheme
    val dark=scheme.surface.luminance()<.5f
    val highContrast=settings.optString("theme")=="Alto contraste"
    val fallback=scheme.primary
    val tint=rememberAlbumAccent(artwork)
    val colors=remember(tint,fallback,dark,highContrast){albumGlassColors(tint ?: fallback,dark,highContrast)}
    val shape=RoundedCornerShape(16.dp)
    Surface(modifier,shape=shape,color=Color.Transparent,contentColor=colors.ink,shadowElevation=if(highContrast)0.dp else 5.dp) {
        Box(Modifier.clip(shape).background(colors.base).border(BorderStroke(if(highContrast)2.dp else 1.dp,Brush.verticalGradient(listOf(colors.ink.copy(alpha=if(highContrast).9f else .38f),colors.ink.copy(alpha=if(highContrast).7f else .08f),colors.ink.copy(alpha=if(highContrast).9f else .22f)))),shape)) {
            if(artwork!=null)AsyncImage(artwork,null,Modifier.matchParentSize().blur(28.dp),contentScale=ContentScale.Crop,alpha=if(highContrast).02f else .10f)
            Box(Modifier.matchParentSize().background(Brush.linearGradient(listOf(colors.top.copy(alpha=.9f),colors.base.copy(alpha=.96f),colors.bottom.copy(alpha=.9f)))))
            Box(Modifier.matchParentSize().drawWithCache {
                val sheen=Brush.verticalGradient(listOf(Color.White.copy(alpha=if(highContrast).01f else .045f),Color.Transparent),endY=size.height*.55f)
                onDrawBehind {drawRect(sheen)}
            })
            content(colors)
        }
    }
}

@Composable internal fun rememberAlbumAccent(artwork:Any?):Color? {
    val context=LocalContext.current
    val tint by produceState<Color?>(null,artwork) {
        value=null
        if(artwork!=null) {
            value=withContext(Dispatchers.IO) {
                runCatching {
                    val result=context.imageLoader.execute(ImageRequest.Builder(context).data(artwork).size(64).allowHardware(false).build())
                    val bitmap=result.drawable?.toBitmap(64,64) ?: return@runCatching null
                    val pixels=IntArray(bitmap.width*bitmap.height)
                    bitmap.getPixels(pixels,0,bitmap.width,0,0,bitmap.width,bitmap.height)
                    // Coil may own this bitmap: let its memory cache manage the lifetime.
                    albumDominantColor(pixels)
                }.getOrNull()
            }
        }
    }
    return tint
}

internal fun albumLyricsColors(accent:Color,highContrast:Boolean):Pair<Color,Color> {
    var background=lerp(accent.copy(alpha=1f),Color.Black,.18f)
    if(highContrast)while(background.luminance()>.1f)background=lerp(background,Color.Black,.1f)
    val ink=if(background.luminance()>.179f)Color.Black else Color.White
    return background to ink
}

@Composable internal fun rememberLyricsColors(vm:OndaViewModel,source:String):Pair<Color,Color> {
    val info by vm.effectsInfo.collectAsStateWithLifecycle()
    val juke by vm.jukebox.state.collectAsStateWithLifecycle()
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    val model=juke.model?.takeIf {it.optString("source")==source}
    val details=info[source]
    val encoded=if(model!=null)model.optString("media_cover") else details?.optString("cover").orEmpty()
    val url=if(model!=null)model.optString("cover_url") else details?.optJSONObject("record")?.optString("cover_url").orEmpty()
    val artwork=remember(encoded,url){if(encoded.isNotBlank())runCatching {android.util.Base64.decode(encoded,android.util.Base64.DEFAULT)}.getOrNull() else url.takeIf {it.isNotBlank()}}
    val accent=rememberAlbumAccent(artwork)
    val scheme=MaterialTheme.colorScheme
    return if(accent==null)scheme.primaryContainer to scheme.onPrimaryContainer else albumLyricsColors(accent,settings.optString("theme")=="Alto contraste")
}
