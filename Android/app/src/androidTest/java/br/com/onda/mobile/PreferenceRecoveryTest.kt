package br.com.onda.mobile

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PreferenceRecoveryTest {
    @Test fun malformedStoredObjectsCanFallBackToDefaults() {
        for(text in listOf(null,"","{broken","[]","null","42"))assertNull(storedObject(text))
        val valid=storedObject("{\"remember\":false,\"language\":\"en\"}")!!
        assertFalse(valid.getBoolean("remember"))
        assertEquals("en",valid.getString("language"))
    }
    @Test fun malformedCollectionPreferencesFallBackToCurrentSettings() {
        val prefs=OndaStore.context.getSharedPreferences("preferences",0)
        val previous=prefs.getString("collection_options",null)
        try {
            prefs.edit().putString("collection_options","[]").commit()
            assertEquals(OndaStore.settings.value.toString(),OndaStore.collectionOptions().toString())
        } finally {prefs.edit().putString("collection_options",previous).commit()}
    }
}
