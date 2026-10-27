package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class QueueImprovementsTest {
    @get:Rule val compose=createComposeRule()
    @Test fun longPressDragReordersAndOffersAccessibleMoveActions() {
        var rows by mutableStateOf(listOf("First","Second","Third"))
        compose.setContent {MaterialTheme {
            val state=rememberLazyListState()
            LazyColumn(state=state,modifier=Modifier.height(360.dp)) {
                itemsIndexed(rows,key={_,row->row}) {index,row->
                    DraggableQueueCard(state,index,rows.size,move={from,to->rows=rows.toMutableList().apply {add(to,removeAt(from))}}) {
                    Row(Modifier.fillMaxWidth().height(80.dp),verticalAlignment=Alignment.CenterVertically) {
                        QueueDragHandle(state,index,rows.size){from,to->rows=rows.toMutableList().apply {add(to,removeAt(from))}}
                        Text(row)
                    }
                    }
                }
            }
        }}
        val handle=compose.onAllNodesWithContentDescription("Arrastar para reorganizar")[0]
        val actions=handle.fetchSemanticsNode().config[androidx.compose.ui.semantics.SemanticsActions.CustomActions]
        assertEquals(2,actions.size)
        val secondTop=compose.onNodeWithText("Second").fetchSemanticsNode().boundsInRoot.top
        val initialTop=compose.onNodeWithText("First").fetchSemanticsNode().boundsInRoot.top
        compose.onNodeWithText("First").performTouchInput {down(center);advanceEventTime(700);moveBy(Offset(0f,150.dp.toPx()),400)}
        assertTrue(compose.onNodeWithText("First").fetchSemanticsNode().boundsInRoot.top>initialTop+80)
        assertTrue(compose.onNodeWithText("Second").fetchSemanticsNode().boundsInRoot.top<secondTop-20)
        compose.onNodeWithText("First").performTouchInput {up()}
        compose.runOnIdle {assertEquals(listOf("Second","Third","First"),rows)}
        compose.runOnIdle {assertTrue(actions[1].label.isNotBlank())}
    }
    @Test fun compactOverlayDoesNotTakeWidthFromPlaybackCard() {
        val record=JSONObject().put("title","Test song").put("artists",org.json.JSONArray().put("Artist"))
        compose.setContent {MaterialTheme {
            val state=rememberLazyListState()
            Column(Modifier.width(300.dp)) {
                PlaybackQueueRow(record,"",120,false,false,{},{},{},{},false,true)
                PlaybackQueueRow(record,"",120,false,false,{},{},{},{},false,true,drag={QueueDragHandle(state,0,2){_,_->}})
            }
        }}
        val titles=compose.onAllNodesWithText("Test song").fetchSemanticsNodes()
        assertEquals(2,titles.size)
        assertEquals(titles[0].boundsInRoot.left,titles[1].boundsInRoot.left,1f)
        assertEquals(titles[0].boundsInRoot.width,titles[1].boundsInRoot.width,1f)
        val icon=compose.onNodeWithContentDescription("Arrastar para reorganizar").fetchSemanticsNode()
        assertTrue(icon.boundsInRoot.width<=with(compose.density){24.dp.toPx()}+1f)
    }
    @Test fun interruptedQueueRestoresCheckpointWithoutStartingService() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context)
        val id=OndaStore.enqueue("https://example.com/recovery-"+java.util.UUID.randomUUID()+".mp4",options=JSONObject(OndaStore.settings.value.toString()).put("detect_duplicates",false))
        try {
            OndaStore.update(id,"Baixando",43f)
            OndaStore.items.value=emptyList()
            OndaStore.initialize(context)
            val restored=OndaStore.items.value.first {it.id==id}
            assertEquals("Pendente",restored.state);assertEquals(43f,restored.progress,0f)
            assertTrue(restored.config.optBoolean("_interrupted"));assertFalse(DownloadRuntime.running.get())
        } finally {OndaStore.remove(setOf(id))}
    }
}
