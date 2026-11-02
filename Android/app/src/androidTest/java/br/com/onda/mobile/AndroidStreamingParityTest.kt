package br.com.onda.mobile

import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.net.ServerSocket
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.Executors

class AndroidStreamingParityTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private class AudioServer:AutoCloseable {
        private val server=ServerSocket(0)
        val url="http://127.0.0.1:${server.localPort}/tone.wav"
        private val clients=Executors.newFixedThreadPool(2)
        private val bytes=ByteBuffer.allocate(44+44100*4*20).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RIFF".toByteArray());putInt(capacity()-8);put("WAVEfmt ".toByteArray());putInt(16);putShort(1);putShort(2);putInt(44100);putInt(44100*4);putShort(4);putShort(16);put("data".toByteArray());putInt(capacity()-44)
            repeat(44100*20){i->val sample=(kotlin.math.sin(i*2*Math.PI*440/44100)*1000).toInt().toShort();putShort(sample);putShort(sample)}
        }.array()
        private val accepting=Thread {
            while(!server.isClosed)try {
                val socket=server.accept()
                clients.execute {socket.use {
                    try {
                        val reader=socket.getInputStream().bufferedReader()
                        val request=reader.readLine().orEmpty()
                        var offset=0
                        while(true){val line=reader.readLine();if(line.isNullOrEmpty())break;if(line.startsWith("Range:",true))offset=line.substringAfter("bytes=","0").substringBefore('-').toIntOrNull() ?: 0}
                        offset=offset.coerceIn(0,bytes.lastIndex)
                        val output=socket.getOutputStream()
                        output.write(("HTTP/1.1 ${if(offset>0)"206 Partial Content" else "200 OK"}\r\nContent-Type: audio/wav\r\nAccept-Ranges: bytes\r\nContent-Length: ${bytes.size-offset}\r\n"+(if(offset>0)"Content-Range: bytes $offset-${bytes.lastIndex}/${bytes.size}\r\n" else "")+"Connection: close\r\n\r\n").toByteArray())
                        if(!request.startsWith("HEAD"))output.write(bytes,offset,bytes.size-offset)
                    } catch(_:Exception){}
                }}
            } catch(_:Exception){}
        }.apply {isDaemon=true;start()}
        override fun close(){server.close();clients.shutdownNow();accepting.join(1000)}
    }
    private fun audioCacheFiles()=(listOf(context.filesDir,context.cacheDir)).flatMap {root->root.walkTopDown().filter {it.isFile && it.extension.lowercase() in setOf("wav","mp3","opus","m4a","flac")}.map {it.absolutePath}.toList()}.toSet()

    @Test fun nativeStreamSeeksPausesAndRestoresWithoutAudioDiskCache()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val preferences=context.getSharedPreferences("playback-sessions",0)
        val old=preferences.getString("jukebox",null)
        val server=AudioServer()
        val before=audioCacheFiles()
        var initialized=false
        var activity:androidx.test.core.app.ActivityScenario<MainActivity>?=null
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);initialized=true;controller.stop();controller.clearPlaybackQueue()
                controller.normal=true;controller.effects.value=JSONObject().put("enabled",false).put("speed",85).put("reverb",25)
                controller.prepare(record=JSONObject().put("title","Native stream fixture").put("source_url",server.url).put("duration_ms",20000).put("artists",JSONArray().put("Fixture")),autoPlay=true)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            activity=androidx.test.core.app.ActivityScenario.launch(MainActivity::class.java)
            delay(200)
            activity.moveToState(androidx.lifecycle.Lifecycle.State.CREATED)
            val initial=controller.state.value.let {controller.sessionSeconds(it.model,it.index,it.phase.toDouble())}
            delay(900)
            assertTrue(controller.state.value.playing)
            assertTrue(controller.state.value.let {controller.sessionSeconds(it.model,it.index,it.phase.toDouble())}>initial+.3)
            withContext(Dispatchers.Main) {
                assertTrue(controller.state.value.model!!.has("_stream"))
                assertEquals("",controller.state.value.model!!.optString("cache"))
                controller.pause();controller.seekSeconds(5.25)
                assertTrue(controller.state.value.paused)
                assertEquals(5.25,controller.sessionSeconds(controller.state.value.model,controller.state.value.index,controller.state.value.phase.toDouble()),.02)
            }
            delay(400)
            withContext(Dispatchers.Main){assertTrue(controller.state.value.paused);controller.playPause()}
            withTimeout(10000){controller.state.first {controller.sessionSeconds(it.model,it.index,it.phase.toDouble())>5.5}}
            withContext(Dispatchers.Main){controller.pause();controller.seekSeconds(2.5);controller.seekSeconds(14.25)}
            delay(450)
            val saved=PlaybackSessions.load(context,"jukebox")!!
            assertEquals(14.25,saved.getDouble("seconds"),.02)
            assertFalse(saved.getJSONObject("model").has("_stream"))
            assertEquals(before,audioCacheFiles())
            withContext(Dispatchers.Main) {
                controller.stopPreservingPosition()
                val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
                val restored=JukeboxController(context,scope,{})
                try {
                    assertNull(restored.state.value.model)
                    assertFalse(restored.state.value.playing)
                    assertEquals("Native stream fixture",restored.state.value.title)
                    assertEquals(14.25,restored.sessionSeconds(null,0,0.0),.02)
                } finally {restored.close();scope.cancel()}
            }
        } finally {
            withContext(Dispatchers.Main){if(initialized){controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings}
            activity?.close()
            withContext(Dispatchers.Main){if(initialized)controller.savePlaybackSession(synchronous=true)}
            preferences.edit().apply {if(old==null)remove("jukebox") else putString("jukebox",old)}.commit()
            server.close()
        }
    }
    @Test fun effectsPrepareWhileNativeStreamContinuesAndReturnToStreaming()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val server=AudioServer()
        var initialized=false
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);initialized=true;controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                controller.effects.value=JSONObject().put("enabled",false).put("speed",85).put("reverb",10).put("keep_pitch",false)
                controller.prepare(record=JSONObject().put("title","Effects continuity fixture").put("source_url",server.url).put("duration_ms",20000).put("artists",JSONArray().put("Fixture")),autoPlay=true)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            withContext(Dispatchers.Main) {
                controller.setEffects("enabled",true)
                assertTrue(controller.state.value.model!!.has("_stream"))
                assertTrue(controller.state.value.playing)
                assertTrue(controller.state.value.effectsPending)
            }
            withTimeout(120000){controller.state.first {it.model!=null && !it.model.has("_stream") && it.playing && !it.effectsPending}}
            withTimeout(15000){controller.audioReady.first {it}}
            withContext(Dispatchers.Main) {
                assertTrue(java.io.File(controller.state.value.model!!.getString("cache"),"audio.wav").isFile)
                controller.setEffects("enabled",false)
                assertTrue(controller.state.value.playing)
            }
            withTimeout(90000){controller.state.first {it.model?.has("_stream")==true && it.playing && !it.effectsPending}}
            withTimeout(15000){controller.audioReady.first {it}}
            withContext(Dispatchers.Main) {
                controller.normal=false
                assertTrue(controller.state.value.model!!.has("_stream"))
                assertTrue(controller.state.value.playing)
            }
            withTimeout(120000){controller.state.first {it.model!=null && !it.model.has("_stream") && it.playing}}
            withTimeout(15000){controller.audioReady.first {it}}
        } finally {
            withContext(Dispatchers.Main){if(initialized){controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings}
            server.close()
        }
    }

    @Test fun realYouTubeAudioStreamsWithNativeHlsWithoutAudioDiskCache()=runBlocking<Unit> {
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("live_stream")=="true")
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val before=audioCacheFiles()
        lateinit var controller:JukeboxController
        var initialized=false
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);initialized=true;controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                controller.effects.value=JSONObject().put("enabled",false).put("speed",85).put("reverb",25)
                controller.prepare(record=JSONObject().put("title","aruarian dance").put("source_url","https://open.spotify.com/track/4sUTagdmyuyAxd7RvbygpQ").put("duration_ms",250433).put("artists",JSONArray().put("Nujabes")),autoPlay=true)
            }
            withTimeout(120000){controller.audioReady.first {it}}
            delay(5000)
            withContext(Dispatchers.Main) {
                assertTrue(controller.state.value.model!!.has("_stream"))
                assertTrue(controller.state.value.playing)
                controller.seekSeconds(42.25)
            }
            withTimeout(30000){controller.state.first {controller.sessionSeconds(it.model,it.index,it.phase.toDouble())>43}}
            assertEquals(before,audioCacheFiles())
        } finally {withContext(Dispatchers.Main){if(initialized){controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings}}
    }

}
