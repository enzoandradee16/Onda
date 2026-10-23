package br.com.onda.mobile

import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class StatusNoticeTest {
    @get:Rule val compose=createComposeRule()
    @Test fun completedNoticeExpiresAndNewMessageGetsFullDuration() {
        val status=mutableStateOf("Primeiro aviso")
        compose.mainClock.autoAdvance=false
        compose.setContent {
            val visible by rememberStatusNotice(status.value,false,"Após 3 segundos")
            if(visible)Text(status.value)
        }
        compose.mainClock.advanceTimeBy(2000)
        compose.onNodeWithText("Primeiro aviso").assertExists()
        compose.runOnIdle {status.value="Novo aviso"}
        compose.mainClock.advanceTimeBy(2000)
        compose.onNodeWithText("Novo aviso").assertExists()
        compose.mainClock.advanceTimeBy(1500)
        compose.onNodeWithText("Novo aviso").assertDoesNotExist()
    }
    @Test fun busyNoticeOnlyExpiresAfterOperationEnds() {
        val busy=mutableStateOf(true)
        compose.mainClock.autoAdvance=false
        compose.setContent {
            val visible by rememberStatusNotice("Processando",busy.value,"Após 3 segundos")
            if(visible)Text("Processando")
        }
        compose.mainClock.advanceTimeBy(10000)
        compose.onNodeWithText("Processando").assertExists()
        compose.runOnIdle {busy.value=false}
        compose.mainClock.advanceTimeBy(2000)
        compose.onNodeWithText("Processando").assertExists()
        compose.mainClock.advanceTimeBy(1500)
        compose.onNodeWithText("Processando").assertDoesNotExist()
    }
    @Test fun manualModeNeverExpires() {
        compose.mainClock.autoAdvance=false
        compose.setContent {
            val visible by rememberStatusNotice("Aviso manual",false,"Fechar manualmente")
            if(visible)Text("Aviso manual")
        }
        compose.mainClock.advanceTimeBy(120000)
        compose.onNodeWithText("Aviso manual").assertExists()
    }
}
