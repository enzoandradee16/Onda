package br.com.onda.mobile

import java.util.Locale
import kotlin.math.ceil

internal data class QueueTimes(val elapsed:Long,val remaining:Long?)
internal fun queueDuration(seconds:Long):String {
    val safe=seconds.coerceAtLeast(0)
    return if(safe>=3600)String.format(Locale.ROOT,"%02d:%02d:%02d",safe/3600,(safe%3600)/60,safe%60)
        else String.format(Locale.ROOT,"%02d:%02d",safe/60,safe%60)
}
/** Engine-owned clock keeps correct boundaries even while the UI is in background. */
internal class QueueTiming(private val clock:()->Double={System.nanoTime()/1_000_000_000.0}) {
    private var accumulated=0.0
    private var started:Double?=null
    private var completed=0
    @Synchronized fun reset() {accumulated=0.0;started=null;completed=0}
    @Synchronized fun setRunning(running:Boolean) {
        if(running && started==null)started=clock()
        else if(!running && started!=null) {accumulated+=(clock()-started!!).coerceAtLeast(0.0);started=null}
    }
    @Synchronized fun recordCompletion() {if(started!=null)completed++}
    @Synchronized fun snapshot(remaining:Int,hasItems:Boolean=true):QueueTimes {
        val elapsed=accumulated+(started?.let {(clock()-it).coerceAtLeast(0.0)} ?: 0.0)
        val estimate=if(hasItems && remaining==0)0L else if(started!=null && completed>0 && elapsed>0)
            ceil(elapsed/completed*remaining.coerceAtLeast(0)).takeIf {it.isFinite()}?.toLong() else null
        return QueueTimes(elapsed.toLong(),estimate)
    }
}
