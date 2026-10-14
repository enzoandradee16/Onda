package br.com.onda.mobile

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.text.TextStyle

@Composable internal fun Modifier.a11yLabel(label:String,state:String?=null):Modifier {
    val language=LocalUiLanguage.current
    val name=translateUi(label,language)
    val value=state?.let {translateUi(it,language)}
    return semantics {contentDescription=name;if(value!=null)stateDescription=value}
}

@Composable internal fun AccessibleSymbol(symbol:String,label:String,modifier:Modifier=Modifier,style:TextStyle=androidx.compose.material3.LocalTextStyle.current) {
    val name=translateUi(label,LocalUiLanguage.current)
    UiText(symbol,modifier.clearAndSetSemantics {contentDescription=name},style=style)
}

@Composable internal fun Modifier.a11yState(state:String):Modifier {
    val value=translateUi(state,LocalUiLanguage.current)
    return semantics {stateDescription=value}
}
