package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class TabGroupOrderTest {
    @Test fun defaultsKeepTheExistingAndroidMenuOrder() {
        assertEquals(listOf("tools","library"),normalizeTabGroupOrder(emptyList()))
    }
    @Test fun libraryCanMoveBeforeToolsWithoutChangingTheirMembers() {
        val before=moreGroups.mapValues {it.value.second.toList()}
        assertEquals(listOf("library","tools"),normalizeTabGroupOrder(listOf("library","tools")))
        assertEquals(before,moreGroups.mapValues {it.value.second})
    }
    @Test fun invalidAndDuplicateCategoriesCannotHideAGroup() {
        assertEquals(listOf("library","tools"),normalizeTabGroupOrder(listOf("invalid","library","library")))
        assertEquals(listOf("tools","library"),normalizeTabGroupOrder(listOf("invalid")))
    }
}
