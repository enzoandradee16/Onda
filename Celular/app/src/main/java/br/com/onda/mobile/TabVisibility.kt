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
