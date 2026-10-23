package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class BottomBarOrderTest {
    @Test fun restoresMissingAndRejectsUnknownOrRepeatedDestinations() {
        assertEquals(bottomBarDefaults,normalizeBottomBarOrder(emptyList()))
        assertEquals(listOf("Efeitos","Pesquisar","Fila"),normalizeBottomBarOrder(listOf("Mais","Efeitos","Efeitos","invalid")))
    }
    @Test fun everyPermutationKeepsMoreLastAndRespectsPlaybackVisibility() {
        for(a in bottomBarDefaults)for(b in bottomBarDefaults.filter {it!=a}) {
            val order=listOf(a,b)+bottomBarDefaults.filter {it!=a && it!=b}
            assertEquals(order+"Mais",bottomBarDestinations(order,true))
            assertEquals(order.filter {it!="Efeitos"}+"Mais",bottomBarDestinations(order,false))
        }
    }
}
