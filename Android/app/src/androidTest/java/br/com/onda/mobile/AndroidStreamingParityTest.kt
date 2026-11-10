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
    internal class AudioServer(val seconds:Int=20):AutoCloseable {
        private val server=ServerSocket(0)
        val url="http://127.0.0.1:${server.localPort}/tone.wav"
        private val clients=Executors.newFixedThreadPool(2)
        private val bytes=ByteBuffer.allocate(44+44100*4*seconds).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RIFF".toByteArray());putInt(capacity()-8);put("WAVEfmt ".toByteArray());putInt(16);putShort(1);putShort(2);putInt(44100);putInt(44100*4);putShort(4);putShort(16);put("data".toByteArray());putInt(capacity()-44)
            repeat(44100*seconds){i->val sample=(kotlin.math.sin(i*2*Math.PI*440/44100)*1000).toInt().toShort();putShort(sample);putShort(sample)}
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

    @Test fun corruptLocalStreamCacheFallsBackWithoutSearchingAgain()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val server=AudioServer()
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val ready=CompletableDeferred<Double>()
        val broken=java.io.File(context.cacheDir,"corrupt-stream-${System.nanoTime()}.mka").apply {writeBytes(ByteArray(512){127})}
        var player:AndroidStreamPlayback?=null
        try {
            withContext(Dispatchers.Main) {
                player=AndroidStreamPlayback(context,scope,JSONObject().put("duration",20).put("_stream_file",broken.absolutePath).put("_stream",JSONObject().put("url",server.url)),5.0,
                    onClock={position,playing,_,_->if(playing)ready.complete(position)},onEnded={},
                    refresh={throw AssertionError("A corrupt local cache must not trigger another catalog search")},
                    onFailure={ready.completeExceptionally(it)},prefetchAllowed={false})
                player!!.volume(0f)
            }
            val resumed=withTimeout(15000){ready.await()}
            assertTrue("Recovered stream must retain its requested position: $resumed",resumed>=4.9 && resumed<6.0)
            assertFalse(broken.exists())
        } finally {withContext(Dispatchers.Main){player?.close();scope.cancel()};broken.delete();server.close()}
    }

    @Test fun streamingClockAdvancesWhileHomeIsVisible()=runBlocking<Unit> {
        val server=AudioServer()
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val ready=CompletableDeferred<Unit>()
        var position=0.0
        var player:AndroidStreamPlayback?=null
        try {
            withContext(Dispatchers.Main) {
                player=AndroidStreamPlayback(context,scope,JSONObject().put("duration",20).put("_stream",JSONObject().put("url",server.url)),0.0,
                    onClock={seconds,playing,_,_->position=seconds;if(playing)ready.complete(Unit)},onEnded={},
                    refresh={throw AssertionError("Unexpected stream refresh")},onFailure={ready.completeExceptionally(it)},prefetchAllowed={false})
                player!!.volume(0f)
            }
            withTimeout(15000){ready.await()}
            InstrumentationRegistry.getInstrumentation().uiAutomation.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
            val before=withContext(Dispatchers.Main){position}
            val ui=InstrumentationRegistry.getInstrumentation().uiAutomation
            ui.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS)
            delay(1000)
            ui.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
            ui.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
            delay(4000)
            val after=withContext(Dispatchers.Main){position}
            assertTrue("Background stream stalled: $before -> $after",after-before>=4.0)
        } finally {withContext(Dispatchers.Main){player?.close()};scope.cancel();server.close()}
    }

    @Test fun extendedEffectsCancellationReview()=runBlocking<Unit> {
        val minutes=InstrumentationRegistry.getArguments().getString("soak_minutes")?.toIntOrNull() ?: 0
        org.junit.Assume.assumeTrue(minutes in 1..20)
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val server=AudioServer(120)
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                controller=JukeboxRuntime.get(context);controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller.effects.value=JSONObject().put("enabled",false).put("speed",85).put("reverb",0)
                controller.enqueueAll((1..4).map {n->JSONObject().put("title","Effects cancellation $n").put("source_url",server.url+"?track=$n").put("duration_ms",120000)})
                controller.playQueued(0)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            val end=android.os.SystemClock.elapsedRealtime()+minutes*60000L
            var cycle=0
            while(android.os.SystemClock.elapsedRealtime()<end) {
                withContext(Dispatchers.Main) {
                    controller.seekSeconds((5+cycle%40).toDouble())
                    controller.setEffects("enabled",true)
                    controller.setEffects("speed",80+cycle%4*5)
                    controller.setEffects("enabled",false)
                }
                delay(600)
                withContext(Dispatchers.Main){assertTrue(controller.state.value.playing);assertTrue(controller.state.value.model!!.has("_stream"))}
                if(cycle%3==0) {
                    withContext(Dispatchers.Main){controller.setEffects("enabled",true)}
                    withTimeout(120000){controller.state.first {it.model!=null && !it.model.has("_stream") && !it.effectsPending && it.playing}}
                    withTimeout(15000){controller.audioReady.first {it}}
                    withContext(Dispatchers.Main){controller.setEffects("enabled",false)}
                    withTimeout(90000){controller.state.first {it.model?.has("_stream")==true && !it.effectsPending && it.playing}}
                    withTimeout(15000){controller.audioReady.first {it}}
                }
                withContext(Dispatchers.Main) {
                    if(cycle%4==0){controller.moveQueued(3,-1);controller.playQueued((controller.nextQueueIndex).coerceAtMost(3))}
                    controller.pause();controller.playPause()
                    assertEquals("",controller.state.value.playbackError)
                }
                withTimeout(30000){controller.audioReady.first {it}}
                if(cycle%5==0)android.util.Log.i("OndaEffectsReview","Effects/cancellation cycle $cycle passed")
                delay(4500);cycle++
            }
        } finally {withContext(Dispatchers.Main){runCatching {controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings};server.close()}
    }

    @Test fun neutralEnabledEffectsStillUseNativeStreaming()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val server=AudioServer()
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                controller.effects.value=JSONObject().put("enabled",true).put("speed",100).put("reverb",0).put("keep_pitch",true)
                controller.prepare(record=JSONObject().put("title","Neutral effects").put("source_url",server.url).put("duration_ms",20000),autoPlay=true)
            }
            withTimeout(30000){controller.audioReady.first {it}}
            withContext(Dispatchers.Main){assertTrue(controller.state.value.model!!.has("_stream"));assertEquals("",controller.state.value.model!!.optString("cache"));assertFalse(controller.state.value.effectsPending)}
        } finally {withContext(Dispatchers.Main){runCatching {controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings};server.close()}
    }

    @Test fun seekDuringFinalPcmDrainKeepsPlaybackAlive()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val folder=java.io.File(context.cacheDir,"final-drain-${System.nanoTime()}").apply {mkdirs();resolve("analysis.json").writeText("{}")}
        var chunks=0
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                controller=JukeboxController(context,scope,{},callOverride={action,_,_->
                    if(action=="jukebox_chunk") {
                        val first=chunks++==0
                        val seconds=if(first)2.0 else .1
                        JSONObject().put("pcm",android.util.Base64.encodeToString(ByteArray((44100*4*seconds).toInt()),android.util.Base64.NO_WRAP))
                            .put("seconds",seconds).put("index",0).put("next",0).put("finished",first).put("edge_completed",true).put("phase_start",0).put("phase_end",1)
                    } else JSONObject()
                })
                controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                controller.playbackQueue.value=listOf(JSONObject().put("_queue_id","drain").put("title","Final drain"))
                val field=JukeboxController::class.java.getDeclaredField("preparedModels").apply {isAccessible=true}
                @Suppress("UNCHECKED_CAST") val prepared=field.get(controller) as MutableMap<String,JSONObject>
                prepared["drain"]=JSONObject().put("cache",folder.absolutePath).put("duration",30).put("beats",JSONArray(listOf(0,30))).put("media_title","Final drain")
                controller.playQueued(0)
            }
            withTimeout(10000){controller.state.first {it.elapsed>1.85}}
            withContext(Dispatchers.Main){controller.seekSeconds(5.0)}
            delay(700)
            withContext(Dispatchers.Main){assertTrue(controller.state.value.message,controller.state.value.playing);assertTrue(controller.audioReady.value);assertTrue(chunks>1)}
        } finally {withContext(Dispatchers.Main){runCatching {controller.close()};scope.cancel()};folder.resolve("analysis.json").delete();folder.delete()}
    }

    @Test fun extendedStreamingTransportReview()=runBlocking<Unit> {
        val minutes=InstrumentationRegistry.getArguments().getString("soak_minutes")?.toIntOrNull() ?: 0
        org.junit.Assume.assumeTrue(minutes in 1..20)
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val server=AudioServer(120)
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                controller=JukeboxRuntime.get(context);controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller.effects.value=JSONObject().put("enabled",false)
                controller.enqueueAll((1..4).map {n->JSONObject().put("title","Extended transport $n").put("source_url",server.url+"?track=$n").put("duration_ms",120000)})
                controller.playQueued(0)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            val end=android.os.SystemClock.elapsedRealtime()+minutes*60000L
            var cycle=0
            while(android.os.SystemClock.elapsedRealtime()<end) {
                withContext(Dispatchers.Main) {
                    controller.pause();controller.seekSeconds((5+cycle%70).toDouble());controller.playPause()
                    controller.setVolume((cycle%10)/10f)
                    if(cycle%3==0)controller.setQueueShuffle(cycle%2==0)
                    if(cycle%5==0)controller.moveQueued(3,-1)
                    if(cycle%7==0)controller.playQueued((controller.nextQueueIndex).coerceAtMost(3))
                }
                withTimeout(30000){controller.audioReady.first {it}}
                delay(1500)
                withContext(Dispatchers.Main) {
                    assertTrue(controller.state.value.message,controller.state.value.playing)
                    assertFalse(controller.state.value.paused)
                    assertEquals("",controller.state.value.playbackError)
                    controller.savePlaybackSession()
                }
                if(cycle%10==0)android.util.Log.i("OndaPlaybackReview","Transport cycle $cycle passed")
                delay(3500);cycle++
            }
        } finally {
            withContext(Dispatchers.Main){runCatching {controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings}
            server.close()
        }
    }

    @Test fun nativeStreamPrefetchesAndSeeksOfflineWithBoundedCache()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val preferences=context.getSharedPreferences("playback-sessions",0)
        val old=preferences.getString("jukebox",null)
        val server=AudioServer(120)
        val before=audioCacheFiles()
        var initialized=false
        var activity:androidx.test.core.app.ActivityScenario<MainActivity>?=null
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);initialized=true;controller.stop();controller.clearPlaybackQueue()
                controller.normal=true;controller.effects.value=JSONObject().put("enabled",false).put("speed",85).put("reverb",25)
                controller.prepare(record=JSONObject().put("title","Native stream fixture").put("source_url",server.url).put("duration_ms",120000).put("artists",JSONArray().put("Fixture")),autoPlay=true)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            withTimeout(30000){controller.streamBuffer.first {it.second>=119.9}}
            assertTrue(StreamAudioCache.size(context)>0)
            assertTrue(StreamAudioCache.size(context)<=StreamAudioCache.LIMIT)
            val cleared=withContext(Dispatchers.IO){MobileEngine.call(context,"active-stream-cache-review","cache_clear",JSONObject().put("_stream_cache_protected",JSONArray(StreamAudioCache.protectedPaths())),EventCallback {})}
            assertFalse(cleared.toString(),cleared.has("error"))
            server.close()
            withContext(Dispatchers.Main){controller.seekSeconds(100.25)}
            withTimeout(10000){controller.state.first {controller.sessionSeconds(it.model,it.index,it.phase.toDouble())>100.5}}
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
            assertTrue("Cache cleanup may remove old files, but playback must not create new audio downloads",before.containsAll(audioCacheFiles()))
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

    @Test fun visibleShuffleAndReorderKeepStreamingTransitionPrepared()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val server=AudioServer()
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_gradual_transition",true).put("jukebox_transition_seconds",2).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                controller.effects.value=JSONObject().put("enabled",false)
                controller.enqueueAll((1..4).map {n->JSONObject().put("title","Queue fixture $n").put("source_url",server.url+"?track=$n").put("duration_ms",20000)})
                controller.playQueued(0)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            val first=controller.currentQueueId.value
            withContext(Dispatchers.Main) {
                controller.setQueueShuffle(true)
                assertEquals(first,controller.playbackQueue.value.first().optString("_queue_id"))
                controller.moveQueued(3,-1)
            }
            withTimeout(90000){controller.playbackQueue.first {rows->rows.getOrNull(1)?.optString("_analysis")=="Pronta"}}
            val expected=controller.playbackQueue.value[1].optString("_queue_id")
            withContext(Dispatchers.Main){controller.seekSeconds(17.8)}
            withTimeout(15000){controller.currentQueueId.first {it==expected}}
            withTimeout(15000){controller.audioReady.first {it}}
            assertTrue(controller.state.value.playing)
            val field=JukeboxController::class.java.getDeclaredField("outgoingStream").apply {isAccessible=true}
            withContext(Dispatchers.Main){assertNotNull("Streaming must overlap while the new track starts",field.get(controller))}
            withContext(Dispatchers.Main){controller.pause()}
            delay(2400)
            withContext(Dispatchers.Main){assertNotNull(field.get(controller));assertTrue(controller.state.value.paused);controller.playPause()}
            withTimeout(10000){while(withContext(Dispatchers.Main){field.get(controller)!=null})delay(25)}
            withContext(Dispatchers.Main){assertTrue(controller.state.value.playing);controller.nextTrack()}
            withTimeout(15000){controller.audioReady.first {it}}
            withContext(Dispatchers.Main){controller.seekSeconds(5.0);assertNull("Seeking must close the outgoing stream",field.get(controller))}
        } finally {
            withContext(Dispatchers.Main){runCatching {controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings}
            server.close()
        }
    }

    @Test fun failedCollectionPreparationReleasesPendingPlaybackRequest()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val gate=CompletableDeferred<Unit>()
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                controller=JukeboxController(context,scope,{},callOverride={_,_,_->gate.await();throw IllegalStateException("fixture preparation failure")})
                controller.stop();controller.clearPlaybackQueue()
                controller.enqueueAll(listOf(JSONObject().put("title","Failed collection track").put("source_url","https://example.com/failed")))
                controller.playQueued(0)
            }
            gate.complete(Unit)
            withTimeout(10000){controller.playbackQueue.first {it.firstOrNull()?.optString("_analysis")=="Erro"}}
            withContext(Dispatchers.Main) {
                assertEquals("",controller.pendingPlaybackId.value)
                assertTrue(controller.state.value.message.contains("fixture preparation failure"))
            }
        } finally {withContext(Dispatchers.Main){runCatching {controller.close()};scope.cancel()}}
    }

    @Test fun preparedNextTrackStartsOfflineWithoutPausingOrStalling()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val settings=OndaStore.settings.value
        val server=AudioServer(120)
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(settings.toString()).put("jukebox_gradual_transition",true).put("jukebox_transition_seconds",2).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxRuntime.get(context);controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.setVolume(0f)
                controller.effects.value=JSONObject().put("enabled",false)
                controller.enqueueAll((1..2).map {n->JSONObject().put("title","Offline prepared track $n").put("source_url",server.url+"?track=$n").put("duration_ms",120000)})
                controller.playQueued(0)
            }
            withTimeout(90000){controller.audioReady.first {it}}
            withTimeout(90000){controller.playbackQueue.first {it.getOrNull(1)?.optString("_analysis")=="Pronta"}}
            // Cache the current fixture too, solely to jump to its end after disconnecting.
            val current=withContext(Dispatchers.Main){JSONObject(controller.state.value.model.toString())}
            StreamAudioCache.prefetch(context,current)
            val next=controller.playbackQueue.value[1].optString("_queue_id")
            server.close()
            withContext(Dispatchers.Main){controller.seekSeconds(117.8)}
            withTimeout(15000){controller.currentQueueId.first {it==next}}
            withTimeout(10000){controller.audioReady.first {it}}
            delay(6000)
            withContext(Dispatchers.Main){assertTrue(controller.state.value.playing);assertFalse(controller.state.value.paused);assertTrue(controller.sessionSeconds(controller.state.value.model,controller.state.value.index,controller.state.value.phase.toDouble())>5)}
        } finally {withContext(Dispatchers.Main){runCatching {controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings};server.close()}
    }

    @Test fun queuedSelectionRestartsWhenPreviousPlaybackHasNoActiveOutput()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val gate=CompletableDeferred<Unit>()
        val cache=java.io.File(context.cacheDir,"stale-playback-fixture").apply {mkdirs()}
        java.io.File(cache,"analysis.json").writeText("{}")
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                controller=JukeboxController(context,scope,{},callOverride={action,_,_->if(action=="jukebox_open")gate.await();JSONObject()})
                controller.stop();controller.clearPlaybackQueue();controller.effects.value=JSONObject().put("enabled",false)
                val model=JSONObject().put("title","Ready collection track").put("cache",cache.absolutePath).put("duration",30).put("beats",JSONArray(listOf(0,30)))
                controller.playbackQueue.value=listOf(JSONObject().put("_queue_id","stale").put("_analysis","Erro"),JSONObject().put("_queue_id","requested").put("_analysis","Pronta"))
                controller.currentQueueId.value="stale"
                controller.state.value=JukeboxState(title="Stale previous session",model=model,playing=true)
                @Suppress("UNCHECKED_CAST")
                val prepared=JukeboxController::class.java.getDeclaredField("preparedModels").apply {isAccessible=true}.get(controller) as MutableMap<String,JSONObject>
                prepared["requested"]=model
                controller.playQueued(1)
                assertEquals("requested",controller.currentQueueId.value)
                val pending=JukeboxController::class.java.getDeclaredField("switchRequest").apply {isAccessible=true}.get(controller) as java.util.concurrent.atomic.AtomicReference<*>
                assertNull("No transition may wait on an absent audio worker",pending.get())
            }
        } finally {withContext(Dispatchers.Main){runCatching {controller.close()};scope.cancel();gate.complete(Unit)};java.io.File(cache,"analysis.json").delete();cache.delete()}
    }

    @Test fun realYouTubeHlsPrefetchesFullTrackWithoutProcessedAudioFiles()=runBlocking<Unit> {
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
            withTimeout(150000){controller.streamBuffer.first {it.first==0.0 && it.second>=controller.state.value.model!!.optDouble("duration")-.1}}
            assertTrue(StreamAudioCache.size(context)>0)
            assertTrue(StreamAudioCache.size(context)<=StreamAudioCache.LIMIT)
            withContext(Dispatchers.Main) {
                assertTrue(controller.state.value.model!!.has("_stream"))
                assertTrue(controller.state.value.playing)
                controller.seekSeconds(42.25)
            }
            withTimeout(30000){controller.state.first {controller.sessionSeconds(it.model,it.index,it.phase.toDouble())>43}}
            assertEquals(before,audioCacheFiles())
        } finally {withContext(Dispatchers.Main){if(initialized){controller.stop();controller.clearPlaybackQueue()};OndaStore.settings.value=settings}}
    }

    @Test fun gradualStreamingActuallyOverlapsBothPlayers()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val saved=OndaStore.settings.value
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val server=AudioServer(8)
        lateinit var controller:JukeboxController
        try {
            withContext(Dispatchers.Main) {
                OndaStore.settings.value=JSONObject(saved.toString()).put("jukebox_gradual_transition",true).put("jukebox_transition_seconds",2).put("jukebox_equalizer",JSONObject().put("enabled",false))
                controller=JukeboxController(context,scope,{},callOverride={_,config,_->
                    val record=config.getJSONObject("record")
                    JSONObject().put("title",record.optString("title")).put("duration",8.0).put("beats",JSONArray().put(0.0).put(8.0)).put("links",0)
                        .put("_stream",JSONObject().put("url",record.getString("source_url")).put("source_url",record.getString("source_url")))
                })
                controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.effects.value=JSONObject().put("enabled",false);controller.setVolume(0f)
                controller.enqueueAll((1..2).map {n->JSONObject().put("title","Fade $n").put("source_url",server.url+"?fade=$n")})
            }
            withTimeout(20000){while(controller.playbackQueue.value.count {it.optString("_analysis")=="Pronta"}<2)delay(30)}
            withContext(Dispatchers.Main){controller.playQueued(0)}
            withTimeout(10000){controller.audioReady.first {it}}
            var overlap=false
            withTimeout(13000) {
                while(!overlap) {
                    withContext(Dispatchers.Main) {
                        val outgoing=controller.javaClass.getDeclaredField("outgoingStream").apply {isAccessible=true}.get(controller)
                        val incoming=controller.javaClass.getDeclaredField("streaming").apply {isAccessible=true}.get(controller)
                        val gain=controller.javaClass.getDeclaredField("streamGain").apply {isAccessible=true}.getFloat(controller)
                        fun playing(instance:Any?):Boolean=instance?.javaClass?.getDeclaredField("player")?.apply {isAccessible=true}?.get(instance)?.let {(it as androidx.media3.exoplayer.ExoPlayer).isPlaying} ?: false
                        overlap=playing(outgoing)&&playing(incoming)&&gain>0f&&gain<1f
                    }
                    delay(30)
                }
            }
            assertTrue(overlap)
        } finally {withContext(Dispatchers.Main){controller.close();scope.cancel();OndaStore.settings.value=saved};server.close()}
    }

    @Test fun gradualTransitionAlsoOverlapsStreamingAndProcessedAudio()=runBlocking<Unit> {
        withContext(Dispatchers.Main){OndaStore.initialize(context);MobileEngine.initialize(context)}
        val saved=OndaStore.settings.value
        val server=AudioServer(8)
        val source=java.io.File(context.cacheDir,"mixed-fade-${System.nanoTime()}.wav")
        try {
            withContext(Dispatchers.IO){source.writeBytes(java.net.URL(server.url).readBytes())}
            val local=withContext(Dispatchers.IO){MobileEngine.call(context,"mixed-fade-prepare","jukebox_prepare",OndaStore.config().put("source",source.absolutePath).put("stream",false),EventCallback {})}
            assertFalse(local.toString(),local.has("error"))
            for(streamFirst in listOf(true,false)) {
                val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
                lateinit var controller:JukeboxController
                try {
                    withContext(Dispatchers.Main) {
                        OndaStore.settings.value=JSONObject(saved.toString()).put("jukebox_gradual_transition",true).put("jukebox_transition_seconds",2).put("jukebox_equalizer",JSONObject().put("enabled",false))
                        controller=JukeboxController(context,scope,{},callOverride={action,config,id->
                            if(action=="jukebox_prepare") {
                                if(config.optString("source").isNotBlank())JSONObject(local.toString())
                                else JSONObject().put("title","Stream").put("duration",8.0).put("beats",JSONArray().put(0.0).put(8.0)).put("links",0).put("_stream",JSONObject().put("url",server.url).put("source_url",server.url))
                            } else withContext(Dispatchers.IO){MobileEngine.call(context,id,action,config,EventCallback {})}
                        })
                        controller.stop();controller.clearPlaybackQueue();controller.normal=true;controller.effects.value=JSONObject().put("enabled",false);controller.setVolume(0f)
                        val records=listOf(JSONObject().put("title","Stream").put("source_url",server.url),JSONObject().put("title","Local").put("_local_source",source.absolutePath))
                        controller.enqueueAll(if(streamFirst)records else records.reversed())
                    }
                    withTimeout(30000){while(controller.playbackQueue.value.count {it.optString("_analysis")=="Pronta"}<2)delay(30)}
                    withContext(Dispatchers.Main){controller.playQueued(0)}
                    withTimeout(10000){controller.audioReady.first {it}}
                    var overlap=false
                    withTimeout(14000) {
                        while(!overlap) {
                            withContext(Dispatchers.Main) {
                                fun field(name:String)=controller.javaClass.getDeclaredField(name).apply {isAccessible=true}.get(controller)
                                fun streamPlaying(instance:Any?)=instance?.javaClass?.getDeclaredField("player")?.apply {isAccessible=true}?.get(instance)?.let {(it as androidx.media3.exoplayer.ExoPlayer).isPlaying} ?: false
                                if(streamFirst) {
                                    val output=field("track") as? android.media.AudioTrack
                                    val gain=field("startGain") as Float
                                    overlap=streamPlaying(field("outgoingStream")) && output?.playState==android.media.AudioTrack.PLAYSTATE_PLAYING && gain>0f&&gain<1f
                                } else {
                                    val tail=field("outgoingPcm")
                                    val output=tail?.javaClass?.getDeclaredField("output")?.apply {isAccessible=true}?.get(tail) as? android.media.AudioTrack
                                    val gain=field("streamGain") as Float
                                    overlap=streamPlaying(field("streaming"))&&output?.playState==android.media.AudioTrack.PLAYSTATE_PLAYING&&gain>0f&&gain<1f
                                }
                            }
                            delay(30)
                        }
                    }
                    assertTrue("Mixed audio must overlap (stream first=$streamFirst)",overlap)
                    delay(2600)
                    withContext(Dispatchers.Main) {
                        assertNull(controller.javaClass.getDeclaredField("outgoingStream").apply {isAccessible=true}.get(controller))
                        assertNull(controller.javaClass.getDeclaredField("outgoingPcm").apply {isAccessible=true}.get(controller))
                        assertTrue(controller.state.value.playing)
                    }
                } finally {withContext(Dispatchers.Main){controller.close();scope.cancel()};delay(150)}
            }
        } finally {withContext(Dispatchers.Main){OndaStore.settings.value=saved};server.close();source.delete()}
    }

}
