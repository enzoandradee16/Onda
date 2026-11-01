package br.com.onda.mobile

import org.json.JSONArray
import org.json.JSONObject

/** Copy owned JSON trees without encoding and reparsing large artwork strings. */
internal fun copyJsonObject(source:JSONObject):JSONObject = JSONObject().apply {
    source.keys().forEach {key->put(key,copyJsonValue(source.get(key)))}
}
private fun copyJsonValue(value:Any?):Any? = when(value) {
    is JSONObject -> copyJsonObject(value)
    is JSONArray -> JSONArray().apply {for(index in 0 until value.length())put(copyJsonValue(value.get(index)))}
    else -> value
}
