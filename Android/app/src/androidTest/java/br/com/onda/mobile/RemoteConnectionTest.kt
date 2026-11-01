package br.com.onda.mobile

import android.graphics.BitmapFactory
import android.graphics.Bitmap
import java.io.ByteArrayOutputStream
import androidx.test.platform.app.InstrumentationRegistry
import com.google.zxing.*
import com.google.zxing.common.HybridBinarizer
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.net.NetworkInterface
import java.net.ServerSocket
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Collections
import java.util.concurrent.CopyOnWriteArrayList

class RemoteConnectionTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun readsQrGeneratedByDesktopAndRejectsForeignCodes() {
        val testContext=InstrumentationRegistry.getInstrumentation().context
        val bitmap=testContext.assets.open("remote-pair.png").use {BitmapFactory.decodeStream(it)}
        val pixels=IntArray(bitmap.width*bitmap.height)
        bitmap.getPixels(pixels,0,bitmap.width,0,0,bitmap.width,bitmap.height)
        val decoded=MultiFormatReader().decode(BinaryBitmap(HybridBinarizer(RGBLuminanceSource(bitmap.width,bitmap.height,pixels))))
        val pair=parseRemotePairing(decoded.text)
        assertEquals("http://192.168.1.9:12345",pair.address);assertEquals("123456",pair.code)
        for(value in listOf("https://example.com","onda://pair?address=http%3A%2F%2F8.8.8.8%3A99&code=123456","onda://pair?address=x&code=123456&code=654321")) {
            try {parseRemotePairing(value);fail("Should reject foreign QR")}catch(_:IllegalArgumentException){}
        }
        bitmap.recycle()
    }

    /** Actual HTTP and native PCM, without internet matching or a personal music file. */
    @Test fun connectsWithoutPausingTransfersExactPositionAndHonorsPcRevocation()=runBlocking {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val local=withContext(Dispatchers.Main) {JukeboxRuntime.get(context)}
        val saved=PlaybackSessions.load(context,"jukebox")
        val root=File(context.cacheDir,"remote-flow-${System.nanoTime()}").apply {mkdirs()}
        val audio=File(root,"fixture.wav")
        val pcm=ByteArray(44100*4*12)
        val header=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).put("RIFF".toByteArray()).putInt(36+pcm.size).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1).putShort(2).putInt(44100).putInt(176400).putShort(4).putShort(16).put("data".toByteArray()).putInt(pcm.size).array()
        audio.outputStream().use {it.write(header);it.write(pcm)}
        val server=FixturePc(audio.readBytes()).apply {features=5;commandResponseLost=true}
        try {
            val model=withContext(Dispatchers.IO) {MobileEngine.call(context,"handoff-flow-prepare","jukebox_prepare",OndaStore.config().put("source",audio.absolutePath),EventCallback {})}
            assertFalse(model.toString(),model.has("error"))
            val bookmark=JukeboxState(title="Phone bookmark",model=model,index=1,phase=.4f)
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.disconnect()
                local.clearPlaybackQueue();local.state.value=bookmark
                RemotePlaybackRuntime.connect(context,server.address,"123456")
            }
            withTimeout(5000){while(!RemotePlaybackRuntime.state.value.online)delay(20)}
            assertEquals("PC song",RemotePlaybackRuntime.state.value.title)
            withTimeout(5000){while(RemotePlaybackRuntime.state.value.artwork==null)delay(20)}
            val cover=RemotePlaybackRuntime.state.value.artwork!!
            assertNotNull(BitmapFactory.decodeByteArray(cover,0,cover.size))
            assertEquals("https://i.scdn.co/image/test",RemotePlaybackRuntime.state.value.artworkUrl)
            assertTrue("Connecting must not send pause or transfer",server.commands.isEmpty())
            assertEquals(bookmark.index,local.state.value.index)
            assertEquals(bookmark.phase,local.state.value.phase)
            val exactStream=JSONObject().put("_stream",JSONObject().put("url",server.address+"/audio.wav").put("headers",JSONObject()))
                .put("duration",12).put("title","PC song").put("media_title","PC song").put("media_artist","Artist")
            val received=withContext(Dispatchers.Main) {local.prepareResolvedHandoff(exactStream)}
            assertTrue(File(received.getString("source")).isFile)
            withContext(Dispatchers.Main) {RemotePlaybackRuntime.transferToPhone(context,prepareOverride={received})}
            assertFalse(RemotePlaybackRuntime.state.value.connected)
            withTimeout(5000) {while(!local.state.value.playing)delay(20)}
            val position=local.sessionSeconds(local.state.value.model,local.state.value.index,local.state.value.phase.toDouble())
            assertTrue("Expected transfer near 5.25 seconds, got $position",position in 5.0..7.0)
            assertTrue(server.commands.contains("handoff_release"))
            server.prepareReady=false
            withContext(Dispatchers.Main) {
                val reverse=async {RemotePlaybackRuntime.reconnect(context,server.address,transferPlayback=true)}
                withTimeout(3000){while(!server.commands.contains("handoff_prepare"))delay(10)}
                assertTrue("Phone must keep playing while PC prepares",local.state.value.playing)
                server.prepareReady=true
                assertTrue(reverse.await())
            }
            assertFalse("Phone must stop only after PC acknowledgement",local.state.value.playing)
            assertTrue(server.commands.contains("handoff_commit"))
            assertTrue(server.remotePlaying)
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.disconnect();server.remotePlaying=false;server.features=4
                RemotePlaybackRuntime.connect(context,server.address,"123456")
                RemotePlaybackRuntime.transferToPhone(context,prepareOverride={received})
                assertFalse("Paused transfer must not open local output",local.state.value.playing)
                assertFalse(local.audioReady.value)
                assertTrue(RemotePlaybackRuntime.reconnect(context,server.address,transferPlayback=true))
                assertFalse("Paused transfer must remain paused on PC",server.remotePlaying)
            }
            withContext(Dispatchers.Main) {local.stopPreservingPosition();RemotePlaybackRuntime.connect(context,server.address,"123456")}
            withTimeout(5000){while(!RemotePlaybackRuntime.state.value.online)delay(20)}
            val before=local.state.value
            server.revoked=true
            withTimeout(5000){while(RemotePlaybackRuntime.state.value.connected)delay(20)}
            assertEquals(before.index,local.state.value.index)
            assertEquals(before.phase,local.state.value.phase)
        } finally {
            withContext(Dispatchers.Main) {RemotePlaybackRuntime.disconnect();local.clearPlaybackQueue();local.stop()}
            PlaybackSessions.save(context,"jukebox",saved ?: JSONObject().put("queue",JSONArray()),true)
            server.close();root.deleteRecursively()
        }
    }

    @Test fun cancelledPairingCannotReconnectAfterDisconnect()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf()).apply {pairDelay=600}
        try {
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.disconnect()
                val pending=async {RemotePlaybackRuntime.connect(context,server.address,"123456")}
                withTimeout(3000){while(server.pairedRequests==0)delay(10)}
                RemotePlaybackRuntime.disconnect()
                try {pending.await();fail("Old attempt must be cancelled")}catch(_:CancellationException){}
                assertFalse(RemotePlaybackRuntime.state.value.connected)
            }
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun newerPairingWinsAndOldResponseCannotReplaceDevice()=runBlocking {
        OndaStore.initialize(context)
        val slow=FixturePc(byteArrayOf()).apply {pairDelay=600}
        val fast=FixturePc(byteArrayOf())
        try {
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.disconnect()
                val first=async {RemotePlaybackRuntime.connect(context,slow.address,"123456")}
                withTimeout(3000){while(slow.pairedRequests==0)delay(10)}
                RemotePlaybackRuntime.connect(context,fast.address,"123456")
                try {first.await();fail("Old attempt must be cancelled")}catch(_:CancellationException){}
                assertEquals(fast.address,RemotePlaybackRuntime.state.value.address)
            }
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};slow.close();fast.close()}
    }

    @Test fun queueFailureDoesNotDisableTransportAndRapidToggleKeepsParity()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf()).apply {queueFailure=true}
        try {
            withContext(Dispatchers.Main){RemotePlaybackRuntime.connect(context,server.address,"123456")}
            delay(2000)
            assertTrue(RemotePlaybackRuntime.state.value.connected)
            assertTrue(RemotePlaybackRuntime.state.value.online)
            withContext(Dispatchers.Main){RemotePlaybackRuntime.toggle();RemotePlaybackRuntime.toggle()}
            withTimeout(3000){while(server.commands.count {it=="toggle"}<2)delay(10)}
            assertTrue(server.remotePlaying)
            server.queueFailure=false
            withTimeout(3000){while(RemotePlaybackRuntime.state.value.queueRevision!=0L)delay(10)}
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun trackChangeDuringPreparationDoesNotPausePcOrReplaceLocalSong()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf())
        val local=withContext(Dispatchers.Main){JukeboxRuntime.get(context)}
        try {
            withContext(Dispatchers.Main){RemotePlaybackRuntime.connect(context,server.address,"123456")}
            val previous=local.state.value
            try {
                withContext(Dispatchers.Main){RemotePlaybackRuntime.transferToPhone(context,prepareOverride={server.trackId="changed";JSONObject()})}
                fail("Changed source must abort transfer")
            }catch(_:IllegalStateException){}
            assertSame(previous,local.state.value)
            assertFalse(server.commands.contains("handoff_release"))
            assertTrue(server.remotePlaying)
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun disconnectCancelsPreparationAndLeavesSourcePlaying()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf())
        val entered=CompletableDeferred<Unit>();val cancelled=CompletableDeferred<Unit>()
        try {
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.connect(context,server.address,"123456")
                val transfer=async {RemotePlaybackRuntime.transferToPhone(context,prepareOverride={
                    entered.complete(Unit)
                    try {awaitCancellation()}finally {cancelled.complete(Unit)}
                })}
                entered.await();RemotePlaybackRuntime.disconnect()
                try {transfer.await();fail("Transfer should be cancelled")}catch(_:CancellationException){}
                withTimeout(3000){cancelled.await()}
                assertFalse(RemotePlaybackRuntime.transferring.value)
            }
            assertFalse(server.commands.contains("handoff_release"))
            assertTrue(server.remotePlaying)
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun temporaryReconnectFailureKeepsTheExistingPairing()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf())
        try {
            withContext(Dispatchers.Main){RemotePlaybackRuntime.connect(context,server.address,"123456");RemotePlaybackRuntime.disconnect()}
            server.stateFailures=1
            withContext(Dispatchers.Main) {
                try {RemotePlaybackRuntime.reconnect(context,server.address);fail("Expected temporary server failure")}
                catch(error:RemoteHttpException){assertEquals(503,error.status)}
                assertTrue(RemotePlaybackRuntime.reconnect(context,server.address))
            }
            assertEquals(1,server.pairedRequests)
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun incompatibleFirstSnapshotDoesNotActivateRemoteSession()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf()).apply {stateProtocol=99}
        try {
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.disconnect()
                try {RemotePlaybackRuntime.connect(context,server.address,"123456");fail("Expected incompatible protocol")}
                catch(_:IllegalArgumentException){}
                assertFalse(RemotePlaybackRuntime.state.value.connected)
            }
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun nativeOutputFailureRestoresPcAndDoesNotCompleteTransfer()=runBlocking {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val server=FixturePc(byteArrayOf()).apply {features=5}
        val folder=File(context.cacheDir,"bad-handoff-${System.nanoTime()}").apply {mkdirs()}
        val local=withContext(Dispatchers.Main){JukeboxRuntime.get(context)}
        val saved=PlaybackSessions.load(context,"jukebox")
        val bad=JSONObject().put("cache",folder.absolutePath).put("source",File(folder,"missing.wav").absolutePath)
            .put("title","Broken fixture").put("duration",12).put("beats",JSONArray().put(0).put(12)).put("neighbors",JSONArray().put(JSONArray()))
        File(folder,"analysis.json").writeText(bad.toString())
        try {
            withContext(Dispatchers.Main) {
                RemotePlaybackRuntime.connect(context,server.address,"123456")
                try {RemotePlaybackRuntime.transferToPhone(context,prepareOverride={bad});fail("Missing audio must fail")}
                catch(_:IllegalStateException){}
            }
            assertTrue(server.remotePlaying)
            assertTrue(server.commands.contains("handoff_cancel"))
            assertFalse(server.commands.contains("handoff_complete"))
            assertFalse(local.state.value.playing)
        } finally {
            withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect();local.clearPlaybackQueue();local.stop()}
            PlaybackSessions.save(context,"jukebox",saved ?: JSONObject().put("queue",JSONArray()),true)
            server.close();folder.deleteRecursively()
        }
    }

    @Test fun repeatedImmediateConnectDisconnectDoesNotCrashForegroundService()=runBlocking {
        OndaStore.initialize(context)
        val server=FixturePc(byteArrayOf())
        try {
            withContext(Dispatchers.Main) {
                repeat(12) {
                    RemotePlaybackRuntime.connect(context,server.address,"123456")
                    RemotePlaybackRuntime.disconnect()
                }
                RemotePlaybackRuntime.connect(context,server.address,"123456")
            }
            delay(6000)
            assertTrue(RemotePlaybackRuntime.state.value.connected)
            assertTrue(RemotePlaybackRuntime.state.value.online)
            withContext(Dispatchers.Main){RemotePlaybackRuntime.toggle()}
            withTimeout(3000){while(!server.commands.contains("toggle"))delay(10)}
        } finally {withContext(Dispatchers.Main){RemotePlaybackRuntime.disconnect()};server.close()}
    }

    @Test fun cancellingBlockedNativeAudioPreparationStopsTheWorker()=runBlocking {
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val server=FixturePc(byteArrayOf()).apply {holdAudio=true}
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
        val controller=JukeboxController(context,scope,{})
        try {
            val model=JSONObject().put("_stream",JSONObject().put("url",server.address+"/audio.wav").put("headers",JSONObject()))
                .put("duration",12).put("title","Blocked fixture")
            val preparation=async {controller.prepareResolvedHandoff(model)}
            withTimeout(5000){while(!server.audioRequested)delay(10)}
            withTimeout(5000){preparation.cancelAndJoin()}
            assertTrue(preparation.isCancelled)
        } finally {
            withContext(Dispatchers.Main){controller.close()};scope.cancel();server.close()
        }
    }

    private class FixturePc(private val audio:ByteArray):AutoCloseable {
        private val socket=ServerSocket(0)
        private val host=Collections.list(NetworkInterface.getNetworkInterfaces()).flatMap {Collections.list(it.inetAddresses)}.first {it.isSiteLocalAddress && it.hostAddress?.contains(':')==false}.hostAddress!!
        val address="http://$host:${socket.localPort}"
        val commands=CopyOnWriteArrayList<String>()
        private val cover=ByteArrayOutputStream().also {output->
            val bitmap=Bitmap.createBitmap(4,4,Bitmap.Config.ARGB_8888)
            bitmap.eraseColor(android.graphics.Color.CYAN);bitmap.compress(Bitmap.CompressFormat.PNG,100,output);bitmap.recycle()
        }.toByteArray()
        @Volatile var revoked=false
        @Volatile var pairDelay=0L
        @Volatile var queueFailure=false
        @Volatile var stateFailures=0
        @Volatile var stateProtocol=1
        @Volatile var holdAudio=false
        @Volatile var audioRequested=false
        @Volatile var features=4
        @Volatile var trackId="current"
        @Volatile var remotePlaying=true
        @Volatile var prepareReady=true
        @Volatile var rejectCommit=false
        @Volatile var commandResponseLost=false
        @Volatile var pairedRequests=0
        @Volatile var position=5.25
        private var result=JSONObject()
        private val thread=Thread {
            while(!socket.isClosed) {
                try {socket.accept().use {client->
                    client.soTimeout=3000
                    val input=client.getInputStream().bufferedReader()
                    val request=input.readLine().split(' ')
                    var size=0
                    while(true) {val line=input.readLine();if(line.isEmpty())break;if(line.startsWith("Content-Length:",true))size=line.substringAfter(':').trim().toInt()}
                    val chars=CharArray(size);var read=0
                    while(read<size){val count=input.read(chars,read,size-read);if(count<0)break;read+=count}
                    val body=if(size>0)JSONObject(String(chars)) else JSONObject()
                    val path=request[1]
                    if(path.startsWith("/v1/artwork")) {
                        client.getOutputStream().apply {write("HTTP/1.1 200 OK\r\nContent-Type: image/png\r\nContent-Length: ${cover.size}\r\nConnection: close\r\n\r\n".toByteArray());write(cover);flush()}
                        return@use
                    }
                    if(path=="/audio.wav") {
                        audioRequested=true
                        while(holdAudio && !socket.isClosed)Thread.sleep(20)
                        client.getOutputStream().apply {write("HTTP/1.1 200 OK\r\nContent-Type: audio/wav\r\nContent-Length: ${audio.size}\r\nConnection: close\r\n\r\n".toByteArray());write(audio);flush()}
                        return@use
                    }
                    if(path=="/v1/pair"){pairedRequests++;if(pairDelay>0)Thread.sleep(pairDelay)}
                    if((path.startsWith("/v1/queue") && queueFailure) || (path=="/v1/state" && stateFailures>0)) {
                        if(path=="/v1/state")stateFailures--
                        val payload="{}".toByteArray()
                        client.getOutputStream().apply {write("HTTP/1.1 503 Busy\r\nContent-Type: application/json\r\nContent-Length: ${payload.size}\r\nConnection: close\r\n\r\n".toByteArray());write(payload);flush()}
                        return@use
                    }
                    if(result.optString("status")=="preparing" && prepareReady)result.put("status","ready")
                    val response=when {
                        path=="/v1/pair"->JSONObject().put("token","test-credential-with-at-least-20-characters").put("name","Fixture PC").put("protocol",1).put("features",features)
                        path=="/v1/command"->{
                            val command=body.getString("command");commands.add(command)
                            val value=body.optJSONObject("value") ?: JSONObject()
                            when(command) {
                                "handoff_prepare"->result=JSONObject().put("id",value.getString("id")).put("status",if(prepareReady)"ready" else "preparing")
                                "handoff_commit"->{
                                    result.put("status",if(rejectCommit)"error" else "started").put("track_id",trackId)
                                    position=value.optDouble("position");remotePlaying=value.optBoolean("playing")
                                }
                                "handoff_release"->{result=JSONObject().put("id",value.getString("id")).put("status","released").put("position",position).put("playing",remotePlaying);remotePlaying=false}
                                "handoff_complete"->result.put("status","complete")
                                "handoff_cancel"->{result.put("status","cancelled");remotePlaying=true}
                                "toggle"->remotePlaying=!remotePlaying
                            }
                            if(command=="handoff_complete" && commandResponseLost)return@use
                            JSONObject().put("accepted",true)
                        }
                        path.startsWith("/v1/queue")->JSONObject().put("rows",JSONArray()).put("revision",0).put("total",0)
                        else->JSONObject().put("protocol",stateProtocol).put("features",features).put("title","PC song").put("artist","Artist").put("track_id",trackId).put("ready",true).put("playing",remotePlaying).put("duration",12).put("position",position).put("queue_revision",0).put("artwork_id","a".repeat(24)).put("cover_url","https://i.scdn.co/image/test").put("transfer_record",JSONObject().put("title","PC song").put("artists",JSONArray().put("Artist")).put("source_url","https://open.spotify.com/track/test")).put("handoff",result)
                    }
                    val payload=(if(revoked)JSONObject().put("error","Disabled") else response).toString().toByteArray()
                    client.getOutputStream().apply {write("HTTP/1.1 ${if(revoked)410 else 200} OK\r\nContent-Type: application/json\r\nContent-Length: ${payload.size}\r\nConnection: close\r\n\r\n".toByteArray());write(payload);flush()}
                }}catch(_:Exception){if(socket.isClosed)break}
            }
        }.apply {isDaemon=true;start()}
        override fun close(){holdAudio=false;socket.close();thread.join(2000)}
    }
}
