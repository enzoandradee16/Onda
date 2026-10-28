package br.com.onda.mobile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import java.text.Normalizer
import org.json.JSONArray

internal data class SettingsSearchEntry(val category:String,val label:String,val keywords:String="")
internal val LocalSettingsSearchTarget=staticCompositionLocalOf {""}
private fun settingsFold(value:String)=Normalizer.normalize(value.lowercase(java.util.Locale.ROOT),Normalizer.Form.NFD).replace(Regex("\\p{M}+"),"")
internal fun settingsSearchMatches(query:String,text:String)=settingsFold(query).split(Regex("\\s+")).filter {it.isNotBlank()}.all {it in settingsFold(text)}
private val settingsSearchTerms by lazy {
    org.json.JSONObject(OndaStore.context.assets.open("search_terms.json").bufferedReader().use {it.readText()})
}
internal fun settingsSearchText(entry:SettingsSearchEntry,language:String):String {
    val values=listOf(entry.category,entry.label,entry.keywords)
    val aliases=settingsSearchTerms.optJSONObject(entry.label)
    return (values+values.map {translateUi(it,language)}+UI_LANGUAGES.map {aliases?.optString(it).orEmpty()}).joinToString(" ")
}
internal fun settingsSearchEntries():List<SettingsSearchEntry> {
    val data=JSONArray(OndaStore.context.assets.open("settings_search.json").bufferedReader().use {it.readText()})
    val legacy=(0 until data.length()).map {data.getJSONObject(it).let {row->SettingsSearchEntry(row.getString("category"),row.getString("label"),row.optString("keywords"))}}
    return (listOf(SettingsSearchEntry("Áudio","Duração da transição entre músicas (segundos)","crossfade sobreposição jukebox timer"))+legacy.filter {it.label !in setOf("Ordem das abas de reprodução","Ordem das abas","Mostrar ou ocultar abas","Restaurar ordem das abas","Mostrar itens na fila","Mostrar ações antes das listas")}+listOf(
        SettingsSearchEntry("Aparência","Tamanho dos cards da pesquisa","capas resultados músicas"),
        SettingsSearchEntry("Aparência","Ordem da barra inferior","reordenar pesquisar downloads reprodução navegação"),
        SettingsSearchEntry("Aparência","Navegação","abas barra inferior links downloads"),
        SettingsSearchEntry("Aparência","Mostrar Reprodução na barra inferior","jukebox efeitos ocultar"),
        SettingsSearchEntry("Aparência","Ferramentas no menu Mais","ordem mostrar ocultar imagens conversor metadados"),
        SettingsSearchEntry("Aparência","Biblioteca no menu Mais","ordem mostrar ocultar álbuns playlists histórico"),
        SettingsSearchEntry("Downloads","Ação ao terminar a fila","som concluir finalização"),
        SettingsSearchEntry("Downloads","Controles na notificação","botões pausar retomar parar fila"),
        SettingsSearchEntry("Desempenho","Limpar temporários automaticamente","cache espaço armazenamento prévias limpeza")
    )).distinctBy {it.category to it.label}
}
@OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)
@Composable internal fun settingsSearchModifier(text:String,modifier:Modifier):Modifier {
    val target=LocalSettingsSearchTarget.current
    if(target.isBlank() || target!=text)return modifier
    val requester=remember {BringIntoViewRequester()}
    LaunchedEffect(target) {delay(240);requester.bringIntoView()}
    return modifier.bringIntoViewRequester(requester).background(MaterialTheme.colorScheme.primary.copy(alpha=.18f)).padding(3.dp)
}

internal fun settingsCategoryOrder():List<String> {
    val layout=org.json.JSONObject(OndaStore.context.assets.open("layout.json").bufferedReader().use {it.readText()}).getJSONArray("categories")
    return (0 until layout.length()).map {layout.getString(it)}
}
