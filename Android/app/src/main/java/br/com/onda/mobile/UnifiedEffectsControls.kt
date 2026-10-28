package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject

/** Effects and infinite navigation operate on the same source and PCM output. */
@Composable internal fun UnifiedEffectsControls(controller:JukeboxController,vm:OndaViewModel) {
    val effects by controller.effects.collectAsStateWithLifecycle()
    val state by controller.state.collectAsStateWithLifecycle()
    val presets=remember {linkedMapOf("Original" to (100 to 0),"Slowed leve" to (90 to 0),"Slowed intenso" to (75 to 0),"Sped Up leve" to (115 to 0),"Sped Up intenso" to (130 to 0),"Sped Up + Reverb" to (120 to 25),"Só Reverb" to (100 to 30),"Clássico" to (85 to 25),"Atmosférico" to (75 to 50))}
    val preset=presets.entries.firstOrNull {it.value.first==effects.optInt("speed",85)&&it.value.second==effects.optInt("reverb",25)}?.key ?: "Personalizado"
    var export by rememberSaveable {mutableStateOf(false)}
    var more by rememberSaveable {mutableStateOf(false)}
    var format by rememberSaveable {mutableStateOf("MP3")}
    ToolCard(Modifier.testTag("unified-effects-card")) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically) {
            Box(Modifier.weight(1f)){Toggle("Efeitos",effects.optBoolean("enabled")){controller.setEffects("enabled",it)}}
            IconButton(onClick={more=true}){OndaIcon("more-vertical","Mais ações",Modifier.size(22.dp))}
        }
        UiText("Velocidade · ${effects.optInt("speed",85)}%",style=MaterialTheme.typography.labelLarge)
        RoundSlider(effects.optInt("speed",85).toFloat(),{controller.setEffects("speed",it.toInt())},valueRange=50f..150f,slim=true,modifier=Modifier.fillMaxWidth().testTag("unified-effects-speed").a11yLabel("Velocidade da música","${effects.optInt("speed",85)}%"))
        UiText("Reverb · ${effects.optInt("reverb",25)}%",style=MaterialTheme.typography.labelLarge)
        RoundSlider(effects.optInt("reverb",25).toFloat(),{controller.setEffects("reverb",it.toInt())},valueRange=0f..100f,slim=true,modifier=Modifier.fillMaxWidth().testTag("unified-effects-reverb").a11yLabel("Intensidade do reverb","${effects.optInt("reverb",25)}%"))
        if(state.effectsPending)UiText("Preparando efeitos; a reprodução atual continua.",style=MaterialTheme.typography.bodySmall)
        if(state.effectsError.isNotBlank())Text(uiExceptionMessage(IllegalStateException(state.effectsError),"Não foi possível preparar os efeitos desta música."),style=MaterialTheme.typography.bodySmall)
    }
    if(more)AlertDialog(onDismissRequest={more=false},title={UiText("Efeitos")},text={Column {
        Select("Preset",preset,presets.keys.toList()){name->val pair=presets.getValue(name);controller.setEffects("speed",pair.first);controller.setEffects("reverb",pair.second)}
        Toggle("Manter tom",effects.optBoolean("keep_pitch")){controller.setEffects("keep_pitch",it)}
        TextButton(onClick={more=false;export=true},enabled=state.model!=null){UiText("Exportar música")}
    }},confirmButton={TextButton(onClick={more=false}){UiText("Pronto")}})
    if(export)AlertDialog(onDismissRequest={export=false},title={UiText("Exportar música")},text={
        Select("Salvar como",format,listOf("MP3","M4A","FLAC","WAV")){format=it}
    },confirmButton={TextButton(onClick={
        val source=state.model?.optString("source").orEmpty()
        if(source.isNotBlank()) {
            val model=state.model!!
            val queued=controller.playbackQueue.value.firstOrNull {it.optString("_queue_id")==controller.currentQueueId.value}
            val record=JSONObject(queued?.toString() ?: "{}").put("media_title",model.optString("media_title").ifBlank {state.title}).put("media_artist",model.optString("media_artist"))
            if(model.optString("album").isNotBlank())record.put("album",model.getString("album"))
            if(model.optString("cover_url").isNotBlank())record.put("cover_url",model.getString("cover_url"))
            val extension=format.lowercase()
            val payload=JSONObject(effects.toString()).put("source",source).put("record",record).put("cover_data",model.optString("media_cover").ifBlank {model.optString("_cover")})
            vm.operation("effects_export_config",payload) {result->
                val output=java.io.File(OndaStore.config().getString("folder"),result.getString("export_name")+"."+extension)
                val config=OndaStore.config().apply {result.keys().forEach {key->put(key,result.get(key))}}.put("output",output.absolutePath).put("_operation","effects")
                val id=OndaStore.enqueue(source,output.name,extra=config)
                DownloadService.start(OndaStore.context,id)
                vm.status.value="Exportação adicionada à fila. Acompanhe na aba Fila."
            }
        }
        export=false
    }){UiText("Exportar música")}},dismissButton={TextButton(onClick={export=false}){UiText("Cancelar")}})
}
