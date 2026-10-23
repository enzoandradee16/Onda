package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MediaChoiceTest {
    @get:Rule(order=0) val permissions=object:org.junit.rules.ExternalResource() {
        override fun before() {
            if(android.os.Build.VERSION.SDK_INT>=33) {
                val instrumentation=InstrumentationRegistry.getInstrumentation()
                instrumentation.uiAutomation.grantRuntimePermission(instrumentation.targetContext.packageName,android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
    @get:Rule(order=1) val compose=createAndroidComposeRule<MainActivity>()

    private fun ready() {
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty()) compose.onNodeWithText("Agora não").performClick()
    }
    @Test fun videoDefaultsToSelectedAudioAndCanChangeToMkv() {
        ready()
        var reply:JSONObject?=null
        val video=JSONObject().put("id","1").put("title","Vídeo teste").put("kind","Vídeo").put("default_mode","mp3")
        compose.runOnIdle {OndaStore.ask("choice-test",JSONObject().put("type","choose_media").put("candidates",JSONArray().put(video))){reply=it}}
        try {
            compose.onNodeWithText("Só áudio · MP3").assertIsDisplayed().performClick()
            compose.onNodeWithText("Vídeo · MKV").performClick()
            compose.onNodeWithText("Confirmar").performClick()
            compose.runOnIdle {assertEquals("video",reply!!.getJSONObject("media_modes").getString("1"))}
        } finally {compose.runOnIdle {OndaStore.dismissQuestions("choice-test")}}
    }
    @Test fun singlePhotoOffersMusicVideoAndExplainsUnavailableAudio() {
        ready()
        for(hasAudio in listOf(true,false)) {
            var reply:JSONObject?=null
            val photo=JSONObject().put("id","1").put("title","Foto teste").put("kind","Foto").put("photo_choice",true).put("has_audio",hasAudio)
            compose.runOnIdle {OndaStore.ask("choice-test",JSONObject().put("type","choose_media").put("candidates",JSONArray().put(photo))){reply=it}}
            try {
                if(hasAudio) {
                    compose.onNodeWithText("Só foto").performClick()
                    compose.onNodeWithText("Foto com música · MP4").performClick()
                    compose.onNodeWithText("Confirmar").performClick()
                    compose.runOnIdle {assertEquals("photo_video",reply!!.getJSONObject("media_modes").getString("1"))}
                } else {
                    compose.onNodeWithText("A plataforma não disponibilizou a música desta foto.").assertIsDisplayed()
                    compose.onNodeWithText("Só foto").performClick()
                    compose.onNodeWithText("Foto com música · MP4").assertDoesNotExist()
                    compose.onAllNodesWithText("Só foto").onLast().performClick()
                    compose.onNodeWithText("Confirmar").performClick()
                    compose.runOnIdle {assertEquals("photos",reply!!.getJSONObject("media_modes").getString("1"))}
                }
            } finally {compose.runOnIdle {OndaStore.dismissQuestions("choice-test")}}
        }
    }

    @Test fun multipleMediaStartSelectedAndToggleAllOrIndividual() {
        ready()
        for(enabled in listOf(true,false)) {
            var reply:JSONObject?=null
            val candidates=JSONArray()
            for(i in 1..2)candidates.put(JSONObject().put("id",i.toString()).put("title","Foto $i").put("kind","Foto").put("auto_select_media",enabled))
            compose.runOnIdle {OndaStore.ask("choice-test",JSONObject().put("type","choose_media").put("candidates",candidates)){reply=it}}
            try {
                if(enabled) {
                    compose.onNodeWithText("Desmarcar todas").performClick()
                    compose.onNodeWithText("Confirmar").assertIsNotEnabled()
                }
                compose.onNodeWithText("Selecionar todas").performClick()
                compose.onNodeWithText("Desmarcar todas").assertIsDisplayed()
                compose.onNodeWithText("Foto 1").performClick()
                compose.onNodeWithText("Selecionar todas").assertIsDisplayed()
                compose.onNodeWithText("Confirmar").performClick()
                compose.runOnIdle {assertEquals(listOf("2"),reply!!.getJSONArray("selected_ids").let {array->(0 until array.length()).map {array.getString(it)}})}
            } finally {compose.runOnIdle {OndaStore.dismissQuestions("choice-test")}}
        }
    }
}
