package br.com.onda.mobile

/** Display labels only; database states and transition rules remain intact. */
internal fun workflowLabel(state:String,preparation:Boolean=false):String = if(preparation) when(state) {
    "Pendente","pending" -> "Aguardando preparação"
    "Analisando","preparing" -> "Preparando"
    "Pronta","ready" -> "Pronta para reproduzir"
    "Erro","error","Erro na preparação" -> "Falha na preparação"
    else -> state
} else when(state) {
    "Na fila" -> "Pendente"
    "Em andamento" -> "Baixando"
    "Erro" -> "Falhou"
    "Aguardando escolha" -> "Aguardando confirmação"
    else -> state
}

internal fun canQueueAction(state:String,action:String):Boolean=workflowLabel(state) in when(action) {
    "pause"->setOf("Pendente","Baixando")
    "resume"->setOf("Pendente","Pausado","Cancelado")
    "retry"->setOf("Falhou","Cancelado")
    "cancel"->setOf("Pendente","Baixando","Pausado")
    else->emptySet()
}
