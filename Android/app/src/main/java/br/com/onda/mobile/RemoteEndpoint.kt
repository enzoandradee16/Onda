package br.com.onda.mobile

import java.net.URI

/** The first prototype only connects to explicit IPv4 addresses on the LAN. */
internal fun remoteEndpoint(input: String): String {
    val text = input.trim().let { if (it.contains("://")) it else "http://$it" }
    val uri = runCatching { URI(text) }.getOrElse { throw IllegalArgumentException("Endereço inválido.") }
    val parts = uri.host.orEmpty().split('.')
    val octets = parts.map { it.toIntOrNull() }
    require(parts.size == 4 && parts.all { it.matches(Regex("[0-9]{1,3}")) } && octets.all { it != null && it in 0..255 }) {
        "Use o endereço numérico exibido no ONDA PC."
    }
    val a = octets[0]!!; val b = octets[1]!!
    val local = a == 10 || (a == 172 && b in 16..31) || (a == 192 && b == 168)
    require(local && uri.scheme == "http" && uri.port in 1..65535 && uri.userInfo == null && uri.query == null && uri.fragment == null && uri.rawPath.orEmpty() in listOf("", "/")) {
        "Use o endereço completo da rede local exibido no PC, incluindo a porta."
    }
    return "http://${octets.joinToString(".")}:${uri.port}"
}
