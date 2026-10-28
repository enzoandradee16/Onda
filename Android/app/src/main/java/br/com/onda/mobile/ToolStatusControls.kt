package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

internal fun toolDateText(value:String,language:String,zone:ZoneId=ZoneId.systemDefault()):String=runCatching {
    OffsetDateTime.parse(value).atZoneSameInstant(zone).format(DateTimeFormatter.ofLocalizedDateTime(FormatStyle.SHORT).withLocale(Locale.forLanguageTag(language)))
}.getOrDefault("—")

@Composable internal fun ToolStatusList(report:JSONObject,modifier:Modifier=Modifier) {
    val language=LocalUiLanguage.current
    var expanded by rememberSaveable {mutableStateOf(false)}
    val rows=report.optJSONArray("tools")?.objects().orEmpty()
    Column(modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(4.dp)) {
        UiText("Situação das ferramentas",style=MaterialTheme.typography.titleSmall,fontWeight=FontWeight.SemiBold)
        if(report.optString("checked_at").isNotBlank()) {
            Text(translateUi("Verificado: {date}",language).replace("{date}",toolDateText(report.optString("checked_at"),language)),style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        } else UiText("Ferramentas ainda não verificadas.",style=MaterialTheme.typography.labelSmall)
        if(report.optString("updated_at").isNotBlank())Text(translateUi("Atualização: {date}",language).replace("{date}",toolDateText(report.optString("updated_at"),language)),style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        if(report.optString("update_state").isNotBlank())UiText(report.optString("update_state"),style=MaterialTheme.typography.labelSmall)
        if(report.optBoolean("restart_required"))UiText("Reinício pendente. As versões exibidas são da última verificação.",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
        for(row in rows) {
            val available=row.optBoolean("available")
            Row(Modifier.fillMaxWidth().heightIn(min=38.dp).semantics(mergeDescendants=true){stateDescription=translateUi(row.optString("status"),language)},verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                AsyncImage(model="file:///android_asset/tools/${row.optString("icon","tools")}.png",contentDescription=null,modifier=Modifier.size(26.dp))
                Text(row.optString("name"),modifier=Modifier.weight(1f),maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.bodySmall,fontWeight=FontWeight.Medium)
                UiText(if(available)row.optString("version") else row.optString("status"),modifier=Modifier.widthIn(max=112.dp),maxLines=1,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                OndaIcon(if(available)"check" else "close",modifier=Modifier.size(16.dp),tint=if(available)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
            }
        }
        if(rows.isNotEmpty())TextButton(onClick={expanded=!expanded},contentPadding=PaddingValues(horizontal=0.dp,vertical=0.dp),modifier=Modifier.heightIn(min=40.dp).testTag("tool-technical-details")) {
            UiText(if(expanded)"Ocultar detalhes técnicos" else "Detalhes técnicos",style=MaterialTheme.typography.labelMedium)
        }
        if(expanded)UiText(report.optString("details"),style=MaterialTheme.typography.labelSmall,modifier=Modifier.testTag("tool-raw-details"))
    }
}

@Composable internal fun ToolStatusControls(vm:OndaViewModel) {
    val busy by vm.busy.collectAsStateWithLifecycle()
    val tools by MobileEngine.toolsState.collectAsStateWithLifecycle()
    val downloading by OndaStore.running.collectAsStateWithLifecycle()
    val preparing by vm.effectsPreparing.collectAsStateWithLifecycle()
    val loadingCollection by vm.loadingPlaybackCollection.collectAsStateWithLifecycle()
    val jukebox by vm.jukebox.state.collectAsStateWithLifecycle()
    var report by remember {mutableStateOf(JSONObject())}
    LaunchedEffect(busy) {
        if(busy)return@LaunchedEffect
        val result=withContext(Dispatchers.IO){MobileEngine.call(OndaStore.context,"tools-status-view","tools_status",JSONObject(),EventCallback {})}
        if(!result.has("error"))report=result.optJSONObject("display") ?: JSONObject()
    }
    ToolStatusList(report)
    if(report.optBoolean("can_restart"))OutlinedButton(enabled=!busy&&!tools.running&&!downloading&&!preparing&&!loadingCollection&&!jukebox.busy,onClick=vm::restartAfterToolCheck,modifier=Modifier.fillMaxWidth().testTag("restart-after-tools-check")){UiText("Reiniciar ONDA")}

    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        OutlinedButton(modifier=Modifier.weight(1f),enabled=!busy&&!tools.running,onClick={vm.operation("tools_check",JSONObject()){report=it.optJSONObject("display") ?: JSONObject()}}){UiText("Verificar")}
        Button(modifier=Modifier.weight(1f),enabled=!busy&&!tools.running,onClick={vm.operation("update",JSONObject()){report=it.optJSONObject("display") ?: JSONObject()}}){UiText("Atualizar")}
    }
}
