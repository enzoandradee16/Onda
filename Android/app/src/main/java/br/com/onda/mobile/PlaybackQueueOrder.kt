package br.com.onda.mobile

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
