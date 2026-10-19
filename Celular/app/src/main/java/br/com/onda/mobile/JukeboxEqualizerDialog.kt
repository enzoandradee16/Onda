package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.layout
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.*

private val equalizerFrequencies=listOf(31.25f,62.5f,125f,250f,500f,1000f,2000f,4000f,8000f,16000f)

@Composable internal fun JukeboxEqualizerDialog(onDismiss:()->Unit) {
    val original=remember {OndaStore.settings.value.optJSONObject("jukebox_equalizer") ?: JSONObject()}
    var enabled by remember {mutableStateOf(original.optBoolean("enabled"))}
    var preamp by remember {mutableFloatStateOf(original.optDouble("preamp",-6.0).toFloat().let {if(it.isFinite())it.coerceIn(-24f,0f) else -6f})}
    val frequencies=remember {mutableStateListOf<Float>().apply {equalizerFrequencies.forEachIndexed {i,f->add(original.optJSONArray("bands")?.optJSONObject(i)?.optDouble("frequency",f.toDouble())?.toFloat()?.takeIf {it.isFinite()}?.coerceIn(20f,20000f) ?: f)}}}
    val gains=remember {mutableStateListOf<Float>().apply {equalizerFrequencies.indices.forEach {i->add(original.optJSONArray("bands")?.optJSONObject(i)?.optDouble("gain",0.0)?.toFloat()?.takeIf {it.isFinite()}?.coerceIn(-12f,12f) ?: 0f)}}}
    val widths=remember {mutableStateListOf<Float>().apply {equalizerFrequencies.indices.forEach {i->add(original.optJSONArray("bands")?.optJSONObject(i)?.optDouble("q",1.4)?.toFloat()?.takeIf {it.isFinite()}?.coerceIn(.1f,10f) ?: 1.4f)}}}
    var expanded by remember {mutableIntStateOf(-1)}
    fun save() {
        val value=JSONObject().put("enabled",enabled).put("preamp",preamp).put("bands",JSONArray().apply {
            equalizerFrequencies.indices.forEach {i->put(JSONObject().put("frequency",frequencies[i]).put("gain",gains[i]).put("q",widths[i]))}
        })
        OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("jukebox_equalizer",value))
    }
    fun close(){save();onDismiss()}
    AlertDialog(onDismissRequest={close()},title={UiText("Equalizador")},text={
        Column(Modifier.fillMaxWidth().heightIn(max=510.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Toggle("Ativar equalizador",enabled){enabled=it;save()}
            UiText(translateUi("Pré-amplificação")+" · %.1f dB".format(preamp))
            RoundSlider(preamp,{preamp=it},valueRange=-24f..0f,onValueChangeFinished={save()})
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(4.dp)) {
                equalizerFrequencies.indices.forEach {i->
                    Column(Modifier.width(56.dp),horizontalAlignment=Alignment.CenterHorizontally) {
                        UiText("%+.1f".format(gains[i]),style=MaterialTheme.typography.labelSmall)
                        RoundSlider(gains[i],{gains[i]=it},valueRange=-12f..12f,onValueChangeFinished={save()},modifier=Modifier
                            .width(48.dp).height(190.dp)
                            .graphicsLayer {rotationZ=270f}
                            .layout {measurable,constraints->
                                val child=measurable.measure(Constraints(minWidth=constraints.minHeight,maxWidth=constraints.maxHeight,minHeight=constraints.minWidth,maxHeight=constraints.maxWidth))
                                layout(child.height,child.width) {child.place((child.height-child.width)/2,(child.width-child.height)/2)}
                            })
                        TextButton(onClick={expanded=if(expanded==i)-1 else i},contentPadding=PaddingValues(0.dp)) {
                            UiText(if(frequencies[i]>=1000)"%.1fk".format(frequencies[i]/1000) else "%.0f".format(frequencies[i]),style=MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
            if(expanded>=0) {
                val i=expanded
                UiText("${i+1} · "+translateUi("Frequência (Hz)")+" · %.0f".format(frequencies[i]))
                RoundSlider(log10(frequencies[i]),{frequencies[i]=10f.pow(it)},valueRange=log10(20f)..log10(20000f),onValueChangeFinished={save()})
                UiText("Q · %.2f".format(widths[i]))
                RoundSlider(widths[i],{widths[i]=it},valueRange=.1f..10f,onValueChangeFinished={save()})
            }
            UiText("Q menor: banda mais larga. Reduza a pré-amplificação ao aumentar os ganhos.",style=MaterialTheme.typography.bodySmall)
        }
    },confirmButton={TextButton(onClick={close()}){UiText("Pronto")}},dismissButton={TextButton(onClick={
        equalizerFrequencies.forEachIndexed {i,f->frequencies[i]=f;gains[i]=0f;widths[i]=1.4f};preamp=-6f;save()
    }){UiText("Restaurar")}})
}
