package br.com.onda.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class RemoteEndpointTest {
    @Test fun acceptsLocalAddressesWithAnExplicitPort() {
        assertEquals("http://192.168.1.4:4321", remoteEndpoint("192.168.1.4:4321"))
        assertEquals("http://10.0.0.2:12345", remoteEndpoint(" http://10.0.0.2:12345/ "))
        assertEquals("http://172.31.0.2:1234", remoteEndpoint("http://172.31.0.2:1234"))
    }

    @Test fun rejectsPublicAddressesCredentialsPathsAndUnexpectedSchemes() {
        for (value in listOf("http://8.8.8.8:1234", "http://127.0.0.1:1234", "https://192.168.1.2:1234", "http://192.168.1.2", "http://192.168.1.2:99999", "http://user@192.168.1.2:1234", "http://192.168.1.2:1234/path", "http://192.168.1.2:1234?x=1", "http://192.168.1.2:1234#fragment", "http://172.32.0.2:1234", "http://192.168.1.999:1234", "http://localhost:1234")) {
            assertThrows(IllegalArgumentException::class.java) { remoteEndpoint(value) }
        }
    }
}
