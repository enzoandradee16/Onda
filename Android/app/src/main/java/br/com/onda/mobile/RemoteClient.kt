package br.com.onda.mobile

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

internal class RemoteHttpException(val status: Int, message: String): Exception(message)

internal object RemoteClient {
    suspend fun request(endpoint: String, path: String, token: String = "", body: JSONObject? = null): JSONObject {
        val data = bytes(endpoint, path, token, body, 1024 * 1024)
        return runCatching { JSONObject(String(data, Charsets.UTF_8)) }.getOrElse {
            throw IllegalArgumentException("Resposta inválida. Confira o endereço do ONDA PC.")
        }
    }

    suspend fun artwork(endpoint: String, token: String, id: String): ByteArray =
        bytes(endpoint, "/v1/artwork?id=$id", token, null, 2 * 1024 * 1024)

    private suspend fun bytes(endpoint: String, path: String, token: String, body: JSONObject?, limit: Int): ByteArray = withContext(Dispatchers.IO) {
        val connection = URL(endpoint + path).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 3000
            connection.readTimeout = 3000
            connection.instanceFollowRedirects = false
            connection.useCaches = false
            if (token.isNotBlank()) connection.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val data = stream?.use { input ->
                val output = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    require(output.size() + read <= limit) { "Resposta inválida do PC." }
                    output.write(buffer, 0, read)
                }
                output.toByteArray()
            } ?: byteArrayOf()
            if (status !in 200..299) {
                val message = runCatching { JSONObject(String(data, Charsets.UTF_8)).optString("error") }.getOrNull()
                throw RemoteHttpException(status, message?.takeIf { it.isNotBlank() } ?: "Não foi possível conectar ao PC.")
            }
            data
        } finally { connection.disconnect() }
    }
}
