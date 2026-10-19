package br.com.onda.mobile

/** Preserve newest-first history without reloading thousands of unchanged database rows. */
internal fun insertHistoryRow(rows:List<HistoryItem>,item:HistoryItem,limit:Int=3000):List<HistoryItem> {
    require(limit>0)
    val found=rows.binarySearchBy(-item.id) {-it.id}
    val position=if(found>=0)found else -found-1
    if(position>=limit)return rows
    val next=ArrayList<HistoryItem>(minOf(rows.size+1,limit))
    next.addAll(rows.take(position));next.add(item)
    next.addAll(rows.drop(position+if(found>=0)1 else 0).take(limit-next.size))
    return next
}
