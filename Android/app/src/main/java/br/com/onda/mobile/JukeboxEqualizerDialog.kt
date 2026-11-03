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
import androidx.compose.ui.platform.testTag
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.*

@Composable internal fun JukeboxEqualizerDialog(onDismiss:()->Unit) {
    val original=remember {cleanEqualizerSettings(OndaStore.settings.value.optJSONObject("jukebox_equalizer"))}
    var enabled by remember {mutableStateOf(original.optBoolean("enabled"))}
    var preamp by remember {mutableFloatStateOf(original.getDouble("preamp").toFloat())}
    var bandCount by remember {mutableIntStateOf(original.getInt("band_count"))}
    val frequencies=remember {mutableStateListOf<Float>().apply {(0 until bandCount).forEach {add(original.getJSONArray("bands").getJSONObject(it).getDouble("frequency").toFloat())}}}
    val gains=remember {mutableStateListOf<Float>().apply {(0 until bandCount).forEach {add(original.getJSONArray("bands").getJSONObject(it).getDouble("gain").toFloat())}}}
    val widths=remember {mutableStateListOf<Float>().apply {(0 until bandCount).forEach {add(original.getJSONArray("bands").getJSONObject(it).getDouble("q").toFloat())}}}
    val presets=remember {JSONArray(OndaStore.context.assets.open("equalizer_presets.json").bufferedReader().use {it.readText()}).let {a->(0 until a.length()).map {a.getJSONObject(it)}}}
    val presetValues=remember(bandCount) {presets.associate {row->
        row.getString("name") to equalizerPreset(row,bandCount)
    }}
    val selectedPreset=presetValues.entries.firstOrNull {(_,value)->
        abs(preamp-value.getDouble("preamp").toFloat())<.01f && (0 until bandCount).all {i->
            val reference=value.getJSONArray("bands").getJSONObject(i)
            abs(gains[i]-reference.getDouble("gain").toFloat())<.01f && abs(frequencies[i]-reference.getDouble("frequency").toFloat())<.01f && abs(widths[i]-reference.getDouble("q").toFloat())<.01f
        }
    }?.key ?: "Personalizado"
    var expanded by remember {mutableIntStateOf(-1)}
    fun current()=JSONObject().put("enabled",enabled).put("preamp",preamp).put("band_count",bandCount).put("bands",JSONArray().apply {
        (0 until bandCount).forEach {i->put(JSONObject().put("frequency",frequencies[i]).put("gain",gains[i]).put("q",widths[i]))}
    })
    fun save() {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("jukebox_equalizer",current()))}
    fun replace(value:JSONObject) {
        val clean=cleanEqualizerSettings(value);val bands=clean.getJSONArray("bands")
        enabled=clean.getBoolean("enabled");preamp=clean.getDouble("preamp").toFloat();expanded=-1
        frequencies.clear();gains.clear();widths.clear()
        for(i in 0 until bands.length()) {val row=bands.getJSONObject(i);frequencies.add(row.getDouble("frequency").toFloat());gains.add(row.getDouble("gain").toFloat());widths.add(row.getDouble("q").toFloat())}
        bandCount=clean.getInt("band_count");save()
    }
    fun close(){save();onDismiss()}
    AlertDialog(onDismissRequest={close()},title={UiText("Equalizador")},text={
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Toggle("Ativar equalizador",enabled){enabled=it;save()}
            Select("Preset",selectedPreset,presetValues.keys.toList()+"Personalizado") {name->presetValues[name]?.let {replace(it)}}
            Select("Quantidade de bandas",bandCount.toString(),equalizerLayouts.keys.map {it.toString()},Modifier.testTag("equalizer-band-count")) {choice->
                val count=choice.toInt()
                val preset=presets.firstOrNull {it.getString("name")==selectedPreset}
                replace(if(preset!=null)equalizerPreset(preset,count).put("enabled",enabled) else resizeEqualizerSettings(current(),count))
            }
            UiText("Os ajustes são adaptados às novas frequências ao mudar a quantidade de bandas.",style=MaterialTheme.typography.bodySmall)
            UiText(translateUi("Pré-amplificação")+" · %.1f dB".format(preamp))
            RoundSlider(preamp,{preamp=it},valueRange=-24f..0f,onValueChangeFinished={save()})
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
            ) {
                (0 until bandCount).forEach {i->
                    Column(Modifier.width(56.dp).testTag("equalizer-band-$i"),horizontalAlignment=Alignment.CenterHorizontally) {
                        UiText("%+.1f".format(gains[i]),style=MaterialTheme.typography.labelSmall)
                        RoundSlider(gains[i],{if(i<gains.size)gains[i]=it},valueRange=-12f..12f,onValueChangeFinished={save()},modifier=Modifier
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
            if(expanded in 0 until bandCount) {
                val i=expanded
                UiText("${i+1} · "+translateUi("Frequência (Hz)")+" · %.0f".format(frequencies[i]))
                RoundSlider(log10(frequencies[i]),{frequencies[i]=10f.pow(it)},valueRange=log10(20f)..log10(20000f),onValueChangeFinished={save()})
                UiText("Q · %.2f".format(widths[i]))
                RoundSlider(widths[i],{widths[i]=it},valueRange=.1f..10f,onValueChangeFinished={save()})
            }
            UiText("Q menor: banda mais larga. Reduza a pré-amplificação ao aumentar os ganhos.",style=MaterialTheme.typography.bodySmall)
        }
    },confirmButton={TextButton(onClick={close()}){UiText("Pronto")}},dismissButton={TextButton(onClick={
        replace(JSONObject().put("enabled",enabled).put("band_count",bandCount).put("preamp",-6))
    }){UiText("Restaurar")}})
}
