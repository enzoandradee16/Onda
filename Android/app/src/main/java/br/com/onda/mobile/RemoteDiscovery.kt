package br.com.onda.mobile

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.NetworkInterface
import java.net.SocketTimeoutException
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import org.json.JSONObject

internal data class PlaybackDevice(val address: String, val name: String)

/** Only run while the devices sheet is visible. Discovery never authenticates a PC. */
internal suspend fun discoverPlaybackDevices(): List<PlaybackDevice> = withContext(Dispatchers.IO) {
    val found = linkedMapOf<String, PlaybackDevice>()
    val nonce = UUID.randomUUID().toString().replace("-", "")
    val bytes = JSONObject().put("type", "onda-discover").put("nonce", nonce).toString().toByteArray()
    DatagramSocket().use { socket ->
        socket.broadcast = true
        socket.soTimeout = 350
        val targets = mutableSetOf(InetAddress.getByName("255.255.255.255"))
        runCatching {
            NetworkInterface.getNetworkInterfaces().toList().filter { it.isUp && !it.isLoopback }.forEach { network ->
                network.interfaceAddresses.mapNotNullTo(targets) { it.broadcast }
            }
        }
        targets.forEach { target -> runCatching { socket.send(DatagramPacket(bytes, bytes.size, target, 45847)) } }
        val deadline = System.nanoTime() + 2_000_000_000L
        while (System.nanoTime() < deadline) {
            currentCoroutineContext().ensureActive()
            val packet = DatagramPacket(ByteArray(1025), 1025)
            try { socket.receive(packet) } catch (_: SocketTimeoutException) { continue }
            if (packet.length > 1024) continue
            runCatching {
                val reply = JSONObject(String(packet.data, 0, packet.length, Charsets.UTF_8))
                if (reply.optString("type") != "onda-device" || reply.optString("nonce") != nonce || reply.optInt("protocol") != 1) return@runCatching
                val address = remoteEndpoint("${packet.address.hostAddress}:${reply.optInt("port")}")
                found[address] = PlaybackDevice(address, reply.optString("name", "ONDA PC").take(80).ifBlank { "ONDA PC" })
            }
        }
    }
    found.values.toList()
}
