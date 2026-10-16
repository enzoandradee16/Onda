package br.com.onda.mobile

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID
import kotlin.math.min
import kotlin.math.roundToInt

// Decode only a bounded preview; export never upscales the chosen crop.
internal fun loadCoverBitmap(path:String):Bitmap {
    val bounds=BitmapFactory.Options().apply {inJustDecodeBounds=true}
    BitmapFactory.decodeFile(path,bounds)
    require(bounds.outWidth>0 && bounds.outHeight>0) {"Não foi possível ler a imagem."}
    var sample=1
    while(maxOf(bounds.outWidth,bounds.outHeight)/sample>2048)sample*=2
    val bitmap=BitmapFactory.decodeFile(path,BitmapFactory.Options().apply {inSampleSize=sample})
        ?: error("Não foi possível ler a imagem.")
    val orientation=runCatching {ExifInterface(path).getAttributeInt(ExifInterface.TAG_ORIENTATION,1)}.getOrDefault(1)
    val matrix=Matrix().apply {
        when(orientation) {
            2->setScale(-1f,1f)
            3->setRotate(180f)
            4->setScale(1f,-1f)
            5->{setRotate(90f);postScale(-1f,1f)}
            6->setRotate(90f)
            7->{setRotate(270f);postScale(-1f,1f)}
            8->setRotate(270f)
        }
    }
    if(matrix.isIdentity)return bitmap
    return Bitmap.createBitmap(bitmap,0,0,bitmap.width,bitmap.height,matrix,true).also {if(it!==bitmap)bitmap.recycle()}
}

internal fun coverOffset(bitmap:Bitmap,zoom:Float,offset:Offset):Offset {
    val side=min(bitmap.width,bitmap.height)/zoom.coerceIn(1f,4f)
    return Offset(offset.x.coerceIn(-(bitmap.width-side)/2,(bitmap.width-side)/2),
        offset.y.coerceIn(-(bitmap.height-side)/2,(bitmap.height-side)/2))
}

internal fun saveCoverCrop(bitmap:Bitmap,zoom:Float,offset:Offset,destination:File) {
    val side=(min(bitmap.width,bitmap.height)/zoom.coerceIn(1f,4f)).roundToInt().coerceAtLeast(1)
    val position=coverOffset(bitmap,zoom,offset)
    val left=((bitmap.width-side)/2f-position.x).roundToInt().coerceIn(0,bitmap.width-side)
    val top=((bitmap.height-side)/2f-position.y).roundToInt().coerceIn(0,bitmap.height-side)
    val cropped=Bitmap.createBitmap(bitmap,left,top,side,side)
    val size=min(1200,side)
    val output=if(size==side)cropped else Bitmap.createScaledBitmap(cropped,size,size,true)
    try {destination.outputStream().use {check(output.compress(Bitmap.CompressFormat.PNG,100,it)) {"Não foi possível salvar a capa."}}}
    finally {if(output!==cropped)output.recycle();if(cropped!==bitmap)cropped.recycle()}
}

