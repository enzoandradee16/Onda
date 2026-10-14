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
                        val entries=linkedMapOf<String,String>()
                        for(host in listOf("https://www.youtube.com","https://m.youtube.com")) {
                            cookies.getCookie(host).orEmpty().split(';').forEach {pair->
                                val parts=pair.trim().split('=',limit=2)
                                if(parts.size==2 && parts[0].isNotBlank() && parts.none {it.contains('\n') || it.contains('\t')}) entries[parts[0]]=parts[1]
                            }
                        }
                        if(entries.isEmpty()) message="A sessão ainda não está disponível. Aguarde o YouTube carregar ou importe cookies.txt em Configurações."
                        else {
                            val file=File(OndaStore.context.filesDir,"youtube-session.txt")
                            val expiry=System.currentTimeMillis()/1000+86400
                            file.writeText("# Netscape HTTP Cookie File\n"+entries.entries.joinToString("\n") {".youtube.com\tTRUE\t/\tTRUE\t$expiry\t${it.key}\t${it.value}"}+"\n")
                            OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("youtube_cookies_file",file.absolutePath))
                            OndaStore.log("Sessão do YouTube salva. Nenhum cookie foi incluído no log.")
                            close()
                        }
                    }) {UiText("Usar esta sessão")}
                }
            }
        }
    }
}
