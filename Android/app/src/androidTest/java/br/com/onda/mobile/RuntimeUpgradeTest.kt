package br.com.onda.mobile

import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class RuntimeUpgradeTest {
    @Test fun formatsEffectsFingerprintAndVideoUseUpdatedNativeTools() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        MobileEngine.initialize(context)
        val scope = Python.getInstance().getModule("builtins").callAttr("dict")
        scope.callAttr("__setitem__", "folder", context.cacheDir.absolutePath)
        Python.getInstance().getModule("builtins").callAttr(
            "exec",
            """
import sys, json, subprocess, tempfile, hashlib, threading, ssl, sqlite3
from pathlib import Path
from PIL import Image
from mobile_backend import _native
from audio_tools import effects_filter
from audio_library import read_audio, write_audio
from android_fingerprint import fingerprint
from video_converter import convert_video, probe_video
assert sys.version_info[:2] == (3, 13)
ffmpeg = str(_native/'libffmpeg.so')
def run(args):
    result = subprocess.run(args, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    return result.stdout.decode(errors='replace')
version = run([ffmpeg, '-version']).splitlines()[0]
assert '9.0.2' in version, version
assert run([str(_native/'libqjs.so'), '-e', 'console.log([3,1,2].toSorted().join(","))']).strip() == '1,2,3'
with tempfile.TemporaryDirectory(dir=folder) as work:
    root = Path(work)
    source = root/'source.wav'
    run([ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=44100:duration=22',str(source)])
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    cover = root/'cover.png'; Image.new('RGB',(32,32),'blue').save(cover)
    for fmt in ('PNG','JPEG','WEBP'):
        picture=root/('picture.'+fmt.lower())
        Image.new('RGB',(32,32),'blue').save(picture,format=fmt)
        assert Image.open(picture).size==(32,32)
    for suffix in ('mp3','m4a','flac','ogg','opus'):
        target=root/('audio.'+suffix)
        run([ffmpeg,'-v','error','-i',str(source),'-t','1',str(target)])
        write_audio(target,{'title':'Compatibilidade','artists':['ONDA']},str(cover))
        assert read_audio(target)['title'] == 'Compatibilidade'
    for keep_pitch in (False, True):
        target=root/('effects-'+str(keep_pitch)+'.wav')
        run([ffmpeg,'-v','error','-i',str(source),'-t','1','-af',effects_filter(85,25,keep_pitch),str(target)])
        assert read_audio(target)['duration'] > 0
    fp=fingerprint(str(source),threading.Event())
    assert fp['duration']==22 and fp['fingerprint']
    video=root/'source.mp4'
    run([ffmpeg,'-v','error','-f','lavfi','-i','testsrc2=size=64x64:rate=10:duration=1','-f','lavfi','-i','sine=duration=1','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',str(video)])
    for fmt in ('MP4','MKV','MOV'):
        target=root/('converted.'+fmt.lower())
        convert_video({'source':str(video),'output':str(target),'video_format':fmt})
        assert probe_video(target)['has_audio']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original
report=json.dumps({'python':sys.version.split()[0],'openssl':ssl.OPENSSL_VERSION,'sqlite':sqlite3.sqlite_version,'ffmpeg':version,'audio_formats':5,'video_formats':3,'effects':2,'fingerprint':True})
""".trimIndent(),
            scope
        )
        android.util.Log.i("ONDA-Runtime", scope.callAttr("__getitem__", "report").toString())
    }

    @Test fun mediaPlayerPlaysAndSeeksAudioPreparedByFfmpeg() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        MobileEngine.initialize(context)
        val file = File(context.cacheDir, "runtime-playback.wav")
        val scope = Python.getInstance().getModule("builtins").callAttr("dict")
        scope.callAttr("__setitem__", "output", file.absolutePath)
        Python.getInstance().getModule("builtins").callAttr(
            "exec",
            """
import subprocess
from mobile_backend import _native
subprocess.run([str(_native/'libffmpeg.so'),'-v','error','-y','-f','lavfi','-i','sine=duration=4',output],check=True,timeout=30)
""".trimIndent(),
            scope
        )
        val ready = CountDownLatch(1)
        var player: ExoPlayer? = null
        try {
            instrumentation.runOnMainSync {
                player = ExoPlayer.Builder(context).build().apply {
                    volume = 0f
                    addListener(object : Player.Listener {
                        override fun onPlaybackStateChanged(state: Int) {
                            if (state ==
                                Player.STATE_READY
                            ) ready.countDown()
                        }
                    })
                    setMediaItem(MediaItem.fromUri(android.net.Uri.fromFile(file)))
                    prepare()
                    play()
                }
            }
            assertTrue("O áudio não ficou pronto", ready.await(15, TimeUnit.SECONDS))
            Thread.sleep(700)
            instrumentation.runOnMainSync {
                assertTrue(player!!.currentPosition > 0)
                player!!.seekTo(2000)
            }
            Thread.sleep(400)
            instrumentation.runOnMainSync {
                assertTrue(player!!.currentPosition >= 1900)
                player!!.pause()
            }
        } finally {
            instrumentation.runOnMainSync { player?.release() }
            file.delete()
        }
    }
}
