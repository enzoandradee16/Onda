package br.com.onda.mobile

import androidx.compose.foundation.Canvas
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics

@Composable internal fun OndaLogo(modifier:Modifier=Modifier,description:String?=null) {
    val accent=MaterialTheme.colorScheme.primary
    val background=MaterialTheme.colorScheme.surface
    Canvas(modifier.semantics {if(description!=null)contentDescription=description}) {
        val x=size.width/48f;val y=size.height/48f
        drawRoundRect(background,cornerRadius=CornerRadius(size.width/4f))
        for((position,top,bottom) in listOf(Triple(9,21,27),Triple(16,14,34),Triple(24,8,40),Triple(32,14,34),Triple(39,21,27))) {
            drawLine(accent,Offset(position*x,top*y),Offset(position*x,bottom*y),strokeWidth=3*x,cap=StrokeCap.Round)
        }
    }
}
