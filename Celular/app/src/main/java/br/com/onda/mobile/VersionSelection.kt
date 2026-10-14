package br.com.onda.mobile

import org.json.JSONObject

// Version selection is a live preference; collection format/quality stay per item.
fun applyVersionSelection(config: JSONObject, settings: JSONObject): JSONObject = config.apply {
    val manual = config.optBoolean("_manual_version", false)
    val automatic = !manual && settings.optBoolean("auto_match", false)
    put("auto_match", automatic)
    put("confirm_version", manual || (!automatic && settings.optBoolean("confirm_version", false)))
}
