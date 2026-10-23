package br.com.onda.mobile

/** Advance only while audio plays; restart the interval when the song changes. */
internal class JukeboxTimerProgress(private val durationSeconds:Double) {
    private var song:Any?=null
    var elapsed=0.0
        private set
    fun advance(seconds:Double,playing:Boolean,paused:Boolean,model:Any?):Double {
        if(model!==song){song=model;elapsed=0.0}
        if(playing && !paused && model!=null)elapsed=(elapsed+seconds.coerceAtLeast(0.0)).coerceAtMost(durationSeconds)
        return (durationSeconds-elapsed).coerceAtLeast(0.0)
    }
    fun restart(){elapsed=0.0}
}

/** Follow an actual audible crossfade, never an arbitrary animation duration. */
internal fun jukeboxJumpBlend(phase:Float,seconds:Double,transitionSeconds:Double):Float {
    if(seconds<=0 || transitionSeconds<=0)return 0f
    val portion=(transitionSeconds/seconds).coerceIn(0.0,1.0)
    return ((phase-(1-portion))/portion).toFloat().coerceIn(0f,1f)
}
