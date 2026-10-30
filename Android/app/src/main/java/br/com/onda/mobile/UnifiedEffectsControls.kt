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

internal val playbackEffectPresets=linkedMapOf("Original" to (100 to 0),"Slowed leve" to (90 to 0),"Slowed intenso" to (75 to 0),"Sped Up leve" to (115 to 0),"Sped Up intenso" to (130 to 0),"Sped Up + Reverb" to (120 to 25),"Só Reverb" to (100 to 30),"Clássico" to (85 to 25),"Atmosférico" to (75 to 50))

/** Effects and infinite navigation operate on the same source and PCM output. */
@Composable internal fun UnifiedEffectsControls(controller:JukeboxController,vm:OndaViewModel) {
    val effects by controller.effects.collectAsStateWithLifecycle()
    val state by controller.state.collectAsStateWithLifecycle()
    val presets=playbackEffectPresets
    val preset=presets.entries.firstOrNull {it.value.first==effects.optInt("speed",85)&&it.value.second==effects.optInt("reverb",25)}?.key ?: "Personalizado"
    var export by rememberSaveable {mutableStateOf(false)}
    var format by rememberSaveable {mutableStateOf("MP3")}
    PlaybackCard(Modifier.testTag("unified-effects-card")) {
        PlaybackSectionToggle("Efeitos",effects.optBoolean("enabled")){controller.setEffects("enabled",it)}
        Row(Modifier.fillMaxWidth(),verticalAlignment=androidx.compose.ui.Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            UiText("Preset",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            Box(Modifier.weight(1f).testTag("unified-effects-preset")) {
                Select("",preset,presets.keys.toList()){name->val pair=presets.getValue(name);controller.setEffects("speed",pair.first);controller.setEffects("reverb",pair.second)}
            }
        }
        PlaybackAdjustment("Velocidade · ${effects.optInt("speed",85)}%",effects.optInt("speed",85).toFloat(),50f..150f,"unified-effects-speed"){controller.setEffects("speed",it.toInt())}
        PlaybackAdjustment("Reverb · ${effects.optInt("reverb",25)}%",effects.optInt("reverb",25).toFloat(),0f..100f,"unified-effects-reverb"){controller.setEffects("reverb",it.toInt())}
        Toggle("Manter tom",effects.optBoolean("keep_pitch")){controller.setEffects("keep_pitch",it)}
        OutlinedButton(onClick={export=true},enabled=state.model!=null,modifier=Modifier.fillMaxWidth().testTag("unified-effects-export"),shape=androidx.compose.foundation.shape.RoundedCornerShape(12.dp)) {
            OndaIcon("download",modifier=Modifier.size(18.dp));Spacer(Modifier.width(8.dp));UiText("Exportar música")
        }
        if(state.effectsPending)LinearProgressIndicator(Modifier.fillMaxWidth().testTag("unified-effects-progress"))
        if(state.effectsError.isNotBlank())Text(uiExceptionMessage(IllegalStateException(state.effectsError),"Não foi possível preparar os efeitos desta música."),color=MaterialTheme.colorScheme.error,style=MaterialTheme.typography.bodySmall)
    }
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
