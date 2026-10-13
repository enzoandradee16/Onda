package br.com.onda.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MediaChoiceTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()

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
}
