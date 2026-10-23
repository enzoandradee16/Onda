package br.com.onda.mobile

import android.os.SystemClock

/** Rate-limit presentation only; terminal events always pass immediately. */
internal class ProgressGate(private val intervalMs: Long, private val now: () -> Long = {SystemClock.elapsedRealtime()}) {
    private var last: Long? = null
    @Synchronized fun allow(force: Boolean = false): Boolean {
        val time = now()
        if (!force && last?.let {time - it < intervalMs} == true) return false
        last = time
        return true
    }
}
