package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class TechnicalErrorsTest {
    private val languages=listOf("pt-BR","es","en")
    private val rows=listOf(
        mapOf("en" to "Permission denied","pt-BR" to "Permissão negada","es" to "Permiso denegado"),
        mapOf("en" to "HTTP Error","pt-BR" to "Erro HTTP","es" to "Error HTTP"),
        mapOf("en" to "Forbidden","pt-BR" to "Acesso proibido","es" to "Acceso prohibido")
    )
    private val headings=mapOf("pt-BR" to "Falha. Detalhes técnicos originais:","es" to "Fallo. Detalles técnicos originales:","en" to "Failure. Original technical details:")
    private val catalog=TechnicalErrorCatalog(rows,headings)
    @Test fun translatesReasonsWithoutChangingCodesPathsOrUrls() {
        val raw="PermissionError: [Errno 13] Permission denied: '/data/user/0/onda/song.mp3'\nhttps://example.org/Forbidden?id=13"
        for(language in languages) {
            val translated=catalog.translate(raw,language)
            assertTrue(translated.contains(rows.first().getValue(language)))
            assertTrue(translated.contains("[Errno 13]"))
            assertTrue(translated.contains("'/data/user/0/onda/song.mp3'"))
            assertTrue(translated.endsWith("https://example.org/Forbidden?id=13"))
            assertEquals(translated,catalog.translate(translated,language))
        }
    }
    @Test fun protectedValuesAndUnknownDetailsRemainIntact() {
        for(text in listOf("'C:/Invalid argument Permission denied/Forbidden song.mp3'","\\\\Server\\Forbidden\\Music",".\\Forbidden","../Permission denied/folder","C:\\Music\\Permission denied.mp3","https://example.org/Forbidden","libmp3lame / aac / HTTP 403")) {
            for(language in languages)assertEquals(text,catalog.translate(text,language))
        }
        val raw="VendorFault: XQ_018 at decoder.cc:57"
        for(language in languages) {
            val translated=catalog.explain(raw,raw,language)
            assertEquals(headings.getValue(language)+"\n"+raw,translated)
            assertEquals(translated,catalog.explain(translated,translated,language))
            assertTrue(catalog.translate(translated,"es").startsWith(headings.getValue("es")))
        }
    }
}
