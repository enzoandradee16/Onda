package br.com.onda.mobile

import androidx.compose.runtime.*
import kotlinx.coroutines.delay

val noticeDurations=linkedMapOf("Fechar manualmente" to 0,"Após 3 segundos" to 3,"Após 5 segundos" to 5,
    "Após 10 segundos" to 10,"Após 15 segundos" to 15,"Após 30 segundos" to 30,"Após 60 segundos" to 60)

@Composable fun rememberStatusNotice(status:String,busy:Boolean,duration:String):MutableState<Boolean> {
    val visible=remember(status) {mutableStateOf(status.isNotBlank())}
    LaunchedEffect(status,busy,duration) {
        visible.value=status.isNotBlank()
        val seconds=noticeDurations[duration] ?: 0
        if(status.isNotBlank() && !busy && seconds>0) {
            delay(seconds*1000L)
            visible.value=false
        }
    }
    return visible
}
