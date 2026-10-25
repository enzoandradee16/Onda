package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TechnicalErrorLocalizationTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun everySharedReasonTranslatesInAllThreeLanguages() {
        val data=JSONObject(context.assets.open("technical_errors.json").bufferedReader().use {it.readText()})
        val rows=data.getJSONArray("phrases")
        for(index in 0 until rows.length()) {
            val row=rows.getJSONObject(index)
            for(language in UI_LANGUAGES) {
                val translated=translateError(row.getString("en"),language,context)
                assertEquals(row.getString("en")+" / "+language,row.getString(language),translated)
                assertEquals(translated,translateError(translated,language,context))
            }
        }
    }
    @Test fun nestedTechnicalErrorsPreserveFilesUrlsAndCodes() {
        val raw="PermissionError: [Errno 13] Permission denied: '/data/user/0/br.com.onda.mobile/files/jukebox/audio.mp3'"
        for((language,phrase) in listOf("pt-BR" to "Permissão negada","es" to "Permiso denegado","en" to "Permission denied")) {
            val translated=translateError(raw,language,context)
            assertTrue(translated.contains(phrase));assertTrue(translated.contains("PermissionError: [Errno 13]"))
            assertTrue(translated.endsWith("'/data/user/0/br.com.onda.mobile/files/jukebox/audio.mp3'"))
        }
        val text="ERROR: [youtube] ABC: Unable to download webpage: HTTP Error 429: Too Many Requests\nhttps://example.org/Forbidden?id=13"
        val es=translateError(text,"es",context)
        assertTrue(es.contains("No se pudo descargar la página"));assertTrue(es.contains("Error HTTP 429: Demasiadas solicitudes"))
        assertTrue(es.endsWith("https://example.org/Forbidden?id=13"))
    }
    @Test fun unknownErrorsAndWrappedCatalogMessagesHaveLocalizedExplanations() {
        val data=JSONObject(context.assets.open("technical_errors.json").bufferedReader().use {it.readText()})
        val raw="VendorUnexpectedStateException: XQ_018 at decoder.cc:57"
        for(language in UI_LANGUAGES) {
            val text=translateError(raw,language,context)
            assertEquals(data.getJSONObject("unknown").getString(language)+"\n"+raw,text)
            assertEquals(text,translateError(text,language,context))
        }
        assertEquals(translateError(raw,"en",context),translateError(translateError(raw,"es",context),"en",context))
        assertEquals("Choose an audio file.\nHTTP Error 403: Forbidden",translateError("Escolha um arquivo de áudio.\nHTTP Error 403: Forbidden","en",context))
        assertEquals("ERROR: [tool] ABC: Choose an audio file.",translateError("ERROR: [tool] ABC: Escolha um arquivo de áudio.","en",context))
    }
    @Test fun protectedPathsAndMusicNamesRemainUnchanged() {
        val values=listOf("'C:/Invalid argument Permission denied/Forbidden song.mp3'","\\\\Server\\Forbidden\\Music",".\\Forbidden","../Permission denied/folder")
        for(language in UI_LANGUAGES) {
            for(value in values)assertEquals(value,translateError(value,language,context))
            for(title in listOf("Forbidden","Not Found","Permission denied"))assertEquals(title,translateUi(title,language,context))
        }
    }
}
