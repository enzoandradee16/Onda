package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject

internal fun hasBatchActions(value: JSONObject) = value.optBoolean(
    "number_tracks"
) || value.optString("find").isNotEmpty() || value.optString("case", "none") != "none"

@Composable internal fun BatchActionsControls(value: JSONObject, enabled: Boolean, onChange: (JSONObject) -> Unit) {
    fun update(key: String, item: Any) = onChange(JSONObject(value.toString()).put(key, item))
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        UiText("Ações em lote", style = MaterialTheme.typography.titleSmall)
        val fields = listOf("Título", "Artista", "Álbum")
        val fieldKeys = listOf("title", "artists", "album")
        Select(
            "Aplicar ao campo",
            fields[fieldKeys.indexOf(value.optJSONArray("fields")?.optString(0) ?: "title").coerceAtLeast(0)],
            fields,
            enabled = enabled
        ) {
            update("fields", JSONArray(listOf(fieldKeys[fields.indexOf(it)])))
        }
        val cases = listOf("Manter texto", "Iniciais maiúsculas", "MAIÚSCULAS", "minúsculas")
        val caseKeys = listOf("none", "title", "upper", "lower")
        Select(
            "Maiúsculas e minúsculas",
            cases[caseKeys.indexOf(value.optString("case", "none")).coerceAtLeast(0)],
            cases,
            enabled = enabled
        ) {
            update("case", caseKeys[cases.indexOf(it)])
        }
        OutlinedTextField(value.optString("find"), {
            update("find", it)
        }, label = { UiText("Localizar texto") }, enabled = enabled, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value.optString("replace"), {
            update("replace", it)
        }, label = { UiText("Substituir por") }, enabled = enabled, modifier = Modifier.fillMaxWidth())
        ToolSwitch("Numerar faixas", value.optBoolean("number_tracks"), enabled = enabled) {
            update("number_tracks", it)
        }
        if (value.optBoolean("number_tracks")) OutlinedTextField(value.optInt("start", 1).toString(), {
            update(
                "start",
                it.toIntOrNull() ?: 0
            )
        }, label = { UiText("Número inicial") }, enabled = enabled, modifier = Modifier.fillMaxWidth())
        if (value.optBoolean(
                "number_tracks"
            )
        ) UiText(
            "A numeração segue a ordem dos arquivos selecionados. Confira cada faixa na prévia.",
            style = MaterialTheme.typography.bodySmall
        )
    }
}
