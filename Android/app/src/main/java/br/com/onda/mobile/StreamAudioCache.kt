package br.com.onda.mobile

import android.content.Context
import androidx.media3.database.StandaloneDatabaseProvider
import androidx.media3.datasource.cache.SimpleCache
import androidx.media3.datasource.cache.LeastRecentlyUsedCacheEvictor
import androidx.media3.datasource.cache.CacheDataSource
import androidx.media3.datasource.DataSource
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

/** App-private, disposable streaming segments; never writes into Downloads. */
@androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
internal object StreamAudioCache {
    const val LIMIT=256L*1024*1024
    // Download sequentially on the caller IO worker, leaving network capacity for playback.
    val executor=java.util.concurrent.Executor {task->task.run()}
    @Volatile private var cache:SimpleCache?=null
    @Synchronized private fun get(context:Context):SimpleCache {
        cache?.let {return it}
        val instance=SimpleCache(File(context.cacheDir,"stream-audio-v1"),LeastRecentlyUsedCacheEvictor(LIMIT/2),StandaloneDatabaseProvider(context.applicationContext))
        if(OndaStore.settings.value.optBoolean("automatic_cache_cleanup",true)) {
            val oldest=System.currentTimeMillis()-7L*24*60*60*1000
            instance.keys.toList().forEach {key->if(instance.getCachedSpans(key).all {it.lastTouchTimestamp<oldest})instance.removeResource(key)}
        }
        cache=instance
        return instance
    }
    fun factory(context:Context,upstream:DataSource.Factory)=CacheDataSource.Factory().setCache(get(context))
        .setUpstreamDataSourceFactory(upstream).setFlags(CacheDataSource.FLAG_IGNORE_CACHE_ON_ERROR)
        .setCacheKeyFactory {spec->MessageDigest.getInstance("SHA-256").digest((spec.key ?: spec.uri.toString()).toByteArray()).joinToString(""){"%02x".format(it.toInt() and 255)}}
    private val client=okhttp3.OkHttpClient.Builder().connectTimeout(15,java.util.concurrent.TimeUnit.SECONDS).readTimeout(30,java.util.concurrent.TimeUnit.SECONDS).retryOnConnectionFailure(true).build()
    fun http(stream:JSONObject):androidx.media3.datasource.okhttp.OkHttpDataSource.Factory {
        val headers=stream.optJSONObject("headers")
        val properties=buildMap<String,String>{headers?.keys()?.forEach {key->val value=headers.optString(key);if(!key.contains('\r')&&!key.contains('\n')&&!value.contains('\r')&&!value.contains('\n'))put(key,value)}}
        return androidx.media3.datasource.okhttp.OkHttpDataSource.Factory(client).setDefaultRequestProperties(properties)
    }
    private val activeFiles=java.util.concurrent.ConcurrentHashMap<String,Int>()
    fun protectedPaths():List<String> = activeFiles.keys.toList()
    fun protect(path:String){activeFiles.compute(path){_,count->(count ?: 0)+1}}
    fun release(path:String){activeFiles.computeIfPresent(path){_,count->if(count<=1)null else count-1}}
    private val prefetchSlots=Semaphore(1)
    suspend fun prefetch(context:Context,model:JSONObject)=prefetchSlots.withPermit {
        val stream=model.getJSONObject("_stream")
        val http=http(stream)
        val url=stream.getString("url")
        val hls=stream.optString("protocol").startsWith("m3u8") || url.contains("/hls_playlist/") || url.substringBefore('?').endsWith(".m3u8")
        if(hls) {
            val id="stream-cache-"+java.util.UUID.randomUUID()
            val payload=OndaStore.config().put("model",model).put("_stream_cache_protected",org.json.JSONArray(activeFiles.keys.toList())).put("_stream_cache_limit",LIMIT/2)
            val result=coroutineScope {
                val task=async(Dispatchers.IO){MobileEngine.call(context,id,"jukebox_stream_cache",payload,EventCallback {})}
                try {task.await()} finally {if(!isActive)MobileEngine.cancel(id)}
            }
            if(result.has("error"))throw java.io.IOException(result.optString("error"))
            model.put("_stream_file",result.getString("path"))
            return@withPermit
        }
        val media=androidx.media3.common.MediaItem.Builder().setUri(url).apply {if(hls)setMimeType(androidx.media3.common.MimeTypes.APPLICATION_M3U8)}.build()
        val factory=factory(context,http)
        val loader:androidx.media3.exoplayer.offline.Downloader=if(hls)androidx.media3.exoplayer.hls.offline.HlsDownloader(media,factory,executor) else androidx.media3.exoplayer.offline.ProgressiveDownloader(media,factory,executor)
        try {
            runInterruptible(Dispatchers.IO){loader.download {length,bytes,_->if(length>LIMIT || bytes>LIMIT)throw java.io.IOException("Streaming cache limit exceeded")}}
        } finally {loader.cancel()}
    }
    fun size(context:Context):Long = cache?.cacheSpace ?: if(File(context.cacheDir,"stream-audio-v1").exists())get(context).cacheSpace else 0
    fun clear(context:Context):Long {
        if(cache==null && !File(context.cacheDir,"stream-audio-v1").exists())return 0
        val instance=get(context)
        val before=instance.cacheSpace
        instance.keys.toList().forEach {instance.removeResource(it)}
        return (before-instance.cacheSpace).coerceAtLeast(0)
    }
}
