package br.com.onda.mobile

private val wordTimestamp=Regex("<([0-9]{1,3}):([0-5][0-9])(?:[.:]([0-9]{1,3}))?>")
internal fun lyricPlainText(text:String)=text.replace(wordTimestamp,"")
internal data class LyricWord(val seconds:Double,val text:String)
internal data class LyricVerse(val plain:String,val prefix:String,val words:List<LyricWord>)

/** Parse once per lyrics document, then only look up the clock on playback frames. */
internal class LyricTimeline(val lines:List<Pair<Double,String>>) {
    val synced=lines.any {it.first>0}
    private val ordered=(1 until lines.size).all {lines[it-1].first<=lines[it].first}
    val verses=lines.map {(_,text)->
        val stamps=wordTimestamp.findAll(text).toList()
        LyricVerse(lyricPlainText(text),text.substring(0,stamps.firstOrNull()?.range?.first ?: text.length),stamps.mapIndexed {i,stamp->
            val fraction=stamp.groupValues[3]
            val seconds=stamp.groupValues[1].toInt()*60+stamp.groupValues[2].toInt()+if(fraction.isEmpty())0.0 else fraction.toDouble()/Math.pow(10.0,fraction.length.toDouble())
            LyricWord(seconds,text.substring(stamp.range.last+1,stamps.getOrNull(i+1)?.range?.first ?: text.length))
        })
    }
    fun activeIndex(seconds:Double):Int {
        if(!synced || seconds.isNaN())return -1
        if(!ordered)return lines.indexOfLast {it.first<=seconds}
        var low=0;var high=lines.size
        while(low<high){val middle=(low+high) ushr 1;if(lines[middle].first<=seconds)low=middle+1 else high=middle}
        return low-1
    }
}
internal fun lyricActiveIndex(lines:List<Pair<Double,String>>,seconds:Double)=LyricTimeline(lines).activeIndex(seconds)
