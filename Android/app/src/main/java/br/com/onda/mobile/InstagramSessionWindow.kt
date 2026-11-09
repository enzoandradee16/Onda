package br.com.onda.mobile

import android.webkit.CookieManager
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.graphics.toArgb
import org.json.JSONObject
import java.io.File

internal fun instagramCookieEntries(headers:List<String>):Map<String,String> = buildMap {
    headers.forEach {header->header.split(';').forEach {part->
        val name=part.substringBefore('=').trim()
        val value=part.substringAfter('=',"").trim()
        if(name.matches(Regex("[A-Za-z0-9_-]+")) && value.isNotBlank() && value.none {it=='\t'||it=='\r'||it=='\n'})put(name,value)
    }}
}

internal fun hasInstagramLogin(entries:Map<String,String>) = !entries["sessionid"].isNullOrBlank() && !entries["ds_user_id"].isNullOrBlank()

internal fun instagramNavigationAllowed(scheme:String?,host:String,mainFrame:Boolean):Boolean =
    scheme=="https" && (!mainFrame || listOf("instagram.com","facebook.com","meta.com").any {host==it || host.endsWith(".$it")})

internal fun instagramCookieFile(entries:Map<String,String>):String {
    require(hasInstagramLogin(entries))
    return "# Netscape HTTP Cookie File\n"+entries.entries.joinToString("\n",postfix="\n") { (name,value)->
        require(name.matches(Regex("[A-Za-z0-9_-]+")) && value.none {it=='\t'||it=='\r'||it=='\n'})
        ".instagram.com\tTRUE\t/\tTRUE\t0\t$name\t$value"
    }
}

/** Expire cookies for this service only; never log out unrelated WebView sessions. */
internal fun clearWebSessionCookies(origins:List<String>) {
    val manager=CookieManager.getInstance()
    origins.forEach {origin->
        val host=android.net.Uri.parse(origin).host ?: return@forEach
        val domain=host.removePrefix("www.").removePrefix("m.")
        val names=manager.getCookie(origin).orEmpty().split(';').map {it.substringBefore('=').trim()}.filter {it.matches(Regex("[A-Za-z0-9_-]+"))}
        names.forEach {name->
            manager.setCookie(origin,"$name=; Max-Age=0; Path=/; Secure")
            manager.setCookie(origin,"$name=; Max-Age=0; Path=/; Domain=.$domain; Secure")
        }
    }
    manager.flush()
}

internal fun disconnectInstagram() {
    SecureVault.remove("instagram-session")
    val path=OndaStore.settings.value.optString("instagram_cookies_file")
    if(path.isNotBlank())File(path).takeIf {it.parentFile==OndaStore.context.filesDir && it.name=="instagram-session.txt"}?.delete()
    clearWebSessionCookies(listOf("https://www.instagram.com","https://instagram.com"))
    OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("instagram_cookies_file",""))
}

internal fun migrateInstagramSession() {
    val file=File(OndaStore.context.filesDir,"instagram-session.txt")
    if(!file.isFile)return
    require(file.length()<=2*1024*1024)
    val text=file.readText()
    require(text.startsWith("# Netscape HTTP Cookie File"))
    SecureVault.put("instagram-session",text)
    check(SecureVault.get("instagram-session")==text)
    if(OndaStore.settings.value.optString("instagram_cookies_file")==file.absolutePath)
        OndaStore.saveSettings(JSONObject(OndaStore.settings.value.toString()).put("instagram_cookies_file","onda-vault:instagram"))
    check(file.delete())
}

@Composable internal fun InstagramSessionWindow(close:()->Unit) {
    val context=androidx.compose.ui.platform.LocalContext.current
    val colors=MaterialTheme.colorScheme
    val launcher=androidx.activity.compose.rememberLauncherForActivityResult(androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()) {close()}
    LaunchedEffect(Unit) {
        launcher.launch(android.content.Intent(context,InstagramLoginActivity::class.java)
            .putExtra("background",colors.background.toArgb()).putExtra("foreground",colors.onBackground.toArgb()).putExtra("accent",colors.primary.toArgb()))
    }
}
