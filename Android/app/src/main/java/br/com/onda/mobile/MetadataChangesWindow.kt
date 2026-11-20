package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import coil.compose.AsyncImage
import org.json.JSONArray
import org.json.JSONObject

@Composable internal fun MetadataChangesWindow(question: Question) {
    val rows = remember(question) { question.event.getJSONArray("entries").objects() }
    var selection by remember(question) {
        mutableStateOf(
            rows.mapIndexed { index, row ->
                index to
                    row.getJSONArray("fields").objects().map { it.getString("key") }.toSet()
            }.toMap()
        )
    }
    val cancel = { OndaStore.answer(JSONObject().put("cancel", true)) }
    Dialog(onDismissRequest = cancel) {
        Surface(shape = MaterialTheme.shapes.large, color = ondaDialogContainerColor()) {
            Column(
                Modifier.fillMaxWidth().heightIn(max = 660.dp).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                UiText("Prévia das alterações", style = MaterialTheme.typography.titleLarge)
                UiText(
                    "Confira as alterações. Desmarque o que deseja preservar.",
                    style = MaterialTheme.typography.bodySmall
                )
                UiText(
                    if (question.event.optBoolean(
                            "overwrite_original"
                        )
                    ) "Os arquivos originais selecionados serão substituídos." else "Os arquivos originais serão preservados; cópias editadas serão salvas.",
                    style = MaterialTheme.typography.bodySmall
                )
                LazyColumn(Modifier.weight(1f, false), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    itemsIndexed(rows) { index, row ->
                        OutlinedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(row.getString("name"), style = MaterialTheme.typography.titleSmall)
                                row.getJSONArray("fields").objects().forEach { field ->
                                    Row(verticalAlignment = Alignment.Top) {
                                        val key = field.getString("key")
                                        Checkbox(key in selection[index].orEmpty(), { checked ->
                                            selection =
                                                selection +
                                                (
                                                    index to selection[index].orEmpty().let {
                                                        if (checked) it + key else it - key
                                                    }
                                                    )
                                        }, modifier = Modifier.a11yLabel(field.getString("label")))
                                        Column(
                                            Modifier.weight(1f).padding(top = 8.dp),
                                            verticalArrangement = Arrangement.spacedBy(3.dp)
                                        ) {
                                            UiText(
                                                field.getString("label"),
                                                style = MaterialTheme.typography.labelLarge
                                            )
                                            Text(
                                                translateUi("Atual", LocalUiLanguage.current) + ": " +
                                                    field.optString("before").ifBlank {
                                                        translateUi("Vazio", LocalUiLanguage.current)
                                                    },
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                            Text(
                                                translateUi("Novo", LocalUiLanguage.current) + ": " +
                                                    field.optString("after").ifBlank {
                                                        translateUi("Vazio", LocalUiLanguage.current)
                                                    },
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.primary
                                            )
                                        }
                                    }
                                }
                                if (row.optString(
                                        "after_cover"
                                    ).isNotBlank()
                                ) Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    for (key in listOf("before_cover", "after_cover")) {
                                        val raw = row.optString(key)
                                        val model =
                                            remember(raw) {
                                                if (raw.startsWith(
                                                        "data:image/"
                                                    )
                                                ) android.util.Base64.decode(
                                                    raw.substringAfter(','),
                                                    android.util.Base64.DEFAULT
                                                ) else raw
                                            }
                                        Column {
                                            UiText(
                                                if (key ==
                                                    "before_cover"
                                                ) "Atual" else "Novo",
                                                style = MaterialTheme.typography.labelSmall
                                            )
                                            AsyncImage(
                                                model,
                                                null,
                                                Modifier.size(64.dp),
                                                contentScale = androidx.compose.ui.layout.ContentScale.Fit
                                            )
                                        }
                                    }
                                }
                                if (row.getJSONArray("fields").length() ==
                                    0
                                ) UiText("Sem alterações de metadados.", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TextButton(onClick = cancel) { UiText("Cancelar") }
                    Button(onClick = {
                        val value = JSONObject()
                        selection.forEach { (index, fields) ->
                            value.put(index.toString(), JSONArray(fields.toList()))
                        }
                        OndaStore.answer(JSONObject().put("selected", value))
                    }) { UiText("Salvar alterações") }
                }
            }
        }
    }
}
