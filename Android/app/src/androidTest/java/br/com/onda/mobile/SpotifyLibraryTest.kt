package br.com.onda.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import com.chaquo.python.Python
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

class SpotifyLibraryTest {
    @get:Rule val compose=createComposeRule()
    @Test fun accountPlaylistsAppearAndOpenWithoutTypingLinks() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        OndaStore.initialize(context);MobileEngine.initialize(context)
        val fixture=Python.getInstance().getModule("spotify_library_smoke")
        fixture.callAttr("install")
        val store=ViewModelStore()
        lateinit var vm:OndaViewModel
        try {
            compose.runOnUiThread {
                vm=ViewModelProvider(store,ViewModelProvider.AndroidViewModelFactory.getInstance(ApplicationProvider.getApplicationContext()))[OndaViewModel::class.java]
                vm.collection.value=org.json.JSONObject()
                vm.spotifyConnected.value=true
            }
            compose.setContent {MaterialTheme {CollectionsPage(vm)}}
            compose.waitUntil(15000){vm.spotifyPlaylists.value.size==1 && !vm.busy.value}
            compose.onNodeWithTag("spotify-playlist-"+"A".repeat(22)).performScrollTo().assertIsDisplayed()
            compose.onNodeWithText("Usar em reprodução").assertIsEnabled()
            compose.onNodeWithText("Abrir coleção").performClick()
            compose.waitUntil(15000){vm.collection.value.optJSONArray("tracks")?.length()==1 && !vm.busy.value}
            assertEquals("Fixture playlist",vm.collection.value.getString("title"))
            assertEquals("Fixture track",vm.collection.value.getJSONArray("tracks").getJSONObject(0).getString("title"))
        } finally {compose.runOnUiThread {store.clear()};fixture.callAttr("restore")}
    }
}
