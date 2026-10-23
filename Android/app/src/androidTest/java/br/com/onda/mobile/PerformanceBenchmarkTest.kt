package br.com.onda.mobile

import android.os.*
import android.system.Os
import android.system.OsConstants
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.Collections
import java.util.Random
import java.util.concurrent.atomic.AtomicBoolean

/** Diagnostics only: local synthetic media and app-private temporary data. */
@RunWith(AndroidJUnit4::class)
class PerformanceBenchmarkTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private val output get()=File(context.filesDir,"performance-results.json")
    private val page=Os.sysconf(OsConstants._SC_PAGESIZE).toDouble()
    private val hz=Os.sysconf(OsConstants._SC_CLK_TCK).toDouble()
    private data class Counters(val rss:Double,val cpu:Double,val processes:Int)
    private var lastObservedProcesses=emptySet<Int>()
    private fun counters():Counters {
        // Android does not expose task/children on every kernel. Read stat
        // only for this application's UID, then select its own process tree.
        val stats=mutableMapOf<Int,List<String>>()
        File("/proc").listFiles()?.forEach {directory->
            val pid=directory.name.toIntOrNull()
            if(pid!=null)runCatching {
                if(Os.stat(directory.path).st_uid==Process.myUid()) {
                    val stat=File(directory,"stat").readText()
                    stats[pid]=stat.substring(stat.lastIndexOf(')')+2).trim().split(Regex("\\s+"))
                }
            }
        }
        check(stats.containsKey(Process.myPid())) {"Não foi possível medir o processo do aplicativo"}
        val ids=mutableSetOf(Process.myPid())
        repeat(10) {ids.addAll(stats.filter {it.value[1].toInt() in ids}.keys)}
        lastObservedProcesses=ids.toSet()
        var rss=0.0;var ticks=0.0
        for(id in ids)runCatching {
            val values=stats.getValue(id)
            rss+=values[21].toDouble()*page
            // Reaped descendants are accumulated in cutime/cstime. Live
            // children are counted above, so FFmpeg CPU is included too.
            ticks+=(11..14).sumOf {values[it].toDouble()}
        }
        return Counters(rss/1048576,ticks/hz,ids.size)
    }
    private fun measure(name:String,action:()->Unit):JSONObject {
        val running=AtomicBoolean(true);val samples=Collections.synchronizedList(mutableListOf<Counters>())
        val lags=Collections.synchronizedList(mutableListOf<Double>())
        val handler=Handler(Looper.getMainLooper());var last=SystemClock.uptimeMillis()
        val pulse=object:Runnable {override fun run() {val now=SystemClock.uptimeMillis();lags.add((now-last-20L).coerceAtLeast(0).toDouble());last=now;if(running.get())handler.postDelayed(this,20)}}
        handler.postDelayed(pulse,20)
        val sample=Thread {while(running.get()){samples.add(counters());Thread.sleep(100)}}
        val before=counters();val start=SystemClock.elapsedRealtimeNanos();sample.start()
        try {action()} finally {running.set(false);sample.join();handler.removeCallbacks(pulse)}
        val elapsed=(SystemClock.elapsedRealtimeNanos()-start)/1e9;val after=counters();val cpu=(after.cpu-before.cpu).coerceAtLeast(0.0)
        val ordered=lags.toList().sorted()
        return JSONObject().put("name",name).put("wall_s",elapsed).put("cpu_s",cpu).put("cpu_one_core_pct",cpu/elapsed*100)
            .put("cpu_machine_pct",cpu/elapsed*100/Runtime.getRuntime().availableProcessors())
            .put("peak_rss_mb",(samples.map {it.rss}+before.rss+after.rss).maxOrNull() ?: 0)
            .put("median_rss_mb",samples.map {it.rss}.sorted().let {if(it.isEmpty())0.0 else it[it.size/2]})
            .put("peak_processes",samples.maxOfOrNull {it.processes} ?: 1)
            .put("ui_lag_p95_ms",if(ordered.isEmpty())0.0 else ordered[((ordered.size-1)*.95).toInt()])
            .put("ui_lag_max_ms",ordered.lastOrNull() ?: 0.0)
    }
    private fun write(result:JSONObject) {output.writeText(result.toString(2));println("ONDA_BENCH "+result.optJSONArray("trials")?.length())}
    @Test fun samplerIncludesLiveChildProcesses() {
        org.junit.Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("ondaBenchmark")=="true")
        val children=List(4){ProcessBuilder("/system/bin/sleep","3").start()}
        try {Thread.sleep(200);counters();assertTrue("Contador deve incluir filhos: $lastObservedProcesses",lastObservedProcesses.size>=5)}
        finally {children.forEach {it.destroy();it.waitFor()}}
    }
    @Test fun benchmarkSyntheticDownloadsAndIdle() {
        org.junit.Assume.assumeTrue("Diagnóstico demorado: use -e ondaBenchmark true",InstrumentationRegistry.getArguments().getString("ondaBenchmark")=="true")
        compose.waitForIdle()
        if(compose.onAllNodesWithText("Agora não").fetchSemanticsNodes().isNotEmpty())compose.onNodeWithText("Agora não").performClick()
        compose.onNodeWithTag("open-menu").performClick();compose.onNodeWithTag("tab-Links e fila").performClick()
        val saved=JSONObject(OndaStore.settings.value.toString());val past=OndaStore.history.value.map {it.id}.toSet()
        val result=JSONObject().put("platform","Android emulator x86_64 API "+Build.VERSION.SDK_INT).put("cpu_logical",Runtime.getRuntime().availableProcessors())
        val trials=JSONArray();result.put("trials",trials)
        val activeIds=mutableSetOf<String>();var module:com.chaquo.python.PyObject?=null
        try {
            OndaStore.saveSettings(JSONObject(saved.toString()).put("schedule_enabled",false).put("resume_queue",false).put("check_updates",false))
            result.put("idle_before_engine",measure("idle_before_engine"){Thread.sleep(10000)});write(result)
            result.put("engine_first_use",measure("engine_first_use"){MobileEngine.initialize(context)});write(result)
            // Diagnostic helper exists only in this instrumentation test. The
            // phone APK does not gain benchmarking code or Python dependencies.
            val code="""import sys,types
module=types.ModuleType('onda_performance_fixture')
exec('''
import json,subprocess,threading,http.server,time,tempfile,shutil
from pathlib import Path
def setup(folder):
    from mobile_backend import _native
    global root,server
    root=Path(tempfile.mkdtemp(prefix="performance-",dir=folder));wav=root/"fixture.wav"
    result=subprocess.run([str(_native/"libffmpeg.so"),"-v","error","-y","-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=60","-af","volume=0.1","-c:a","pcm_s16le",str(wav)],capture_output=True,timeout=60)
    assert result.returncode==0,result.stderr.decode(errors="replace")
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_HEAD(self):self.headers_only()
        def headers_only(self):
            self.send_response(200);self.send_header("Content-Type","audio/wav");self.send_header("Content-Length",str(wav.stat().st_size));self.end_headers()
        def do_GET(self):
            self.headers_only()
            try:
                with wav.open("rb") as f:
                    while chunk:=f.read(65536):
                        self.wfile.write(chunk);self.wfile.flush();time.sleep(65536/(2*1048576))
            except (BrokenPipeError,ConnectionResetError):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return "http://127.0.0.1:"+str(server.server_port)
def cleanup():
    server.shutdown();server.server_close();shutil.rmtree(root,ignore_errors=True)
''',module.__dict__)
sys.modules[module.__name__]=module
""".trimIndent()
            val builtins=Python.getInstance().getModule("builtins")
            builtins.callAttr("exec",code,builtins.callAttr("dict"))
            module=Python.getInstance().getModule("onda_performance_fixture")
            val base=module.callAttr("setup",context.cacheDir.absolutePath).toString()
            result.put("idle_after_engine",measure("idle_after_engine"){Thread.sleep(10000)});write(result)
            for(repeat in 0 until 3) {
                val scenarios=mutableListOf<Pair<Int,Boolean>>()
                for(workers in listOf(1,2,4))for(normal in listOf(false,true))scenarios.add(workers to normal)
                Collections.shuffle(scenarios,Random(70L+repeat))
                for((workers,normal) in scenarios) {
                    val options=JSONObject(OndaStore.settings.value.toString()).put("mode","mp3").put("audio_quality","320 kbps")
                        .put("concurrent_downloads",workers.toString()).put("normalize_volume",normal).put("duplicate_policy","keep").put("output_uri","")
                    OndaStore.saveSettings(options)
                    val ids=(0 until 4).map {OndaStore.enqueue("$base/track-$it.wav",options=options)}.toSet();activeIds.addAll(ids)
                    // Use the actual queue coordinator, native Python/FFmpeg,
                    // callbacks and publication into MediaStore.
                    val measured=measure("downloads") {
                        DownloadService.batch(context,ids.toList())
                        val deadline=SystemClock.uptimeMillis()+180000
                        while(SystemClock.uptimeMillis()<deadline) {
                            if(OndaStore.items.value.filter {it.id in ids}.all {it.state in listOf("Concluído","Erro")} && !DownloadRuntime.running.get())break
                            Thread.sleep(50)
                        }
                    }
                    assertEquals(4,OndaStore.items.value.count {it.id in ids && it.state=="Concluído"})
                    val completed=OndaStore.history.value.filter {it.id !in past}
                    assertEquals(4,completed.size)
                    measured.put("workers",workers).put("normalize",normal).put("repeat",repeat).put("output_bytes",completed.sumOf {it.size})
                    trials.put(measured);write(result)
                    OndaStore.remove(ids);activeIds.removeAll(ids)
                    completed.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null);OndaStore.removeHistory(it.id)}
                    Thread.sleep(800)
                }
            }
        } finally {
            DownloadService.stop(context)
            val deadline=SystemClock.uptimeMillis()+10000
            while(DownloadRuntime.running.get() && SystemClock.uptimeMillis()<deadline)Thread.sleep(50)
            OndaStore.remove(activeIds);OndaStore.saveSettings(saved)
            OndaStore.history.value.filter {it.id !in past}.forEach {context.contentResolver.delete(android.net.Uri.parse(it.uri),null,null);OndaStore.removeHistory(it.id)}
            module?.callAttr("cleanup");write(result)
        }
    }
}
