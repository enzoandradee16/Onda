package br.com.onda.mobile
import androidx.compose.ui.unit.dp

import android.content.Context
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.Typography
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import org.json.JSONObject

internal val LocalUiLanguage=staticCompositionLocalOf { "pt-BR" }
internal val UI_LANGUAGES=listOf("pt-BR","es","en")
internal fun normalizedLanguage(value:String)=value.takeIf {it in UI_LANGUAGES} ?: "pt-BR"

private data class UiTemplate(val pattern:Regex,val placeholders:List<String>,val translation:String)

private object UiCatalog {
    private var diagnostics:TechnicalErrorCatalog?=null
    @Synchronized fun errors(context:Context):TechnicalErrorCatalog = diagnostics ?: run {
        val data=JSONObject(context.assets.open("technical_errors.json").bufferedReader().use {it.readText()})
        val rows=data.getJSONArray("phrases")
        val phrases=(0 until rows.length()).map {index->val row=rows.getJSONObject(index);UI_LANGUAGES.associateWith {row.getString(it)}}
        val headings=data.getJSONObject("unknown")
        TechnicalErrorCatalog(phrases,UI_LANGUAGES.associateWith {headings.getString(it)}).also {diagnostics=it}
    }
    private val compiled=mutableMapOf<String,List<UiTemplate>>()
    private val loaded=mutableMapOf<String,Map<String,String>>()
    @Synchronized fun templates(context:Context,language:String):List<UiTemplate> = compiled.getOrPut(language) {
        buildList {
            val placeholder=Regex("\\{([a-zA-Z_][a-zA-Z_0-9]*)\\}")
            for((key,translation) in get(context,language)) {
                val matches=placeholder.findAll(key).toList()
                if(matches.isEmpty())continue
                var position=0
                val pattern=buildString {
                    for(match in matches){append(Regex.escape(key.substring(position,match.range.first)));append("(.+?)");position=match.range.last+1}
                    append(Regex.escape(key.substring(position)))
                }
                add(UiTemplate(Regex(pattern,RegexOption.DOT_MATCHES_ALL),matches.map {it.value},translation))
            }
        }.sortedByDescending {it.pattern.pattern.replace("(.+?)","").length}
    }
    @Synchronized fun get(context:Context,language:String):Map<String,String> = loaded.getOrPut(language) {
        JSONObject(context.assets.open("$language.json").bufferedReader().use {it.readText()}).let {json->
            json.keys().asSequence().associateWith {json.getString(it)}
        }
    }
}

internal fun translateUi(text:String,language:String=OndaStore.settings.value.optString("language","pt-BR"),context:Context=OndaStore.context):String {
    val selected=normalizedLanguage(language)
    if(selected=="pt-BR")return text
    val catalog=UiCatalog.get(context,selected)
    catalog[text]?.let {return it}
    if('\n' in text)return text.split('\n').joinToString("\n"){translateUi(it,selected,context)}
    if(Regex("^(?:(?:ERROR|ERRO|WARNING|AVISO):|[\\w.]+(?:Error|Exception):|\\[(?:Errno|WinError) )").containsMatchIn(text)) {
        for(colon in Regex(": ").findAll(text)) {
            val end=colon.range.last+1
            catalog[text.substring(end)]?.let {return UiCatalog.errors(context).translate(text.substring(0,end),selected)+it}
        }
    }
    for(template in UiCatalog.templates(context,selected)) {
        val match=template.pattern.matchEntire(text) ?: continue
        var output=template.translation
        template.placeholders.forEachIndexed {index,placeholder->
            val value=match.groupValues[index+1]
            val translated=if(placeholder in listOf("{state}","{status}","{message}","{reason}","{size}","{label}"))translateUi(value,selected,context) else value
            output=output.replace(placeholder,translated)
        }
        return output
    }
    return text
}

internal fun translateError(text:String,language:String=OndaStore.settings.value.optString("language","pt-BR"),context:Context=OndaStore.context):String {
    val selected=normalizedLanguage(language)
    val translated=UiCatalog.errors(context).translate(translateUi(text,selected,context),selected)
    return UiCatalog.errors(context).explain(text,translated,selected,UiCatalog.get(context,"en").containsKey(text))
}

@Composable internal fun LocalizedTheme(language:String,colorScheme:ColorScheme,typography:Typography,spacing:String="Padrão",content:@Composable ()->Unit) {
    CompositionLocalProvider(LocalUiLanguage provides normalizedLanguage(language),LocalLayoutSpacing provides spacingValues(spacing)) {
        MaterialTheme(colorScheme=colorScheme,typography=typography,shapes=androidx.compose.material3.Shapes(extraSmall=androidx.compose.foundation.shape.RoundedCornerShape(16.dp),small=androidx.compose.foundation.shape.RoundedCornerShape(12.dp),medium=androidx.compose.foundation.shape.RoundedCornerShape(16.dp),large=androidx.compose.foundation.shape.RoundedCornerShape(20.dp)),content=content)
    }
}

@Composable internal fun UiText(text:String,modifier:Modifier=Modifier,color:Color=Color.Unspecified,
    fontWeight:FontWeight?=null,textAlign:TextAlign?=null,overflow:TextOverflow=TextOverflow.Clip,
    softWrap:Boolean=true,maxLines:Int=Int.MAX_VALUE,style:TextStyle=androidx.compose.material3.LocalTextStyle.current) {
    val language=LocalUiLanguage.current
    val context=LocalContext.current
    val translated=remember(text,language) {translateUi(text,language,context)}
    androidx.compose.material3.Text(translated,modifier=settingsSearchModifier(text,modifier),color=color,fontWeight=fontWeight,
        textAlign=textAlign,overflow=overflow,softWrap=softWrap,maxLines=maxLines,style=style)
}

@Composable internal fun UiErrorText(text:String,modifier:Modifier=Modifier,color:Color=Color.Unspecified,
    maxLines:Int=Int.MAX_VALUE,style:TextStyle=MaterialTheme.typography.bodyMedium) {
    val language=LocalUiLanguage.current
    val context=LocalContext.current
    val translated=remember(text,language){translateError(text,language,context)}
    androidx.compose.material3.Text(translated,modifier=modifier,color=color,maxLines=maxLines,style=style)
}

internal fun uiExceptionMessage(error:Throwable,fallback:String)=translateError(error.message ?: fallback)
