package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

/** Virtualized content plus constant-size navigation, including TalkBack actions. */
@Composable internal fun NavigableList(modifier:Modifier=Modifier,navigationId:String,verticalArrangement:Arrangement.Vertical=Arrangement.spacedBy(LayoutSpacing.controls),content:LazyListScope.()->Unit) {
    val state=rememberLazyListState()
    val scope=rememberCoroutineScope()
    val count by remember {derivedStateOf {state.layoutInfo.totalItemsCount}}
    var dragging by remember {mutableStateOf<Float?>(null)}
    Box(modifier) {
        LazyColumn(Modifier.fillMaxSize().testTag("$navigationId-list"),state=state,verticalArrangement=verticalArrangement,contentPadding=PaddingValues(bottom=if(count>30)80.dp else 8.dp),content=content)
        if(count>30) Surface(Modifier.align(Alignment.BottomCenter).fillMaxWidth(),tonalElevation=4.dp) {
            Row(Modifier.padding(horizontal=4.dp),verticalAlignment=Alignment.CenterVertically) {
                TextButton(onClick={scope.launch {state.scrollToItem(0)}},modifier=Modifier.testTag("$navigationId-first")){AccessibleSymbol("↑","Início")}
                Slider(value=dragging ?: state.firstVisibleItemIndex.toFloat()/((count-1).coerceAtLeast(1)),onValueChange={dragging=it},onValueChangeFinished={val position=dragging ?: 0f;dragging=null;scope.launch {state.scrollToItem((position*(count-1)).toInt().coerceIn(0,(count-1).coerceAtLeast(0))) }},modifier=Modifier.weight(1f).a11yLabel("Posição na lista").testTag("$navigationId-position"))
                TextButton(onClick={scope.launch {state.scrollToItem((count-1).coerceAtLeast(0))}},modifier=Modifier.testTag("$navigationId-last")){AccessibleSymbol("↓","Fim")}
            }
        }
    }
}