@Composable fun CoverCropper(path:String,onCancel:()->Unit,onApply:(String)->Unit) {
    val context=LocalContext.current
    val scope=rememberCoroutineScope()
    var bitmap by remember(path) {mutableStateOf<Bitmap?>(null)}
    var error by remember(path) {mutableStateOf("")}
    var zoom by androidx.compose.runtime.saveable.rememberSaveable(path) {mutableFloatStateOf(1f)}
    var x by androidx.compose.runtime.saveable.rememberSaveable(path) {mutableFloatStateOf(0f)}
    var y by androidx.compose.runtime.saveable.rememberSaveable(path) {mutableFloatStateOf(0f)}
    var width by remember {mutableIntStateOf(1)}
    var saving by remember {mutableStateOf(false)}
    LaunchedEffect(path) {
        runCatching {withContext(Dispatchers.IO) {loadCoverBitmap(path)}}.onSuccess {bitmap=it}.onFailure {error=it.message ?: "Não foi possível abrir a capa."}
    }
    Dialog(onDismissRequest={if(!saving)onCancel()},properties=DialogProperties(usePlatformDefaultWidth=false)) {
        Surface(shape=MaterialTheme.shapes.extraLarge,modifier=Modifier.fillMaxWidth().padding(LayoutSpacing.inset)) {
            Column(Modifier.padding(LayoutSpacing.inset).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.controls)) {
                UiText("Ajustar capa",style=MaterialTheme.typography.titleLarge)
                UiText("Arraste a imagem para mover e ajuste o zoom.",style=MaterialTheme.typography.bodySmall)
                val image=bitmap
                if(image==null && error.isBlank())CircularProgressIndicator()
                if(image!=null) {
                    val display=remember(image) {image.asImageBitmap()}
                    val cropLabel=translateUi("Área de recorte da capa",LocalUiLanguage.current)
                    val moveLeft=translateUi("Mover capa para a esquerda",LocalUiLanguage.current)
                    val moveRight=translateUi("Mover capa para a direita",LocalUiLanguage.current)
                    val moveUp=translateUi("Mover capa para cima",LocalUiLanguage.current)
                    val moveDown=translateUi("Mover capa para baixo",LocalUiLanguage.current)
                    fun move(dx:Float,dy:Float):Boolean {
                        val step=min(image.width,image.height)/zoom*.1f
                        val adjusted=coverOffset(image,zoom,Offset(x+dx*step,y+dy*step))
                        val moved=adjusted.x!=x || adjusted.y!=y
                        x=adjusted.x;y=adjusted.y
                        return moved
                    }
                    Canvas(Modifier.semantics {
                        contentDescription=cropLabel
                        if(!saving)customActions=listOf(
                            CustomAccessibilityAction(moveLeft){move(-1f,0f)},
                            CustomAccessibilityAction(moveRight){move(1f,0f)},
                            CustomAccessibilityAction(moveUp){move(0f,-1f)},
                            CustomAccessibilityAction(moveDown){move(0f,1f)})
                    }.fillMaxWidth().aspectRatio(1f).onSizeChanged {width=it.width}
                        .pointerInput(image,saving) {
                            if(!saving)detectTransformGestures {_,pan,factor,_->
                                val oldSide=min(image.width,image.height)/zoom
                                zoom=(zoom*factor).coerceIn(1f,4f)
                                val adjusted=coverOffset(image,zoom,Offset(x+pan.x*oldSide/width,y+pan.y*oldSide/width))
                                x=adjusted.x;y=adjusted.y
                            }
                        }) {
                        val offset=coverOffset(image,zoom,Offset(x,y))
                        val scale=size.width*zoom/min(image.width,image.height)
                        clipRect {
                            drawRect(Color(0xFF191F27))
                            drawImage(display,dstOffset=IntOffset(((size.width-image.width*scale)/2+offset.x*scale).roundToInt(),((size.height-image.height*scale)/2+offset.y*scale).roundToInt()),
                                dstSize=IntSize((image.width*scale).roundToInt(),(image.height*scale).roundToInt()))
                            for(fraction in listOf(1f/3,2f/3)) {
                                drawLine(Color.White.copy(alpha=.5f),Offset(size.width*fraction,0f),Offset(size.width*fraction,size.height))
                                drawLine(Color.White.copy(alpha=.5f),Offset(0f,size.height*fraction),Offset(size.width,size.height*fraction))
                            }
                        }
                    }
                    UiText("Zoom",style=MaterialTheme.typography.labelMedium)
                    Slider(value=zoom,onValueChange={zoom=it;val offset=coverOffset(image,zoom,Offset(x,y));x=offset.x;y=offset.y},valueRange=1f..4f,enabled=!saving,modifier=Modifier.a11yLabel("Zoom da capa","${(zoom*100).toInt()}%"))
                }
                if(error.isNotBlank())UiText(error,color=MaterialTheme.colorScheme.error)
                if(saving)LinearProgressIndicator(Modifier.fillMaxWidth())
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    TextButton(onClick={zoom=1f;x=0f;y=0f},enabled=!saving){UiText("Redefinir")}
                    TextButton(onClick=onCancel,enabled=!saving){UiText("Cancelar")}
                }
                Button(enabled=image!=null && !saving,onClick={
                    saving=true;error=""
                    val destination=File(context.cacheDir,"cover-crop-${UUID.randomUUID()}.png")
                    scope.launch {
                        runCatching {withContext(Dispatchers.IO) {saveCoverCrop(image!!,zoom,Offset(x,y),destination)}}
                            .onSuccess {onApply(destination.absolutePath)}
                            .onFailure {destination.delete();error=it.message ?: "Não foi possível salvar a capa."}
                        saving=false
                    }
                },modifier=Modifier.fillMaxWidth()){UiText("Aplicar capa")}
            }
        }
    }
}
