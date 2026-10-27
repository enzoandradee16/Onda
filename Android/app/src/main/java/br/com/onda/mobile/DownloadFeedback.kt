package br.com.onda.mobile

import org.json.JSONObject

internal fun failureAdvice(message:String):Pair<String,String> {
    val text=message.lowercase(java.util.Locale.ROOT)
    return when {
        listOf("403","401","private","login","cookies","permission","forbidden","acesso","privado").any {it in text}->"A plataforma pode exigir autenticação ou permissão." to "Verificar acesso"
        listOf("404","not found","removed","deleted","unsupported url","inválid","removido","não encontrado").any {it in text}->"O link pode ter mudado ou o conteúdo foi removido." to "Atualizar link"
        listOf("timeout","timed out","connection","network","429","502","503","conexão").any {it in text}->"A conexão ou a plataforma pode estar temporariamente indisponível." to "Tentar novamente"
        else->"Não foi possível concluir. Consulte os detalhes da falha." to "Tentar novamente"
    }
}
internal fun downloadDetail(event:JSONObject):String {
    if(event.optString("status")=="finished")return "Salvando"
    val parts=mutableListOf("Baixando")
    val size=event.optDouble("downloaded",0.0)
    val total=event.optDouble("total",0.0)
    if(total>0)parts.add("%.1f / %.1f MB".format(size/1048576,total/1048576))
    else if(size>0)parts.add("%.1f MB".format(size/1048576))
    val speed=event.optDouble("speed",0.0)
    if(speed>0)parts.add("%.2f MB/s".format(speed/1048576))
    return parts.joinToString(" · ")
}
