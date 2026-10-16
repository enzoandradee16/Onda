package br.com.onda.mobile

import androidx.compose.runtime.*
import androidx.compose.animation.*
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.clickable
import androidx.compose.material3.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.*
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

/** Kept in composition during exit so both automatic and manual dismissal slide up. */
@Composable internal fun TopStatusNotice(status:String,visible:Boolean,busy:Boolean,animated:Boolean,onCancel:()->Unit,onDismiss:()->Unit,onOpenSettings:((String)->Unit)?=null) {
    val destination=if(busy || onOpenSettings==null)null else noticeDestination(status)
    val actionLabel=destination?.let {if(it=="Sessão do YouTube")translateUi("Abrir sessão do YouTube") else translateUi("Abrir configurações de {category}").replace("{category}",translateUi(it))}
    val transition=remember {MutableTransitionState(false)}
    transition.targetState=visible
    var lastMessage by remember {mutableStateOf(status)}
    LaunchedEffect(status) {if(status.isNotBlank())lastMessage=status}
    AnimatedVisibility(visibleState=transition,
        enter=if(animated)slideInVertically(tween(220)) {-it}+expandVertically(tween(220),expandFrom=Alignment.Top) else EnterTransition.None,
        exit=if(animated)slideOutVertically(tween(180)) {-it}+shrinkVertically(tween(180),shrinkTowards=Alignment.Top) else ExitTransition.None) {
        Row(Modifier.fillMaxWidth().padding(horizontal=LayoutSpacing.inset).testTag("top-status-notice"),verticalAlignment=Alignment.CenterVertically) {
            UiText(status.ifBlank {lastMessage},Modifier.weight(1f).testTag("app-status").then(
                if(destination!=null)Modifier.clickable(role=Role.Button,onClickLabel=actionLabel) {onOpenSettings?.invoke(destination)} else Modifier
            ).semantics {if(!busy)liveRegion=LiveRegionMode.Polite},color=if(destination!=null)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,style=MaterialTheme.typography.bodySmall,maxLines=2)
            if(busy)TextButton(onClick=onCancel) {UiText("Cancelar")}
            else TextButton(onClick=onDismiss) {AccessibleSymbol("×","Fechar aviso")}
        }
    }
}
