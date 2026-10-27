package br.com.onda.mobile

internal fun shuffledNextIndex(size:Int,current:Int,target:Int,choose:(Int)->Int={kotlin.random.Random.nextInt(it)}):Int {
    val candidates=(target until size).filter {it!=current}
    return if(candidates.isEmpty())target else candidates[choose(candidates.size)]
}

internal fun nextPlaybackIndex(size:Int,current:Int,repeat:String,automatic:Boolean=false):Int {
    if(size<=0)return -1
    if(automatic && repeat=="Uma" && current in 0 until size)return current
    val next=current+1
    return if(next in 0 until size)next else if(repeat=="Todas")0 else -1
}

/** Move one row without changing the identity of the track currently playing. */
internal fun <T> movePlaybackEntry(rows:List<T>,index:Int,direction:Int):List<T> {
    val target=index+direction
    if(index !in rows.indices || target !in rows.indices)return rows
    return rows.toMutableList().apply {add(target,removeAt(index))}
}

internal fun playbackCursorAfterMove(cursor:Int,from:Int,to:Int):Int=when {
    cursor==from->to
    from<cursor&&to>=cursor->cursor-1
    from>cursor&&to<=cursor->cursor+1
    else->cursor
}
