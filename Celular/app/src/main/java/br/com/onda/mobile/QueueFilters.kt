package br.com.onda.mobile
import java.text.Normalizer
import org.json.JSONObject
internal val queueFilters=listOf("Todos","Pendentes","Em andamento","Concluídos","Com falha","Cancelados")
private val queueMarks=Regex("\\p{M}+")
private val queueSpaces=Regex("\\s+")
private fun queueFold(value:String)=Normalizer.normalize(value.lowercase(),Normalizer.Form.NFD).replace(queueMarks,"")
internal fun queueMatches(title:String,state:String,config:JSONObject,query:String,filter:String):Boolean {
    val allowed=when(filter) {
        "Pendentes"->setOf("Pendente","Na fila")
        "Em andamento"->setOf("Baixando","Em andamento","Aguardando escolha")
        "Concluídos"->setOf("Concluído")
        "Com falha"->setOf("Erro","Falhou")
        "Cancelados"->setOf("Cancelado","Parado")
        else->emptySet()
    }
    if(allowed.isNotEmpty() && state !in allowed)return false
    if(query.isBlank())return true
    val info=config.optJSONObject("catalog_record") ?: config.optJSONObject("queue_info") ?: JSONObject()
    val text=queueFold(listOf(title,config.optString("url"),config.optString("mode"),info.optString("artists"),info.optString("album"),info.optString("platform")).joinToString(" "))
    return queueFold(query).split(queueSpaces).filter {it.isNotBlank()}.all {it in text}
}
