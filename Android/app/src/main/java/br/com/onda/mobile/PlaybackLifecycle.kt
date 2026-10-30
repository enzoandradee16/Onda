package br.com.onda.mobile

/** Launcher component changes may remove a task even with DONT_KILL_APP. */
internal fun canApplyLauncherChange(visibleActivities: Int, localAudio: Boolean, effectsAudio: Boolean, remoteSession: Boolean): Boolean =
    visibleActivities == 0 && !localAudio && !effectsAudio && !remoteSession

/** Transitions briefly publish an idle state; recheck before stopping the service. */
internal class PlaybackIdleStop {
    private var revision = 0L
    fun changed(): Long = ++revision
    fun canStop(request: Long, playing: Boolean, preparing: Boolean = false): Boolean =
        request == revision && !playing && !preparing
}
