package br.com.onda.mobile

import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import org.json.JSONObject
import java.io.File

/** Own browser session only; never reads cookies from other installed apps. */
@Composable fun YouTubeSessionWindow(close: ()->Unit) {
    var browser by remember {mutableStateOf<WebView?>(null)}
    var message by remember {mutableStateOf("Abra o vídeo no YouTube e conclua a verificação, se aparecer. Depois toque em Usar esta sessão.")}
    DisposableEffect(Unit) {onDispose {browser?.stopLoading();browser?.destroy();browser=null}}
    Dialog(onDismissRequest=close,properties=androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth=false)) {
        Surface(Modifier.fillMaxSize().padding(8.dp),shape=MaterialTheme.shapes.large) {
            Column(Modifier.padding(12.dp)) {
                UiText("Sessão do YouTube",style=MaterialTheme.typography.titleLarge)
                UiText(message,style=MaterialTheme.typography.bodySmall,modifier=Modifier.padding(vertical=8.dp))
                AndroidView(factory={context->WebView(context).apply {
                    settings.javaScriptEnabled=true;settings.domStorageEnabled=true
                    webViewClient=object:WebViewClient() {
                        override fun shouldOverrideUrlLoading(view:WebView,request:android.webkit.WebResourceRequest):Boolean {
                            val uri=request.url;val host=uri.host.orEmpty()
                            return uri.scheme!="https" || !(host=="youtube.com" || host.endsWith(".youtube.com") || host=="accounts.google.com" || host.endsWith(".google.com"))
                        }
                    }
                    CookieManager.getInstance().setAcceptCookie(true)
                    browser=this;loadUrl("https://m.youtube.com")
                }},modifier=Modifier.weight(1f).fillMaxWidth())
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    TextButton(onClick=close){UiText("Fechar")}
                    Button(onClick={
                        val cookies=CookieManager.getInstance()
                        cookies.flush()
                        val entries=youtubeCookieEntries(listOf("https://www.youtube.com","https://m.youtube.com").map {cookies.getCookie(it).orEmpty()})
                        if(!hasYouTubeLogin(entries)) message="Esta sessão ainda não contém um login do YouTube. Entre na sua conta e aguarde o YouTube carregar antes de usar a sessão. Se o Google bloquear o navegador integrado, importe cookies.txt em Configurações."
                        else {
                            try {
                                val file=File(OndaStore.context.filesDir,"youtube-session.txt")
                                val atomic=android.util.AtomicFile(file);val stream=atomic.startWrite()
                                try {stream.write(youtubeCookieFile(entries).toByteArray(Charsets.UTF_8));atomic.finishWrite(stream)}
                                catch(error:Exception) {atomic.failWrite(stream);throw error}
                                OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("youtube_cookies_file",file.absolutePath).put("youtube_user_agent",browser?.settings?.userAgentString.orEmpty()))
                            OndaStore.log("Sessão do YouTube salva. Nenhum cookie foi incluído no log.")
                                close()
                            } catch(_:Exception) {message="Não foi possível salvar a sessão. Tente novamente."}
                        }
                    }) {UiText("Usar esta sessão")}
                }
            }
        }
    }
}
