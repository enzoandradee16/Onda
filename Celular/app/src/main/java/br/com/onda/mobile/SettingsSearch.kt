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
private fun settingsFold(value:String)=Normalizer.normalize(value.lowercase(),Normalizer.Form.NFD).replace(Regex("\\p{M}+"),"")
internal fun settingsSearchMatches(query:String,text:String)=settingsFold(query).split(Regex("\\s+")).filter {it.isNotBlank()}.all {it in settingsFold(text)}
internal fun settingsSearchEntries():List<SettingsSearchEntry> {
    val data=JSONArray(OndaStore.context.assets.open("settings_search.json").bufferedReader().use {it.readText()})
    return (0 until data.length()).map {data.getJSONObject(it).let {row->SettingsSearchEntry(row.getString("category"),row.getString("label"),row.optString("keywords"))}}
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
