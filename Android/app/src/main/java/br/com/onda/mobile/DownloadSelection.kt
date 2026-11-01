package br.com.onda.mobile

import java.util.Locale

/** Match selected completed downloads in one pass, retaining history order. */
internal fun downloadMetadataUris(queue:List<DownloadItem>,selected:Set<String>,history:List<HistoryItem>):List<String> {
    if(selected.isEmpty())return emptyList()
    val keys=queue.asSequence().filter {it.id in selected && it.state=="Concluído"}
        .mapNotNull {item->jobSource(item.config).takeIf {it.isNotBlank()}?.let {it to item.config.optString("mode").lowercase(Locale.ROOT)}}.toHashSet()
    if(keys.isEmpty())return emptyList()
    return history.asSequence().filter {(it.source to it.mode.lowercase(Locale.ROOT)) in keys && historyKind(it.mode,it.title)=="Áudio"}
        .map {it.uri}.distinct().toList()
}
