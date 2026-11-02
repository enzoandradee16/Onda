package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CompleteLocalizationTest {
    @Test fun allSharedEntriesAndPlaceholdersMatchOnAndroid() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val en=JSONObject(context.assets.open("en.json").bufferedReader().use {it.readText()})
        val es=JSONObject(context.assets.open("es.json").bufferedReader().use {it.readText()})
        assertEquals(en.keys().asSequence().toSet(),es.keys().asSequence().toSet())
        val placeholders=Regex("\\{[a-zA-Z_][a-zA-Z_0-9]*\\}")
        for((language,catalog) in listOf("en" to en,"es" to es)) for(key in catalog.keys()) {
            val value=catalog.getString(key)
            assertTrue(key,value.isNotBlank())
            assertEquals(key,placeholders.findAll(key).map {it.value}.toSet(),placeholders.findAll(value).map {it.value}.toSet())
            assertEquals(key,value,translateUi(key,language,context))
        }
    }
    @Test fun countTemplatesPreserveNamesAndRemoteErrorsTranslateCompletely() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        for(language in listOf("en","es")) {
            assertEquals("A Night de Tokyo",translateUi("A Night de Tokyo",language,context))
            assertEquals("Canção de verão sem tradução cadastrada",translateUi("Canção de verão sem tradução cadastrada",language,context))
        }
        assertEquals("00:12 of 04:30",translateUi("00:12 de 04:30","en",context))
        assertEquals("The connection changed. Try again.",translateUi("A conexão mudou. Tente novamente.","en",context))
        assertEquals("La conexión ha cambiado. Inténtalo de nuevo.",translateUi("A conexão mudou. Tente novamente.","es",context))
        assertEquals("This phone's queue is full.",translateUi("A fila deste telefone está cheia.","en",context))
    }

    @Test fun backendNotesAndCountsTranslateWithoutChangingNames() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("Discovery · 14 items. Spotify album via API; original order and edition.",translateUi("Discovery · 14 itens. Álbum Spotify via API; ordem e edição originais.","en",context))
        assertEquals("Discovery · 14 elementos. Álbum de Spotify mediante la API; orden y edición originales.",translateUi("Discovery · 14 itens. Álbum Spotify via API; ordem e edição originais.","es",context))
        assertEquals("12 items added to the queue",translateUi("12 itens adicionados à fila","en",context))
        assertEquals("12 elementos añadidos a la cola",translateUi("12 itens adicionados à fila","es",context))
        for(language in listOf("en","es")) {
            assertEquals("ONDA",translateUi("ONDA",language,context))
            assertEquals("Minha música · Meu artista",translateUi("Minha música · Meu artista",language,context))
        }
    }
}
