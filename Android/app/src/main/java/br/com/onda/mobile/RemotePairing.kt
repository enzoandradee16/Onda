package br.com.onda.mobile

import java.net.URI
import java.net.URLDecoder

internal data class RemotePairing(val address:String,val code:String)
internal fun parseRemotePairing(value:String):RemotePairing {
    require(value.length<=2048) {"QR Code inválido."}
    val uri=URI(value)
    require(uri.scheme=="onda" && uri.host=="pair" && uri.userInfo==null && uri.port==-1 && uri.fragment==null && uri.path.orEmpty().isEmpty()) {"Use o QR Code exibido no ONDA PC."}
    val pairs=uri.rawQuery.orEmpty().split('&').map {part->
        val bits=part.split('=',limit=2)
        require(bits.size==2) {"QR Code inválido."}
        URLDecoder.decode(bits[0],"UTF-8") to URLDecoder.decode(bits[1],"UTF-8")
    }
    require(pairs.size==2 && pairs.map {it.first}.toSet()==setOf("address","code")) {"QR Code inválido."}
    val fields=pairs.toMap()
    val code=fields.getValue("code")
    require(code.matches(Regex("[0-9]{6}"))) {"Código de conexão inválido."}
    return RemotePairing(remoteEndpoint(fields.getValue("address")),code)
}
