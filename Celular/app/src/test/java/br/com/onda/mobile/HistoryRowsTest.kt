package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class HistoryRowsTest {
    private fun row(id:Long,title:String="Track")=HistoryItem(id,title,"content://audio/$id","mp3",100)
    @Test fun insertsConcurrentCompletionsInDatabaseOrder() {
        val rows=listOf(row(10),row(8),row(6))
        assertEquals(listOf(10L,9L,8L,6L),insertHistoryRow(rows,row(9)).map {it.id})
        assertEquals(listOf(11L,10L,8L,6L),insertHistoryRow(rows,row(11)).map {it.id})
    }
    @Test fun keepsLimitAndUpdatesExistingIdentity() {
        val rows=listOf(row(10),row(8),row(6))
        assertEquals(listOf(11L,10L,8L),insertHistoryRow(rows,row(11),3).map {it.id})
        assertSame(rows,insertHistoryRow(rows,row(1),3))
        val updated=insertHistoryRow(rows,row(8,"Updated"),3)
        assertEquals(3,updated.size);assertEquals("Updated",updated[1].title)
        assertEquals(1,insertHistoryRow(emptyList(),row(1)).size)
    }
}
