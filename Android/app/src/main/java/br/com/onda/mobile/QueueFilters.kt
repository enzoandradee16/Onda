package br.com.onda.mobile
import java.text.Normalizer
import org.json.JSONObject
internal val queueFilters=listOf("Todos","Pendentes","Em andamento","Concluídos","Com falha","Cancelados")
private val queueMarks=Regex("\\p{M}+")
private val queueSpaces=Regex("\\s+")
private fun queueFold(value:String)=Normalizer.normalize(value.lowercase(),Normalizer.Form.NFD).replace(queueMarks,"")
internal class QueueMatcher(query:String,filter:String) {
    internal val terms=queueFold(query).split(queueSpaces).filter {it.isNotBlank()}
    private val allowed=when(filter) {
        "Pendentes"->setOf("Pendente","Na fila")
        "Em andamento"->setOf("Baixando","Em andamento","Aguardando escolha")
        "Concluídos"->setOf("Concluído")
        "Com falha"->setOf("Erro","Falhou")
        "Cancelados"->setOf("Cancelado","Parado")
        else->emptySet()
    }
    fun matches(title:String,state:String,config:JSONObject):Boolean {
        if(allowed.isNotEmpty() && state !in allowed)return false
        if(terms.isEmpty())return true
        val info=config.optJSONObject("catalog_record") ?: config.optJSONObject("queue_info")
        val text=queueFold(listOf(title,config.optString("url"),config.optString("mode"),info?.optString("artists").orEmpty(),info?.optString("album").orEmpty(),info?.optString("platform").orEmpty()).joinToString(" "))
        return terms.all {it in text}
    }
}
internal fun queueMatches(title:String,state:String,config:JSONObject,query:String,filter:String):Boolean = QueueMatcher(query,filter).matches(title,state,config)
