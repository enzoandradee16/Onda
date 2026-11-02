package br.com.onda.mobile

import org.json.JSONObject
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test

class CollectionFiltersTest {
    @Test fun combinesTrackFiltersWithoutMutatingTheCollection() {
        val first=JSONObject().put("title","Other").put("artists",JSONArray().put("Someone"))
        val target=JSONObject().put("title","Coração カタカナ").put("artists",JSONArray().put("Cindy")).put("album","Angel Touch").put("release_date","1990-05-25")
        val rows=listOf(first,target)
        val index=collectionFilterIndex(rows)
        assertEquals(listOf(target),filterCollectionEntries(index,"coracao かたかな","cindy","angel",date="25/05/1990"))
        assertEquals(2,rows.size)
        assertSame(target,filterCollectionEntries(index,"",date="1990").single())
        assertTrue(filterCollectionEntries(index,"",date="2000").isEmpty())
    }
    @Test fun filtersSavedTypesAndUsesOnlyActualCreationDates() {
        val album=JSONObject().put("title","Album").put("kind","album").put("release_date","1990-05-25")
        val playlist=JSONObject().put("title","Playlist").put("kind","playlist").put("creation_date","2020-02-01")
        val unknown=JSONObject().put("title","Unknown").put("tracks",JSONArray().put(JSONObject().put("release_date","1980")))
        val index=collectionFilterIndex(listOf(album,playlist,unknown),true)
        assertEquals(listOf(album),filterCollectionEntries(index,"",kind="album",date="1990",collections=true))
        assertEquals(listOf(playlist),filterCollectionEntries(index,"",kind="playlist",date="2020",collections=true))
        assertEquals("",collectionDate(unknown))
        assertTrue(filterCollectionEntries(index,"",date="1980",collections=true).isEmpty())
        assertEquals(3,filterCollectionEntries(index,"",collections=true).size)
    }
    @Test fun orderingPreservesIdentityAndKeepsUnknownDatesLast() {
        val old=JSONObject().put("kind","playlist").put("created_at","1990-01-01")
        val newer=JSONObject().put("kind","playlist").put("created_at","2020-01-01")
        val unknown=JSONObject()
        val rows=listOf(unknown,old,newer)
        assertEquals(listOf(newer,old,unknown),orderCollectionRows(rows,"date",true))
        assertEquals(listOf(old,newer,unknown),orderCollectionRows(rows,"date",false))
        assertSame(rows,orderCollectionRows(rows,"",false))
        assertSame(unknown,rows.first())
    }
}
