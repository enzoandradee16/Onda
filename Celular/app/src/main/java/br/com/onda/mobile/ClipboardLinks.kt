package br.com.onda.mobile

import android.content.ClipboardManager
import android.content.Context
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.*
import org.json.JSONObject

@Composable fun ClipboardDownloadPrompt(enabled:Boolean,canPrompt:Boolean,onConfirm:(JSONObject)->Unit) {
    val context=LocalContext.current
    val view=LocalView.current
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    var seen by rememberSaveable {mutableStateOf(emptyList<String>())}
    var pending by remember {mutableStateOf<JSONObject?>(null)}
    val latestConfirm by rememberUpdatedState(onConfirm)
    LaunchedEffect(enabled,canPrompt,lifecycle,view) {
        if(!enabled || !canPrompt) {pending=null;return@LaunchedEffect}
        lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            val clipboard=context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            var reading=false
            fun check() {
                if(!view.hasWindowFocus() || reading || pending!=null)return
                val text=runCatching {clipboard.primaryClip?.takeIf {it.itemCount>0}?.getItemAt(0)?.text?.toString()}.getOrNull() ?: return
                if(text.length>16384 || !(text.contains("http://",ignoreCase=true) || text.contains("https://",ignoreCase=true) || text.contains("spotify:",ignoreCase=true)))return
                reading=true
                launch {
                    try {
                        val candidate=withContext(Dispatchers.IO) {MobileEngine.call(context,"clipboard","clipboard_link",JSONObject().put("text",text),EventCallback {})}
                        val key=candidate.optString("key")
                        if(isActive && view.hasWindowFocus() && key.isNotBlank() && key !in seen) {seen=seen+key;pending=candidate}
                    } finally {reading=false}
                }
            }
            val listener=ClipboardManager.OnPrimaryClipChangedListener {check()}
            clipboard.addPrimaryClipChangedListener(listener)
            try {
                while(!view.hasWindowFocus())delay(200)
                check()
                awaitCancellation()
            } finally {clipboard.removePrimaryClipChangedListener(listener)}
        }
    }
    pending?.let {candidate->
        AlertDialog(containerColor=ondaDialogContainerColor(),onDismissRequest={pending=null},title={UiText("Link copiado")},
            text={androidx.compose.foundation.layout.Column {UiText("Foi encontrado um link compatível. Deseja iniciar o download?");Text(candidate.optString("url"),maxLines=5)}},
            confirmButton={TextButton(onClick={pending=null;latestConfirm(candidate)}){UiText("Baixar agora")}},
            dismissButton={TextButton(onClick={pending=null}){UiText("Agora não")}})
    }
}
