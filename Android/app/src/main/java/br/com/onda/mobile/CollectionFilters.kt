package br.com.onda.mobile

import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

internal fun collectionFold(value:String):String {
    val text=Normalizer.normalize(value,Normalizer.Form.NFKC).lowercase(Locale.ROOT)
    return buildString {
        text.forEach {char->
            when {
                char in '\u30a1'..'\u30f6'->append((char.code-0x60).toChar())
                Character.UnicodeScript.of(char.code)==Character.UnicodeScript.LATIN->append(Normalizer.normalize(char.toString(),Normalizer.Form.NFD).filter {Character.getType(it)!=Character.NON_SPACING_MARK.toInt()})
                else->append(char)
            }
        }
    }
}
internal fun collectionDate(row:JSONObject):String = if(row.optString("kind")=="album")
    row.cleanString("release_date").ifBlank {row.optJSONArray("tracks")?.objects()?.firstNotNullOfOrNull {it.cleanString("release_date").takeIf(String::isNotBlank)}.orEmpty()}
    else row.cleanString("created_at").ifBlank {row.cleanString("creation_date")}
internal fun collectionDateMatches(value:String,query:String):Boolean {
    val q=query.trim()
    if(q.isBlank())return true
    val term=if(Regex("\\d{2}/\\d{2}/\\d{4}").matches(q))q.split('/').reversed().joinToString("-") else q
    return value.isNotBlank() && value.startsWith(term)
}
internal data class CollectionFilterEntry(val row:JSONObject,val title:String,val artist:String,val album:String,val all:String,val kind:String,val date:String)
internal fun collectionFilterIndex(rows:List<JSONObject>,collections:Boolean=false)=rows.map {row->
    val title=collectionFold(row.optString("title"))
    val artist=collectionFold(row.stringList("artists").ifBlank {row.cleanString("owner").ifBlank {row.cleanString("subtitle")}})
    val album=collectionFold(row.cleanString("album"))
    CollectionFilterEntry(row,title,artist,album,"$title $artist $album",row.optString("kind","playlist"),if(collections)collectionDate(row) else row.cleanString("release_date"))
}
internal fun filterCollectionEntries(index:List<CollectionFilterEntry>,query:String,artist:String="",album:String="",kind:String="",date:String="",collections:Boolean=false):List<JSONObject> {
    fun terms(value:String)=collectionFold(value).split(Regex("\\s+")).filter(String::isNotBlank)
    val names=terms(query);val artists=terms(artist);val albums=terms(album)
    return index.filter {entry->(kind.isBlank()||entry.kind==kind) && names.all {it in if(collections)entry.all else entry.title} && artists.all {it in entry.artist} && albums.all {it in entry.album} && collectionDateMatches(entry.date,date)}.map {it.row}
}

internal fun orderCollectionRows(rows:List<JSONObject>,field:String,descending:Boolean):List<JSONObject> {
    if(field.isBlank())return rows
    fun value(row:JSONObject)=collectionFold(when(field){
        "date"->collectionDate(row)
        "artist"->row.stringList("artists").ifBlank {row.cleanString("artist")}
        else->row.cleanString(field)
    })
    return rows.map {it to value(it)}.sortedWith {a,b->
        val av=a.second;val bv=b.second
        if(av.isBlank()!=bv.isBlank()) {if(av.isBlank())1 else -1}
        else av.compareTo(bv)*(if(descending)-1 else 1)
    }.map {it.first}
}
