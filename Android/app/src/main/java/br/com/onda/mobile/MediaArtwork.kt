package br.com.onda.mobile

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64

/** Invalid embedded previews must not prevent a valid catalog cover loading. */
internal fun decodeMediaArtwork(embedded:String,url:String,fetch:(String)->ByteArray?):Bitmap? {
    fun decode(bytes:ByteArray):Bitmap? {
        if(bytes.size>10*1024*1024)return null
        val bounds=BitmapFactory.Options().apply {inJustDecodeBounds=true}
        BitmapFactory.decodeByteArray(bytes,0,bytes.size,bounds)
        var sample=1
        while(maxOf(bounds.outWidth,bounds.outHeight)/sample>512)sample*=2
        return BitmapFactory.decodeByteArray(bytes,0,bytes.size,BitmapFactory.Options().apply {inSampleSize=sample})
    }
    val local=runCatching {
        val encoded=if(embedded.startsWith("data:"))embedded.substringAfter(',') else embedded
        val bytes=Base64.decode(encoded,Base64.DEFAULT)
        decode(bytes)
    }.getOrNull()
    if(local!=null)return local
    val remote=url.ifBlank {embedded}
    if(!remote.startsWith("https://") && !remote.startsWith("http://"))return null
    return runCatching {fetch(remote)?.let {decode(it)}}.getOrNull()
}
