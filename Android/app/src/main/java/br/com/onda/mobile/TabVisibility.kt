package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject

internal val requiredTabs=setOf("Pesquisar","Links e fila","Fila")
internal fun hiddenTabs(settings:JSONObject):List<String> {
    val known=listOf("Imagens","Conversor de vídeos","Playlists / Álbuns","Histórico","Efeitos","Metadados")
    val saved=settings.optJSONArray("hidden_tabs") ?: JSONArray()
    return known.filter {name->(0 until saved.length()).any {saved.opt(it)==name}}
}
internal fun visibleTabs(settings:JSONObject):JSONArray {
    val hidden=hiddenTabs(settings).toSet()
    val order=settings.optJSONArray("tab_order") ?: OndaStore.defaults().getJSONArray("tab_order")
    return JSONArray((0 until order.length()).map {order.getString(it)}.filter {it !in hidden})
}

internal val bottomBarDefaults=listOf("Pesquisar","Fila","Efeitos")
internal fun normalizeBottomBarOrder(saved:List<String>):List<String> =
    saved.filter {it in bottomBarDefaults}.distinct().let {it+bottomBarDefaults.filter {name->name !in it}}
internal fun bottomBarOrder(settings:JSONObject):List<String> {
    val saved=settings.optJSONArray("bottom_bar_order") ?: JSONArray()
    return normalizeBottomBarOrder((0 until saved.length()).map {saved.optString(it)})
}
internal fun bottomBarDestinations(order:List<String>,playbackVisible:Boolean):List<String> =
    normalizeBottomBarOrder(order).filter {it!="Efeitos" || playbackVisible}+"Mais"
