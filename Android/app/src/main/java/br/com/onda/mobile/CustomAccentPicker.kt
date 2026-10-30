package br.com.onda.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog

@Composable internal fun AccentPreference(value: String, modifier: Modifier = Modifier, changed: (String) -> Unit) {
    var editing by remember { mutableStateOf(false) }
    val custom=normalizeAccent(value)
    Column(modifier) {
        Select("Cor de destaque", if(custom!=null)CUSTOM_ACCENT else value, accents.keys.toList()+CUSTOM_ACCENT) {
            if(it==CUSTOM_ACCENT)editing=true else changed(it)
        }
        if(custom!=null) TextButton(onClick={editing=true},modifier=Modifier.testTag("edit-custom-accent")) {Text(custom);Spacer(Modifier.width(8.dp));UiText("Editar")}
    }
    if(editing)CustomAccentDialog(custom ?: resolvedAccent(value,MaterialTheme.colorScheme.background.luminance()<.5f).hexRgb(),{editing=false}) {
        changed(it);editing=false
    }
}

@Composable private fun CustomAccentDialog(initial: String, dismiss: () -> Unit, apply: (String) -> Unit) {
    val start=remember {accentHsv(Color(0xFF000000 or initial.removePrefix("#").toLong(16)))}
    var hue by remember {mutableFloatStateOf(start[0])}
    var saturation by remember {mutableFloatStateOf(start[1])}
    var brightness by remember {mutableFloatStateOf(start[2])}
    var hex by remember {mutableStateOf(initial)}
    val valid=normalizeAccent(hex)
    val dark=MaterialTheme.colorScheme.background.luminance()<.5f
    val highContrast=OndaStore.settings.value.optString("theme")=="Alto contraste"
    val preview=if(highContrast)Color.Yellow else valid?.let {readableCustomAccent(it,dark)} ?: MaterialTheme.colorScheme.primary
    fun writeHex(){hex=Color.hsv(hue,saturation,brightness).hexRgb()}
    Dialog(onDismissRequest=dismiss) {
        Surface(shape=RoundedCornerShape(24.dp),color=ondaDialogContainerColor(),modifier=Modifier.fillMaxWidth().testTag("custom-accent-dialog")) {
            Column(Modifier.heightIn(max=640.dp).verticalScroll(rememberScrollState()).padding(20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
                UiText("Cor personalizada",style=MaterialTheme.typography.titleLarge)
                AccentPlane(hue,saturation,brightness) {s,v->saturation=s;brightness=v;writeHex()}
                UiText("Matiz",style=MaterialTheme.typography.labelMedium)
                AccentHue(hue) {hue=it;writeHex()}
                OutlinedTextField(hex,{value->
                    hex=value
                    normalizeAccent(value)?.let {
                        val hsv=accentHsv(Color(0xFF000000 or it.removePrefix("#").toLong(16)))
                        hue=hsv[0];saturation=hsv[1];brightness=hsv[2]
                    }
                },label={UiText("Hexadecimal")},singleLine=true,isError=valid==null,
                    supportingText={if(valid==null)UiText("Use o formato #RRGGBB.")},modifier=Modifier.fillMaxWidth().testTag("custom-accent-hex"))
                Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                    UiText("Prévia",modifier=Modifier.weight(1f))
                    Surface(color=preview,contentColor=accentInk(preview),shape=RoundedCornerShape(10.dp)) {
                        UiText("Texto de exemplo",modifier=Modifier.padding(horizontal=16.dp,vertical=12.dp))
                    }
                }
                UiText("A tonalidade pode ser ajustada para manter o contraste.",style=MaterialTheme.typography.bodySmall)
                UiText("O ícone da tela inicial usa a cor predefinida mais próxima.",style=MaterialTheme.typography.bodySmall)
                Row(Modifier.align(Alignment.End),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick=dismiss){UiText("Cancelar")}
                    Button(onClick={valid?.let(apply)},enabled=valid!=null,modifier=Modifier.testTag("apply-custom-accent")){UiText("Aplicar cor")}
                }
            }
        }
    }
}

@Composable private fun AccentPlane(hue: Float, saturation: Float, brightness: Float, pick: (Float,Float) -> Unit) {
    val latest by rememberUpdatedState(pick)
    Canvas(Modifier.fillMaxWidth().height(160.dp).testTag("custom-accent-plane").pointerInput(Unit) {
        awaitEachGesture {
            fun select(position:Offset){latest((position.x/size.width).coerceIn(0f,1f),1-(position.y/size.height).coerceIn(0f,1f))}
            val down=awaitFirstDown();select(down.position);down.consume()
            drag(down.id){select(it.position);it.consume()}
        }
    }) {
        drawRect(Color.hsv(hue,1f,1f))
        drawRect(Brush.horizontalGradient(listOf(Color.White,Color.Transparent)))
        drawRect(Brush.verticalGradient(listOf(Color.Transparent,Color.Black)))
        val center=Offset(saturation*size.width,(1-brightness)*size.height)
        drawCircle(Color.Black,8.dp.toPx(),center,style=Stroke(3.dp.toPx()))
        drawCircle(Color.White,8.dp.toPx(),center,style=Stroke(1.5.dp.toPx()))
    }
}

@Composable private fun AccentHue(hue: Float, pick: (Float) -> Unit) {
    val latest by rememberUpdatedState(pick)
    Canvas(Modifier.fillMaxWidth().height(28.dp).testTag("custom-accent-hue").pointerInput(Unit) {
        awaitEachGesture {
            fun select(position:Offset){latest((position.x/size.width).coerceIn(0f,1f)*360f)}
            val down=awaitFirstDown();select(down.position);down.consume()
            drag(down.id){select(it.position);it.consume()}
        }
    }) {
        drawRect(Brush.horizontalGradient(listOf(Color.Red,Color.Yellow,Color.Green,Color.Cyan,Color.Blue,Color.Magenta,Color.Red)))
        val center=Offset(hue/360*size.width,size.height/2)
        drawCircle(Color.Black,9.dp.toPx(),center,style=Stroke(3.dp.toPx()))
        drawCircle(Color.White,9.dp.toPx(),center,style=Stroke(1.5.dp.toPx()))
    }
}
