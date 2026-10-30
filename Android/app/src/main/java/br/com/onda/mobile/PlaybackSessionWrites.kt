package br.com.onda.mobile

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executor

/** Immutable snapshots, ordered disk writes and immediate reads of pending positions. */
internal class PlaybackSessionWrites(private val executor: Executor, private val failed: (Exception) -> Unit) {
    private class Snapshot(val raw: String)
    private val pending = ConcurrentHashMap<String, Snapshot>()
    private val persisted = ConcurrentHashMap<String, String>()
    private val writeLock = Any()

    fun latest(key: String): String? = pending[key]?.raw

    fun save(key: String, raw: String, synchronous: Boolean, commit: (String) -> Unit) {
        val snapshot = Snapshot(raw)
        pending[key] = snapshot
        val write = {
            synchronized(writeLock) {
                // A delayed save from an older song must never replace the latest position.
                if (pending[key] === snapshot) {
                    if (synchronous || persisted[key] != raw) {
                        commit(raw)
                        persisted[key] = raw
                    }
                    pending.remove(key, snapshot)
                }
            }
        }
        if (synchronous) write() else executor.execute {
            try { write() } catch (error: Exception) { failed(error) }
        }
    }
}
