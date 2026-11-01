package br.com.onda.mobile

import org.json.JSONObject

internal const val EMPTY_MUSIC_SEARCH = "Informe uma música, álbum, playlist ou link."

internal fun operationResultMessage(result:JSONObject):String {
    (result.opt("message") as? String)?.takeIf {it.isNotBlank()}?.let {return it}
    if(result.has("bytes")) {
        val remaining="Cache em disco: {size} MB.".replace("{size}","%.2f".format(result.optLong("bytes")/1048576.0))
        val lines=mutableListOf<String>()
        if(result.has("removed"))lines+="Cache limpo. Espaço liberado: {size} MB.".replace("{size}","%.2f".format(result.optLong("removed")/1048576.0))
        lines+=remaining
        if(result.optInt("failed")>0)lines+="Alguns arquivos não puderam ser removidos. Tente novamente depois de fechar as operações em andamento."
        return lines.joinToString("\n")
    }
    return "Concluído"
}
