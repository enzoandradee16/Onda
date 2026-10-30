package br.com.onda.mobile

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.json.JSONObject

/** Quick appearance controls share the same settings as the full settings page. */
@Composable internal fun AppearanceWindow(close:()->Unit) {
    val settings by OndaStore.settings.collectAsStateWithLifecycle()
    fun put(key:String,value:Any) {OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put(key,value))}
    Dialog(onDismissRequest=close) {
        Surface(Modifier.widthIn(max=420.dp).fillMaxWidth().testTag("appearance-dialog"),shape=RoundedCornerShape(24.dp),color=ondaDialogContainerColor()) {
            Column(Modifier.heightIn(max=640.dp).verticalScroll(rememberScrollState()).padding(LayoutSpacing.inset),verticalArrangement=Arrangement.spacedBy(LayoutSpacing.section)) {
                UiText("Aparência",style=MaterialTheme.typography.headlineSmall)
                Select("Modo de aparência",settings.optString("theme","Preto puro"),appearanceModes,Modifier.testTag("appearance-theme")){put("theme",it)}
                AccentPreference(settings.optString("accent","Verde-Água"),Modifier.testTag("appearance-accent")){put("accent",it)}
                if(settings.optString("theme")=="Preto puro")Toggle("Mostrar bordas e separações no Preto puro",settings.optBoolean("pure_black_separators",false)){put("pure_black_separators",it)}
                FilledTonalButton(onClick=close,modifier=Modifier.align(Alignment.End).testTag("appearance-done")){UiText("Pronto")}
            }
        }
    }
}
