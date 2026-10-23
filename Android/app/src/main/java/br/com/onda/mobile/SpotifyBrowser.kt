package br.com.onda.mobile

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent

fun spotifyBrowserIntent(): Intent = CustomTabsIntent.Builder().setShowTitle(true).build().intent.apply {
    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_HISTORY)
}

fun openSpotifyAuthorization(context:Context,url:String) {
    val uri=Uri.parse(url)
    require(uri.scheme=="https" && uri.host=="accounts.spotify.com") {"Endereço de autorização Spotify inválido."}
    // Browser-owned session: no embedded WebView and no access to its credentials.
    val intent=spotifyBrowserIntent().setData(uri)
    try {context.startActivity(intent)}
    catch(_:android.content.ActivityNotFoundException) {
        context.startActivity(Intent(Intent.ACTION_VIEW,uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
