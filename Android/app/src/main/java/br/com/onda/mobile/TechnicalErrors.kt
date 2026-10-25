package br.com.onda.mobile

/** Shared diagnostic vocabulary; values such as URLs, paths and codecs remain intact. */
internal class TechnicalErrorCatalog(private val rows:List<Map<String,String>>,private val unknown:Map<String,String>) {
    private val phrases=buildMap<String,Map<String,String>> {rows.forEach {row->row.values.forEach {phrase->putIfAbsent(phrase.lowercase(java.util.Locale.ROOT),row)}}}
    private val expression=Regex("(?<![\\p{L}\\p{N}_])(?:"+phrases.keys.sortedByDescending {it.length}.joinToString("|"){Regex.escape(it)}+")(?![\\p{L}\\p{N}_])",RegexOption.IGNORE_CASE)
    private val protectedValues=Regex("""(["'])(?:[A-Za-z]:[\\/]|/|\\\\|\.{1,2}[\\/])[^\n]*?\1|\\\\[^\s<>"']+|\.{1,2}[\\/][^\s<>"']+|https?://[^\s<>"']+|(?:[A-Za-z]:[\\/]|/)[^\s<>"']+|\b[^\s<>"']+\.(?:mp3|m4a|flac|wav|ogg|opus|apk|exe|json|lrc|txt|mp4|webm)\b""",RegexOption.IGNORE_CASE)
    fun translate(text:String,language:String):String {
        fun part(value:String)=expression.replace(value){phrases.getValue(it.value.lowercase(java.util.Locale.ROOT)).getValue(language)}
        val heading=unknown.values.firstOrNull {text.startsWith(it)}
        val input=if(heading!=null)unknown.getValue(language)+text.substring(heading.length) else text
        var start=0
        return buildString {
            protectedValues.findAll(input).forEach {match->append(part(input.substring(start,match.range.first)));append(match.value);start=match.range.last+1}
            append(part(input.substring(start)))
        }
    }
    fun explain(raw:String,translated:String,language:String,known:Boolean=false):String {
        if(raw.isBlank() || translated!=raw || known || expression.containsMatchIn(raw) || language=="pt-BR" && Regex("[ãõçáéíóúâêô]").containsMatchIn(raw))return translated
        val heading=unknown.getValue(language)
        if(unknown.values.any {raw.startsWith(it)})return heading+raw.substringAfter(':')
        return heading+"\n"+raw
    }
}
